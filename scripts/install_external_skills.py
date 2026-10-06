"""Install reviewed external skills with recoverable, explicit replacements."""
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, tempfile
from pathlib import Path, PurePosixPath
from setup_runtime import ROOT, state_root, write_json


def source_folder(checkout, raw_path):
    path = PurePosixPath(raw_path)
    if path.is_absolute() or '..' in path.parts or path.name != 'SKILL.md':
        raise RuntimeError('Invalid skill source path: '+raw_path)
    source = (checkout/Path(*path.parts)).parent.resolve()
    if not source.is_relative_to(checkout.resolve()) or not (source/'SKILL.md').is_file():
        raise RuntimeError('Skill source missing or outside checkout: '+raw_path)
    for current, dirs, files in os.walk(source):
        dirs[:] = [name for name in dirs if name != '.git']
        if any((Path(current)/name).is_symlink() for name in dirs+files):
            raise RuntimeError('Skill source contains a symlink: '+raw_path)
    return source


def folder_snapshot(folder, *, source=False):
    result = {}
    for current, dirs, files in os.walk(folder, followlinks=False):
        if source:
            dirs[:] = [name for name in dirs if name != '.git']
        for name in dirs+files:
            path = Path(current)/name
            if path.is_symlink():
                raise RuntimeError('Skill folder contains a symlink: '+str(path))
            if path.is_file():
                result[str(path.relative_to(folder))] = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mode & 0o777)
    return result


def install(names, *, catalog, home, state, refresh=False, replace_existing=False):
    if replace_existing and not refresh:
        raise RuntimeError('--replace-existing requires --refresh')
    entries = json.loads(Path(catalog).read_text())['skills']
    unknown = sorted(set(names)-set(entries))
    if unknown:
        raise RuntimeError('Unknown work-pack skill: '+', '.join(unknown))
    if any(not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name) for name in names):
        raise RuntimeError('Invalid skill name')
    state = Path(state)
    lockfile = state/'external-skills.lock.json'
    lock = json.loads(lockfile.read_text()) if lockfile.exists() else {}
    target_root = Path(home)/'.agents/skills'
    results = {}
    with tempfile.TemporaryDirectory(prefix='codex-work-packs-') as temp:
        checkouts = {}
        for name in names:
            item = entries[name]
            target = target_root/name
            if target.is_symlink():
                results[name] = 'existing_link_preserved'
                continue
            if target.exists() and not refresh:
                recorded = lock.get(name)
                digest = hashlib.sha256((target/'SKILL.md').read_bytes()).hexdigest() if (target/'SKILL.md').is_file() else None
                results[name] = 'already_installed' if recorded and recorded.get('sha256') == digest else 'existing_preserved'
                continue
            recorded = lock.get(name)
            if recorded and recorded.get('source') != item['sourceUrl'] and not refresh:
                raise RuntimeError('Source changed since installation: '+name)
            revision = item.get('ref') if refresh else recorded['commit'] if recorded else item.get('ref')
            key = (item['sourceUrl'], revision)
            if key not in checkouts:
                checkout = Path(temp)/str(len(checkouts))
                subprocess.run(['git','clone','--quiet','--depth','1',item['sourceUrl'],str(checkout)],check=True)
                if revision:
                    subprocess.run(['git','-C',str(checkout),'fetch','--quiet','--depth','1','origin',revision],check=True)
                    subprocess.run(['git','-C',str(checkout),'checkout','--quiet','--detach',revision],check=True)
                checkouts[key] = checkout
            checkout = checkouts[key]
            source = source_folder(checkout,item['skillPath'])
            target_root.mkdir(parents=True,exist_ok=True)
            commit = subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip()
            next_lock = {'source':item['sourceUrl'],'commit':commit,'path':item['skillPath'],
                         'sha256':hashlib.sha256((source/'SKILL.md').read_bytes()).hexdigest()}
            if target.exists():
                if not target.is_dir():
                    results[name] = 'existing_preserved'
                    continue
                current = folder_snapshot(target)
                if current == folder_snapshot(source,source=True):
                    lock[name] = next_lock
                    write_json(lockfile,lock)
                    results[name] = 'up_to_date'
                    continue
                if not recorded and not replace_existing:
                    results[name] = 'untracked_copy_preserved'
                    continue
                if recorded and not replace_existing:
                    old_key = (recorded['source'],recorded['commit'])
                    if old_key not in checkouts:
                        old_checkout = Path(temp)/str(len(checkouts))
                        subprocess.run(['git','clone','--quiet','--depth','1',recorded['source'],str(old_checkout)],check=True)
                        subprocess.run(['git','-C',str(old_checkout),'fetch','--quiet','--depth','1','origin',recorded['commit']],check=True)
                        subprocess.run(['git','-C',str(old_checkout),'checkout','--quiet','--detach',recorded['commit']],check=True)
                        checkouts[old_key] = old_checkout
                    old_source = source_folder(checkouts[old_key],recorded['path'])
                    if current != folder_snapshot(old_source,source=True):
                        results[name] = 'modified_copy_preserved'
                        continue
                backup = state/'external-skill-backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')/name
                backup.parent.mkdir(parents=True,exist_ok=True)
                with tempfile.TemporaryDirectory(prefix='.codex-skill-stage-',dir=target_root) as stagedir:
                    stage = Path(stagedir)/name
                    shutil.copytree(source,stage,ignore=shutil.ignore_patterns('.git'))
                    if folder_snapshot(stage) != folder_snapshot(source,source=True):
                        raise RuntimeError('Staged skill differs from upstream: '+name)
                    target.rename(backup)
                    try:
                        stage.rename(target)
                        if folder_snapshot(target) != folder_snapshot(source,source=True):
                            raise RuntimeError('Installed skill differs from upstream: '+name)
                        lock[name] = next_lock
                        write_json(lockfile,lock)
                        write_json(backup.parent/'receipt.json',{
                            'skill':name,'backup':str(backup),'source':item['sourceUrl'],
                            'commit':commit,'previous_files':len(current),'installed_files':len(folder_snapshot(target))})
                    except Exception:
                        if target.exists(): shutil.rmtree(target)
                        backup.rename(target)
                        if recorded is None: lock.pop(name,None)
                        else: lock[name] = recorded
                        write_json(lockfile,lock)
                        raise
                results[name] = 'updated; backup='+str(backup)
            else:
                shutil.copytree(source,target,ignore=shutil.ignore_patterns('.git'))
                lock[name] = next_lock
                write_json(lockfile,lock)
                results[name] = 'installed'
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names',nargs='*')
    parser.add_argument('--all',action='store_true',help='install all reviewed work-pack skills')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--refresh',action='store_true',help='check newest upstream and update only verified unmodified copies')
    parser.add_argument('--replace-existing',action='store_true',help='back up and replace reviewed existing copies; requires --refresh')
    parser.add_argument('--catalog',type=Path,default=ROOT/'inventories/external-skills.json')
    parser.add_argument('--home',type=Path,default=Path.home())
    parser.add_argument('--state',type=Path)
    args = parser.parse_args()
    entries = json.loads(args.catalog.read_text())['skills']
    if args.all and args.names:
        parser.error('Choose names or --all')
    names = list(entries) if args.all else args.names
    if not names:
        parser.error('Provide skill names or --all')
    if not args.apply:
        for name in names:
            item = entries[name]
            print(name,item['sourceUrl'],item['skillPath'])
        return
    state = args.state or state_root(args.home)
    print(json.dumps(install(names,catalog=args.catalog,home=args.home,state=state,
                             refresh=args.refresh,replace_existing=args.replace_existing),ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
