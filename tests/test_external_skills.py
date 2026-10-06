import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from install_external_skills import install, source_folder


class WorkPackInstallTests(unittest.TestCase):
    def test_installs_grouped_source_and_preserves_later_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source'
            source.mkdir()
            subprocess.run(['git','init','-q',str(source)], check=True)
            entries = {}
            for name in ('alpha','beta'):
                folder = source/'skills'/name
                folder.mkdir(parents=True)
                (folder/'SKILL.md').write_text(f'---\nname: {name}\ndescription: fixture\n---\n')
                entries[name] = {'sourceUrl': str(source), 'skillPath': f'skills/{name}/SKILL.md'}
            subprocess.run(['git','-C',str(source),'add','.'], check=True)
            subprocess.run(['git','-C',str(source),'-c','user.name=Fixture',
                            '-c','user.email=fixture@example.invalid','commit','-qm','fixture'], check=True)
            catalog = root/'catalog.json'
            catalog.write_text(json.dumps({'skills': entries}))
            home, state = root/'home', root/'state'
            first = install(list(entries), catalog=catalog, home=home, state=state)
            self.assertEqual(first, {'alpha':'installed','beta':'installed'})
            self.assertFalse((home/'.agents/skills/alpha/.git').exists())
            self.assertEqual(set(json.loads((state/'external-skills.lock.json').read_text())), set(entries))
            (home/'.agents/skills/alpha/SKILL.md').write_text('user edit')
            second = install(list(entries), catalog=catalog, home=home, state=state)
            self.assertEqual(second, {'alpha':'existing_preserved','beta':'already_installed'})
            self.assertEqual((home/'.agents/skills/alpha/SKILL.md').read_text(), 'user edit')
            (source/'skills/beta/SKILL.md').write_text('new upstream beta')
            subprocess.run(['git','-C',str(source),'add','.'], check=True)
            subprocess.run(['git','-C',str(source),'-c','user.name=Fixture',
                            '-c','user.email=fixture@example.invalid','commit','-qm','update'], check=True)
            refreshed = install(list(entries), catalog=catalog, home=home, state=state, refresh=True)
            self.assertEqual(refreshed['alpha'], 'modified_copy_preserved')
            self.assertTrue(refreshed['beta'].startswith('updated; backup='))
            self.assertEqual((home/'.agents/skills/beta/SKILL.md').read_text(), 'new upstream beta')
            self.assertTrue((Path(refreshed['beta'].split('=',1)[1])/'SKILL.md').is_file())

    def test_refresh_protects_untracked_and_non_skill_user_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source'
            folder = source/'skills/alpha'
            folder.mkdir(parents=True)
            (folder/'SKILL.md').write_text('version one')
            (folder/'notes.md').write_text('reference one')
            subprocess.run(['git','init','-q',str(source)], check=True)
            subprocess.run(['git','-C',str(source),'add','.'], check=True)
            subprocess.run(['git','-C',str(source),'-c','user.name=Fixture',
                            '-c','user.email=fixture@example.invalid','commit','-qm','first'], check=True)
            catalog = root/'catalog.json'
            catalog.write_text(json.dumps({'skills': {'alpha': {'sourceUrl': str(source), 'skillPath': 'skills/alpha/SKILL.md'}}}))
            home, state = root/'home', root/'state'
            install(['alpha'], catalog=catalog, home=home, state=state)
            target = home/'.agents/skills/alpha'
            (target/'notes.md').write_text('user change')
            (folder/'notes.md').write_text('reference two')
            subprocess.run(['git','-C',str(source),'add','.'], check=True)
            subprocess.run(['git','-C',str(source),'-c','user.name=Fixture',
                            '-c','user.email=fixture@example.invalid','commit','-qm','second'], check=True)
            self.assertEqual(install(['alpha'], catalog=catalog, home=home, state=state, refresh=True),
                             {'alpha':'modified_copy_preserved'})
            self.assertEqual((target/'notes.md').read_text(), 'user change')
            (state/'external-skills.lock.json').unlink()
            self.assertEqual(install(['alpha'], catalog=catalog, home=home, state=state, refresh=True),
                             {'alpha':'untracked_copy_preserved'})
            with self.assertRaisesRegex(RuntimeError, 'requires --refresh'):
                install(['alpha'], catalog=catalog, home=home, state=state, replace_existing=True)
            replaced = install(['alpha'], catalog=catalog, home=home, state=state,
                               refresh=True, replace_existing=True)
            backup = Path(replaced['alpha'].split('=', 1)[1])
            self.assertEqual((backup/'notes.md').read_text(), 'user change')
            self.assertEqual((target/'notes.md').read_text(), 'reference two')
            self.assertEqual(json.loads((backup.parent/'receipt.json').read_text())['skill'], 'alpha')
            self.assertEqual(install(['alpha'], catalog=catalog, home=home, state=state, refresh=True),
                             {'alpha':'up_to_date'})

    def test_refresh_can_migrate_a_verified_copy_to_new_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = []
            for index in (1, 2):
                repo = root/f'source-{index}'
                folder = repo/'skills/alpha'
                folder.mkdir(parents=True)
                (folder/'SKILL.md').write_text(f'version {index}')
                subprocess.run(['git','init','-q',str(repo)], check=True)
                subprocess.run(['git','-C',str(repo),'add','.'], check=True)
                subprocess.run(['git','-C',str(repo),'-c','user.name=Fixture',
                                '-c','user.email=fixture@example.invalid','commit','-qm','source'], check=True)
                sources.append(repo)
            catalog = root/'catalog.json'
            home, state = root/'home', root/'state'
            def write_catalog(repo):
                catalog.write_text(json.dumps({'skills': {'alpha': {'sourceUrl': str(repo),
                                                                  'skillPath': 'skills/alpha/SKILL.md'}}}))
            write_catalog(sources[0])
            install(['alpha'], catalog=catalog, home=home, state=state)
            write_catalog(sources[1])
            result = install(['alpha'], catalog=catalog, home=home, state=state, refresh=True)
            self.assertTrue(result['alpha'].startswith('updated; backup='))
            self.assertEqual((home/'.agents/skills/alpha/SKILL.md').read_text(), 'version 2')
            self.assertEqual(json.loads((state/'external-skills.lock.json').read_text())['alpha']['source'], str(sources[1]))

    def test_root_skill_does_not_copy_git_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source'
            source.mkdir()
            (source/'SKILL.md').write_text('root skill')
            subprocess.run(['git','init','-q',str(source)], check=True)
            subprocess.run(['git','-C',str(source),'add','.'], check=True)
            subprocess.run(['git','-C',str(source),'-c','user.name=Fixture',
                            '-c','user.email=fixture@example.invalid','commit','-qm','root'], check=True)
            catalog = root/'catalog.json'
            catalog.write_text(json.dumps({'skills': {'alpha': {'sourceUrl': str(source), 'skillPath': 'SKILL.md'}}}))
            home, state = root/'home', root/'state'
            install(['alpha'], catalog=catalog, home=home, state=state)
            target = home/'.agents/skills/alpha'
            self.assertFalse((target/'.git').exists())
            self.assertEqual(install(['alpha'], catalog=catalog, home=home, state=state, refresh=True),
                             {'alpha':'up_to_date'})

    def test_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                source_folder(Path(directory), '../SKILL.md')


if __name__ == '__main__':
    unittest.main()
