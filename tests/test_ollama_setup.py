import io
import json
import sys
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import setup_runtime as setup


class OllamaSetupTests(unittest.TestCase):
    def test_existing_model_is_verified_without_reinstall(self):
        def urlopen(request, timeout=5):
            url = request.full_url if hasattr(request, 'full_url') else request
            if url.endswith('/api/version'):
                body = {'version': '0.35.1'}
            elif url.endswith('/api/tags'):
                body = {'models': [{'name': 'nomic-embed-text:latest'}]}
            elif url.endswith('/api/embed'):
                body = {'embeddings': [[0.1, 0.2]]}
            else:
                raise AssertionError(url)
            return io.BytesIO(json.dumps(body).encode())

        with (
            patch.object(setup.shutil, 'which', side_effect=lambda name: '/opt/homebrew/bin/' + name),
            patch.object(setup, 'run') as command,
            patch.object(urllib.request, 'urlopen', side_effect=urlopen),
        ):
            result = setup.ensure_ollama('nomic-embed-text')

        self.assertEqual(result['embedding_dimensions'], 2)
        self.assertFalse(result['installed'])
        self.assertFalse(result['model_pulled'])
        command.assert_not_called()

    def test_missing_ollama_and_model_are_installed_by_setup(self):
        state = {'ollama': False, 'model': False}
        calls = []

        def which(name):
            if name == 'brew':
                return '/opt/homebrew/bin/brew'
            if name == 'ollama' and state['ollama']:
                return '/opt/homebrew/bin/ollama'
            return None

        def command(args, **kwargs):
            calls.append(args)
            if args == ['/opt/homebrew/bin/brew', 'install', 'ollama']:
                state['ollama'] = True
            if args == ['/opt/homebrew/bin/ollama', 'pull', 'nomic-embed-text']:
                state['model'] = True

        def urlopen(request, timeout=5):
            url = request.full_url if hasattr(request, 'full_url') else request
            if url.endswith('/api/version'):
                body = {'version': '0.35.1'}
            elif url.endswith('/api/tags'):
                body = {'models': [{'name': 'nomic-embed-text:latest'}] if state['model'] else []}
            elif url.endswith('/api/embed'):
                body = {'embeddings': [[0.1, 0.2]]}
            else:
                raise AssertionError(url)
            return io.BytesIO(json.dumps(body).encode())

        with (
            patch.object(setup.shutil, 'which', side_effect=which),
            patch.object(setup, 'run', side_effect=command),
            patch.object(urllib.request, 'urlopen', side_effect=urlopen),
        ):
            result = setup.ensure_ollama('nomic-embed-text')

        self.assertTrue(result['installed'])
        self.assertTrue(result['model_pulled'])
        self.assertEqual(result['embedding_dimensions'], 2)
        self.assertIn(['/opt/homebrew/bin/brew', 'install', 'ollama'], calls)
        self.assertIn(['/opt/homebrew/bin/ollama', 'pull', 'nomic-embed-text'], calls)

    def test_stopped_ollama_service_is_started(self):
        state = {'running': False}
        calls = []

        def command(args, **kwargs):
            calls.append(args)
            if args == ['/opt/homebrew/bin/brew', 'services', 'start', 'ollama']:
                state['running'] = True

        def urlopen(request, timeout=5):
            if not state['running']:
                raise urllib.error.URLError('connection refused')
            url = request.full_url if hasattr(request, 'full_url') else request
            if url.endswith('/api/version'):
                body = {'version': '0.35.1'}
            elif url.endswith('/api/tags'):
                body = {'models': [{'name': 'nomic-embed-text:latest'}]}
            elif url.endswith('/api/embed'):
                body = {'embeddings': [[0.1, 0.2]]}
            else:
                raise AssertionError(url)
            return io.BytesIO(json.dumps(body).encode())

        with (
            patch.object(setup.shutil, 'which', side_effect=lambda name: '/opt/homebrew/bin/' + name),
            patch.object(setup, 'run', side_effect=command),
            patch.object(urllib.request, 'urlopen', side_effect=urlopen),
        ):
            result = setup.ensure_ollama('nomic-embed-text')

        self.assertTrue(result['service_started'])
        self.assertIn(['/opt/homebrew/bin/brew', 'services', 'start', 'ollama'], calls)


if __name__ == '__main__':
    unittest.main()
