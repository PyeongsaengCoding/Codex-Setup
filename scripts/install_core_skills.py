"""Install repository skills as independent, recoverable user skill copies."""
import datetime
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from setup_runtime import ROOT, state_root


def write_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.'+path.name+'-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def snapshot(folder):
    result = {}
    for current, dirs, files in os.walk(folder, followlinks=False):
        for name in dirs + files:
            path = Path(current)/name
            if path.is_symlink():
                raise RuntimeError('Skill contains a symlink: '+str(path))
            if path.is_file():
                result[str(path.relative_to(folder))] = [hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mode & 0o777]
    return result


def install(source_root=ROOT/'skills', home=None, state=None):
    source_root = Path(source_root).resolve()
    home = Path(home or Path.home())
    state = Path(state or state_root(home))
    target_root = home/'.agents/skills'
    lockfile = state/'core-skills.lock.json'
    lock = json.loads(lockfile.read_text()) if lockfile.exists() else {}
    result = {}
    for source in sorted(source_root.iterdir()):
        if not (source/'SKILL.md').is_file():
            continue
        name = source.name
        target = target_root/name
        wanted = snapshot(source)
        if target.is_symlink():
            if target.resolve() != source:
                result[name] = 'foreign_link_preserved'
                continue
            current = wanted
        elif target.exists():
            if not target.is_dir():
                result[name] = 'existing_preserved'
                continue
            current = snapshot(target)
            if current == wanted:
                if lock.get(name) != {'files': wanted}:
                    lock[name] = {'files': wanted}
                    write_atomic(lockfile, lock)
                result[name] = 'up_to_date'
                continue
            if current != lock.get(name, {}).get('files'):
                result[name] = 'modified_copy_preserved'
                continue
        else:
            current = None
        target_root.mkdir(parents=True, exist_ok=True)
        backup = state/'core-skill-backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')/name
        previous_record = lock.get(name)
        with tempfile.TemporaryDirectory(prefix='.codex-core-stage-', dir=target_root) as directory:
            staging = Path(directory)
            incoming = staging/name
            shutil.copytree(source, incoming)
            if snapshot(incoming) != wanted:
                raise RuntimeError('Staged core skill differs from source: '+name)
            backup.parent.mkdir(parents=True, exist_ok=True)
            contents = backup.parent/'previous-contents'
            if current is not None:
                shutil.copytree(source if target.is_symlink() else target, contents)
                if snapshot(contents) != current:
                    raise RuntimeError('Core skill backup differs from installed copy: '+name)
            receipt_path = backup.parent/'receipt.json'
            receipt = {'skill': name, 'target': str(target), 'backup': str(backup) if current is not None else None,
                       'contents': str(contents) if current is not None else None,
                       'previous_files': current, 'previous_record': previous_record,
                       'installed_files': wanted, 'applied': False}
            write_atomic(receipt_path, receipt)
            moved_original = False
            installed_new = False
            try:
                if os.path.lexists(target):
                    target.rename(backup)
                    moved_original = True
                incoming.rename(target)
                installed_new = True
                if snapshot(target) != wanted:
                    raise RuntimeError('Installed core skill differs from source: '+name)
                lock[name] = {'files': wanted}
                write_atomic(lockfile, lock)
                receipt['applied'] = True
                write_atomic(receipt_path, receipt)
            except BaseException:
                if installed_new and target.exists():
                    shutil.rmtree(target)
                if moved_original and os.path.lexists(backup):
                    backup.rename(target)
                if previous_record is None:
                    lock.pop(name, None)
                else:
                    lock[name] = previous_record
                write_atomic(lockfile, lock)
                receipt['rolled_back'] = True
                write_atomic(receipt_path, receipt)
                raise
        result[name] = 'updated' if current is not None else 'installed'
    return result


def restore(receipt_path):
    receipt_path = Path(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    if 'installed_files' not in receipt:
        raise RuntimeError('Legacy backup needs manual review before restore')
    target = Path(receipt['target'])
    if os.path.lexists(target):
        if target.is_symlink() or not target.is_dir() or snapshot(target) != receipt['installed_files']:
            raise RuntimeError('Installed core skill changed since backup: '+receipt['skill'])
    elif receipt.get('applied'):
        raise RuntimeError('Installed core skill is missing: '+receipt['skill'])
    contents = Path(receipt['contents']) if receipt['contents'] else None
    if contents is not None and (not contents.is_dir() or snapshot(contents) != receipt['previous_files']):
        raise RuntimeError('Core skill backup is missing or changed: '+receipt['skill'])
    state = receipt_path.parents[2]
    lockfile = state/'core-skills.lock.json'
    lock = json.loads(lockfile.read_text()) if lockfile.exists() else {}
    before_lock = lock.get(receipt['skill'])
    with tempfile.TemporaryDirectory(prefix='.codex-core-restore-', dir=target.parent) as directory:
        staging = Path(directory)
        incoming = staging/'original'
        if contents is not None:
            shutil.copytree(contents, incoming)
        displaced = receipt_path.parent/'displaced-installed'
        if os.path.lexists(displaced):
            raise RuntimeError('Restore already has a displaced target: '+receipt['skill'])
        moved_installed = False
        restored_previous = False
        try:
            if os.path.lexists(target):
                target.rename(displaced)
                moved_installed = True
            if contents is not None:
                incoming.rename(target)
                restored_previous = True
            if receipt['previous_record'] is None:
                lock.pop(receipt['skill'], None)
            else:
                lock[receipt['skill']] = receipt['previous_record']
            write_atomic(lockfile, lock)
            receipt['restored'] = True
            write_atomic(receipt_path, receipt)
        except BaseException:
            if restored_previous and target.exists():
                shutil.rmtree(target)
            if moved_installed and os.path.lexists(displaced):
                displaced.rename(target)
            if before_lock is None:
                lock.pop(receipt['skill'], None)
            else:
                lock[receipt['skill']] = before_lock
            write_atomic(lockfile, lock)
            raise
        if os.path.lexists(displaced):
            if displaced.is_symlink():
                displaced.unlink()
            else:
                shutil.rmtree(displaced)
    return {'restored': str(target)}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('action', nargs='?', choices=('install', 'restore'), default='install')
    parser.add_argument('--backup-receipt', type=Path)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--state', type=Path)
    args = parser.parse_args()
    if args.action == 'restore':
        if not args.backup_receipt:
            parser.error('--backup-receipt is required for restore')
        result = restore(args.backup_receipt)
    else:
        result = install(home=args.home, state=args.state)
    print(json.dumps(result, ensure_ascii=False, indent=2))
