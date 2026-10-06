"""Portable apply checks use disposable homes; never modify the real user home."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('managed', Path(__file__).resolve().parents[1] / 'scripts/apply_managed.py')
managed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(managed)


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.original_root = managed.ROOT
        self.addCleanup(setattr, managed, 'ROOT', self.original_root)
        managed.ROOT = self.root / 'setup'
        for path in ['instructions', 'config', 'skills/example']:
            (managed.ROOT / path).mkdir(parents=True)
        (managed.ROOT / 'instructions/AGENTS.md').write_text('{{HOME}} {{CODEX_HOME}}/working-method.md')
        (managed.ROOT / '11-working-method.md').write_text('routing guide')
        (managed.ROOT / 'config/models.json').write_text('{"families":{"sol":"test-sol"}}')
        (managed.ROOT / 'skills/example/SKILL.md').write_text('---\nname: example\ndescription: Example\n---\n')
        self.home = self.root / 'new user'
        self.coding = self.root / 'projects elsewhere'
        self.codex = self.root / 'custom codex'
        self.backup = self.root / 'backup'

    def run_apply(self, commit):
        return managed.apply(self.home, self.backup, commit, self.codex)

    def test_dry_run_then_portable_apply_and_repeat(self):
        self.assertEqual(len(self.run_apply(False)['changes']), 3)
        self.assertFalse(self.home.exists())
        self.assertFalse(self.coding.exists())
        self.run_apply(True)
        self.assertEqual((self.codex / 'AGENTS.md').read_text(), f'{self.home} {self.codex}/working-method.md')
        self.assertEqual((self.codex / 'working-method.md').read_text(), 'routing guide')
        self.assertEqual((self.codex / 'models.json').read_text(), '{"families":{"sol":"test-sol"}}')
        self.assertFalse(self.coding.exists())
        self.assertFalse((self.home / '.agents/skills/example').exists())
        self.assertEqual(self.run_apply(True)['changes'], [])

    def test_existing_user_instructions_remain_editable(self):
        self.codex.mkdir()
        (self.codex / 'AGENTS.md').write_text('prior user instructions')
        result = self.run_apply(True)
        self.assertEqual((self.codex / 'AGENTS.md').read_text(), 'prior user instructions')
        self.assertEqual(result['preserved'], [str(self.codex/'AGENTS.md')])
        self.assertEqual((self.codex / 'working-method.md').read_text(), 'routing guide')

    def test_user_edited_local_model_guide_is_preserved(self):
        self.codex.mkdir()
        (self.codex / 'working-method.md').write_text('my routing guide')
        result = self.run_apply(True)
        self.assertEqual((self.codex / 'working-method.md').read_text(), 'my routing guide')
        self.assertIn(str(self.codex / 'working-method.md'), result['preserved'])

    def test_user_edited_model_ids_are_preserved(self):
        self.codex.mkdir()
        (self.codex / 'models.json').write_text('{"families":{"sol":"my-model"}}')
        result = self.run_apply(True)
        self.assertEqual((self.codex / 'models.json').read_text(), '{"families":{"sol":"my-model"}}')
        self.assertIn(str(self.codex / 'models.json'), result['preserved'])

    def test_known_legacy_instructions_migrate_with_backup(self):
        self.codex.mkdir()
        old = f'{self.home} {managed.ROOT}/11-working-method.md'
        (self.codex/'AGENTS.md').write_text(old)
        result = self.run_apply(True)
        self.assertEqual((self.codex/'AGENTS.md').read_text(), f'{self.home} {self.codex}/working-method.md')
        self.assertEqual((Path(result['backup'])/'0').read_text(), old)

    def test_foreign_link_is_rejected_before_changes(self):
        self.codex.mkdir()
        foreign = self.root / 'foreign'
        foreign.write_text('keep')
        (self.codex / 'AGENTS.md').symlink_to(foreign)
        with self.assertRaises(RuntimeError):
            self.run_apply(True)
        self.assertEqual(foreign.read_text(), 'keep')
        self.assertFalse(self.coding.exists())

    def test_existing_skill_is_outside_instruction_apply(self):
        skill = self.home / '.agents/skills/example'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('keep')
        self.run_apply(True)
        self.assertEqual((skill / 'SKILL.md').read_text(), 'keep')
        self.assertTrue((self.codex / 'AGENTS.md').exists())

    def test_apply_does_not_change_project_workspace(self):
        self.coding.mkdir()
        marker = self.coding / 'AGENTS.md'
        marker.write_text('private project instruction')
        result = self.run_apply(True)
        self.assertEqual(len(result['changes']), 3)
        self.assertTrue((self.codex/'AGENTS.md').exists())
        self.assertEqual(marker.read_text(), 'private project instruction')


if __name__ == '__main__':
    unittest.main()
