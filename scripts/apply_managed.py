"""Apply managed common files with portable paths. Default: read-only plan."""
import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render(source, home, codex_home=None):
    values = {'{{HOME}}': str(home),
              '{{SETUP_ROOT}}': str(ROOT), '{{CODEX_HOME}}': str(codex_home or Path(home)/'.codex')}
    text = source.read_text()
    shell = text.startswith('#!/bin/zsh')
    for key, value in values.items():
        if shell:
            for char in ['\\', '"', '$', '`']:
                value = value.replace(char, '\\' + char)
        text = text.replace(key, value)
    return text.encode()


def targets(home, codex_home):
    return [(ROOT / 'instructions/AGENTS.md', codex_home / 'AGENTS.md', 'user_instruction'),
            (ROOT / '11-working-method.md', codex_home / 'working-method.md', 'user_instruction'),
            (ROOT / 'config/models.json', codex_home / 'models.json', 'user_instruction')]


def apply(home, backup_root, commit=False, codex_home=None):
    home = Path(home).resolve()
    codex_home = Path(codex_home or home / '.codex').resolve()
    changes = []
    preserved = []
    for src, dst, kind in targets(home, codex_home):
        if kind == 'link':
            if os.path.lexists(dst):
                if dst.is_symlink() and dst.resolve() == src.resolve():
                    continue
                if dst.is_dir() and not dst.is_symlink():
                    source_files = {str(f.relative_to(src)): f.read_bytes() for f in src.rglob('*') if f.is_file()}
                    target_files = {str(f.relative_to(dst)): f.read_bytes() for f in dst.rglob('*') if f.is_file()}
                    if source_files == target_files:
                        continue
                raise RuntimeError('Existing skill target is not our managed link: ' + dst.name)
            data = None
        else:
            if dst.is_symlink():
                raise RuntimeError('Unexpected file symlink; inspect before replacing: ' + str(dst))
            data = render(src, home, codex_home)
            if dst.exists() and dst.read_bytes() == data and (not os.access(src, os.X_OK) or os.access(dst, os.X_OK)):
                continue
            if kind == 'user_instruction' and dst.exists():
                legacy = data.replace(str(codex_home/'working-method.md').encode(),
                                      str(ROOT/'11-working-method.md').encode())
                if dst.read_bytes() != legacy:
                    preserved.append(str(dst))
                    continue
        changes.append((src, dst, kind, data))
    result = {'apply': commit, 'codex_home': str(codex_home),
              'changes': [str(d) for _, d, _, _ in changes], 'preserved': preserved}
    if not commit or not changes:
        return result
    backup_root = Path(backup_root).resolve()
    backup = backup_root / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True, mode=0o700)
    backup_root.chmod(0o700)
    receipt = []
    # Persist all recovery data before the first target mutation.
    for i, (src, dst, kind, data) in enumerate(changes):
        old = backup / str(i)
        existed = dst.exists()
        old_mode = dst.stat().st_mode & 0o777 if existed else None
        if existed:
            old.write_bytes(dst.read_bytes())
            old.chmod(0o600)
        receipt.append({'target': str(dst), 'kind': kind, 'backup': str(old) if existed else None,
                        'previous_mode': old_mode,
                        'before_sha256': hashlib.sha256(old.read_bytes()).hexdigest() if existed else None,
                        'applied_sha256': hashlib.sha256(data).hexdigest() if data is not None else None,
                        'link_target': str(src) if kind == 'link' else None, 'applied': False})
    p = backup / 'receipt.json'
    def journal():
        tmp = backup / 'receipt.tmp'
        tmp.write_text(json.dumps(receipt, indent=2)); tmp.chmod(0o600)
        os.replace(tmp, p)
    journal()
    for i, (src, dst, kind, data) in enumerate(changes):
        old_mode = receipt[i]['previous_mode']
        dst.parent.mkdir(parents=True, exist_ok=True)
        if kind == 'link':
            dst.symlink_to(src)
        else:
            temp = dst.with_name(dst.name + '.setup-tmp')
            created_temp = False
            try:
                with temp.open('xb') as fh:
                    created_temp = True
                    fh.write(data)
                temp.chmod(old_mode if old_mode is not None else (0o700 if os.access(src, os.X_OK) else 0o600))
                if os.access(src, os.X_OK):
                    temp.chmod(temp.stat().st_mode | 0o100)
                os.replace(temp, dst)
            finally:
                if created_temp and temp.exists(): temp.unlink()
        receipt[i]['applied'] = True
        journal()
    result['backup'] = str(backup)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ['CODEX_HOME']) if os.environ.get('CODEX_HOME') else None)
    parser.add_argument('--backup-root', type=Path)
    args = parser.parse_args()
    print(json.dumps(apply(args.home, args.backup_root or args.home / 'Downloads/Codex-Setup-Backups', args.apply, args.codex_home), ensure_ascii=False, indent=2))
