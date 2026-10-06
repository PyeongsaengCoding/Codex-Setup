"""Core skills become independent user-owned copies after installation."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
spec = importlib.util.spec_from_file_location('core_skills', Path(__file__).resolve().parents[1] / 'scripts/install_core_skills.py')
core_skills = importlib.util.module_from_spec(spec)
if spec.loader is not None:
    spec.loader.exec_module(core_skills)


class CoreSkillTests(unittest.TestCase):
    def test_migrates_source_link_to_independent_copy_and_updates_unmodified_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source'
            skill = source/'example'
            skill.mkdir(parents=True)
            (skill/'SKILL.md').write_text('version 1')
            home, state = root/'home', root/'state'
            target = home/'.agents/skills/example'
            target.parent.mkdir(parents=True)
            target.symlink_to(skill)

            first = core_skills.install(source, home, state)
            self.assertEqual(first['example'], 'updated')
            self.assertFalse(target.is_symlink())
            self.assertEqual((target/'SKILL.md').read_text(), 'version 1')
            (skill/'SKILL.md').write_text('version 2')
            self.assertEqual((target/'SKILL.md').read_text(), 'version 1')

            second = core_skills.install(source, home, state)
            self.assertEqual(second['example'], 'updated')
            self.assertEqual((target/'SKILL.md').read_text(), 'version 2')
            self.assertEqual(core_skills.install(source, home, state), {'example': 'up_to_date'})
            self.assertIn('example', json.loads((state/'core-skills.lock.json').read_text()))

    def test_preserves_user_modified_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source/example'
            source.mkdir(parents=True)
            (source/'SKILL.md').write_text('version 1')
            home, state = root/'home', root/'state'
            core_skills.install(source.parent, home, state)
            target = home/'.agents/skills/example/SKILL.md'
            target.write_text('user revision')
            (source/'SKILL.md').write_text('version 2')
            self.assertEqual(core_skills.install(source.parent, home, state), {'example': 'modified_copy_preserved'})
            self.assertEqual(target.read_text(), 'user revision')

    def test_receipt_restores_previous_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source/example'
            source.mkdir(parents=True)
            (source/'SKILL.md').write_text('version 1')
            home, state = root/'home', root/'state'
            core_skills.install(source.parent, home, state)
            (source/'SKILL.md').write_text('version 2')
            core_skills.install(source.parent, home, state)
            receipt = sorted((state/'core-skill-backups').glob('*/receipt.json'))[-1]
            core_skills.restore(receipt)
            self.assertEqual((home/'.agents/skills/example/SKILL.md').read_text(), 'version 1')
            self.assertEqual(json.loads((state/'core-skills.lock.json').read_text())['example']['files'],
                             core_skills.snapshot(home/'.agents/skills/example'))

    def test_interrupted_swap_keeps_original_and_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source/example'
            source.mkdir(parents=True)
            (source/'SKILL.md').write_text('version 1')
            home, state = root/'home', root/'state'
            core_skills.install(source.parent, home, state)
            (source/'SKILL.md').write_text('version 2')
            target = home/'.agents/skills/example'
            original = Path.rename
            def interrupt(path, destination):
                if path.name == 'example' and path.parent.name.startswith('.codex-core-stage-') and Path(destination) == target:
                    raise KeyboardInterrupt('injected')
                return original(path, destination)
            with patch.object(core_skills.Path, 'rename', interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    core_skills.install(source.parent, home, state)
            self.assertEqual((target/'SKILL.md').read_text(), 'version 1')
            self.assertTrue(list((state/'core-skill-backups').glob('*/receipt.json')))

    def test_receipt_failure_rolls_back_lock_and_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source/example'
            source.mkdir(parents=True)
            (source/'SKILL.md').write_text('version 1')
            home, state = root/'home', root/'state'
            core_skills.install(source.parent, home, state)
            (source/'SKILL.md').write_text('version 2')
            original = core_skills.write_atomic
            def fail_applied(path, data):
                if Path(path).name == 'receipt.json' and data.get('applied'):
                    raise OSError('injected receipt failure')
                return original(path, data)
            with patch.object(core_skills, 'write_atomic', fail_applied):
                with self.assertRaisesRegex(OSError, 'injected'):
                    core_skills.install(source.parent, home, state)
            target = home/'.agents/skills/example'
            self.assertEqual((target/'SKILL.md').read_text(), 'version 1')
            self.assertEqual(json.loads((state/'core-skills.lock.json').read_text())['example']['files'], core_skills.snapshot(target))


if __name__ == '__main__':
    unittest.main()
