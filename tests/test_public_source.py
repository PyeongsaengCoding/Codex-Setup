"""Keep machine and project state out of the public setup source."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PublicSourceTests(unittest.TestCase):
    def test_no_project_workspace_is_bundled(self):
        self.assertFalse((ROOT / 'workspace').exists())

    def test_no_personal_home_or_real_email_in_source(self):
        home = re.compile(r'/Users/(?!<|\{|\$)[A-Za-z0-9._-]+')
        email = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
        for folder in ('instructions', 'scripts', 'skills', 'config', 'inventories'):
            for file in (ROOT / folder).rglob('*'):
                if not file.is_file() or file.suffix in {'.pyc', '.png'}:
                    continue
                text = file.read_text(errors='replace')
                self.assertIsNone(home.search(text), str(file))
                self.assertFalse([value for value in email.findall(text)
                                  if not value.endswith('@example.invalid')], str(file))


if __name__ == '__main__':
    unittest.main()
