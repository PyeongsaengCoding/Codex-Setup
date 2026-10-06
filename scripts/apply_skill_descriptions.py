#!/usr/bin/env python3
"""Plan or apply curated one-line descriptions to selected Codex skills."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass


class DescriptionError(Exception):
    """A validation error that must prevent all target writes."""


@dataclass(frozen=True)
class Change:
    relative_path: str
    path: Path
    original: bytes
    updated: bytes
    mode: int
    before_count: int
    after_count: int


def parse_args() -> argparse.Namespace:
    script_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Plan description updates; pass --apply to write them."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=script_root / "config" / "skill-descriptions.json",
        help="JSON object mapping relative SKILL.md paths to descriptions",
    )
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=Path("~/.agents/skills").expanduser(),
        help="root containing the selected skill paths",
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        default=Path("~/Downloads/Codex-Setup-Backups").expanduser(),
        help="directory in which private timestamped backups are created",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write validated changes (default is a read-only plan)",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, str]:
    duplicate_keys: list[str] = []

    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                duplicate_keys.append(key)
            result[key] = value
        return result

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle, object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DescriptionError(f"cannot read manifest {path}: {exc}") from exc

    if duplicate_keys:
        raise DescriptionError(
            "manifest has duplicate path(s): " + ", ".join(sorted(set(duplicate_keys)))
        )
    if not isinstance(data, dict):
        raise DescriptionError("manifest must be a JSON object")

    manifest: dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise DescriptionError("every manifest path and description must be a string")
        if not value.strip() or "\n" in value or "\r" in value:
            raise DescriptionError(f"description for {key!r} must be non-empty and single-line")
        manifest[key] = value
    return manifest


def validate_relative_path(raw_path: str) -> PurePosixPath:
    relative = PurePosixPath(raw_path)
    if (
        not raw_path
        or relative.is_absolute()
        or "\\" in raw_path
        or any(part in ("", ".", "..") for part in relative.parts)
        or relative.name != "SKILL.md"
    ):
        raise DescriptionError(f"invalid relative SKILL.md path: {raw_path!r}")
    return relative


def strip_line_ending(line: bytes) -> tuple[bytes, bytes]:
    if line.endswith(b"\r\n"):
        return line[:-2], b"\r\n"
    if line.endswith(b"\n") or line.endswith(b"\r"):
        return line[:-1], line[-1:]
    return line, b""


def description_value_length(raw_value: str, relative_path: str) -> int:
    value = raw_value.strip()
    if not value or value[0] in "|>":
        raise DescriptionError(
            f"{relative_path}: description must be a non-empty single-line scalar"
        )
    if value.startswith('"'):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise DescriptionError(
                f"{relative_path}: invalid double-quoted description: {exc.msg}"
            ) from exc
        if not isinstance(decoded, str):
            raise DescriptionError(f"{relative_path}: description must be a string")
        return len(decoded)
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise DescriptionError(f"{relative_path}: invalid single-quoted description")
        decoded = value[1:-1].replace("''", "'")
        return len(decoded)
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return len(value)


def rewrite_description(
    original: bytes, new_description: str, relative_path: str
) -> tuple[bytes, int, int]:
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DescriptionError(f"{relative_path}: SKILL.md is not valid UTF-8") from exc

    byte_lines = original.splitlines(keepends=True)
    text_lines = text.splitlines(keepends=True)
    if not byte_lines or len(byte_lines) != len(text_lines):
        raise DescriptionError(f"{relative_path}: cannot parse frontmatter lines")

    first, _ = strip_line_ending(byte_lines[0])
    if first != b"---":
        raise DescriptionError(f"{relative_path}: missing opening frontmatter delimiter")

    closing_index = None
    for index in range(1, len(byte_lines)):
        content, _ = strip_line_ending(byte_lines[index])
        if content == b"---":
            closing_index = index
            break
    if closing_index is None:
        raise DescriptionError(f"{relative_path}: missing closing frontmatter delimiter")

    matches: list[tuple[int, str, str]] = []
    for index in range(1, closing_index):
        line_content = text_lines[index].rstrip("\r\n")
        if line_content.startswith("description:"):
            matches.append((index, "description:", line_content[len("description:") :]))

    if len(matches) != 1:
        raise DescriptionError(
            f"{relative_path}: expected exactly one single-line description field; found {len(matches)}"
        )

    line_index, prefix, old_value = matches[0]
    before_count = description_value_length(old_value, relative_path)
    encoded_description = json.dumps(new_description, ensure_ascii=False)
    _, ending = strip_line_ending(byte_lines[line_index])
    replacement = f"{prefix} {encoded_description}".encode("utf-8") + ending

    updated_lines = list(byte_lines)
    updated_lines[line_index] = replacement
    return b"".join(updated_lines), before_count, len(new_description)


def collect_changes(
    manifest: dict[str, str], skill_root: Path
) -> tuple[list[Change], int, int]:
    try:
        root = skill_root.expanduser().resolve(strict=True)
    except OSError as exc:
        raise DescriptionError(f"cannot resolve skill root {skill_root}: {exc}") from exc
    if not root.is_dir():
        raise DescriptionError(f"skill root is not a directory: {root}")

    changes: list[Change] = []
    before_total = 0
    after_total = 0
    for raw_path in sorted(manifest):
        relative = validate_relative_path(raw_path)
        lexical_target = root.joinpath(*relative.parts)
        try:
            target_lstat = lexical_target.lstat()
            target = lexical_target.resolve(strict=True)
            target.relative_to(root)
        except (OSError, ValueError) as exc:
            raise DescriptionError(f"unsafe or missing target {raw_path!r}: {exc}") from exc
        if stat.S_ISLNK(target_lstat.st_mode) or not stat.S_ISREG(target_lstat.st_mode):
            raise DescriptionError(f"target must be a regular, non-symlink file: {raw_path}")

        try:
            original = target.read_bytes()
        except OSError as exc:
            raise DescriptionError(f"cannot read target {raw_path!r}: {exc}") from exc
        updated, before_count, after_count = rewrite_description(
            original, manifest[raw_path], raw_path
        )
        before_total += before_count
        after_total += after_count
        if updated != original:
            changes.append(
                Change(
                    relative_path=raw_path,
                    path=target,
                    original=original,
                    updated=updated,
                    mode=stat.S_IMODE(target_lstat.st_mode),
                    before_count=before_count,
                    after_count=after_count,
                )
            )
    return changes, before_total, after_total


def print_plan(changes: list[Change], before_total: int, after_total: int) -> None:
    print("Changed paths:")
    if changes:
        for change in changes:
            print(f"  {change.relative_path}")
    else:
        print("  (none)")
    print(f"Description characters: {before_total} -> {after_total}")


def make_backup(changes: list[Change], backup_root: Path) -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    root = backup_root.expanduser().resolve()
    for candidate in (root, *root.parents):
        if (candidate / ".git").exists():
            raise DescriptionError(f"backup root must be outside a Git worktree: {root}")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup_dir = root / timestamp
    backup_dir.mkdir(mode=0o700)
    os.chmod(backup_dir, 0o700)

    for change in changes:
        destination = backup_dir.joinpath(*PurePosixPath(change.relative_path).parts)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        destination.write_bytes(change.original)
        os.chmod(destination, change.mode)
    return backup_dir


def replace_safely(change: Change) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{change.path.name}.", suffix=".tmp", dir=change.path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(change.updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, change.mode)
        os.replace(temporary_name, change.path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def apply_changes(changes: list[Change], backup_root: Path) -> Path | None:
    if not changes:
        return None
    backup_dir = make_backup(changes, backup_root)
    try:
        for change in changes:
            replace_safely(change)
    except BaseException as exc:
        raise DescriptionError(
            f"write failed after backup was created at {backup_dir}: {exc}"
        ) from exc
    return backup_dir


def main() -> int:
    args = parse_args()
    try:
        manifest = load_manifest(args.manifest.expanduser())
        changes, before_total, after_total = collect_changes(manifest, args.skill_root)
        print_plan(changes, before_total, after_total)
        if args.apply:
            backup_dir = apply_changes(changes, args.backup_root)
            if backup_dir is None:
                print("No files needed changes; no backup was created.")
            else:
                print(f"Backup: {backup_dir}")
                print(f"Applied {len(changes)} change(s).")
        else:
            print("Read-only plan. Pass --apply to write these changes.")
    except DescriptionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
