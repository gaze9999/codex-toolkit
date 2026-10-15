"""The compatibility publisher must never bypass the draft/platform CI flow."""
import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scripts import release


class ReleasePublicationTests(unittest.TestCase):
    def test_legacy_publisher_cannot_push_or_create_a_release(self):
        with patch.object(release, 'run') as command, patch.object(release.subprocess, 'run') as process:
            for tag in ('v0.4.2', 'v1.0.0', 'v12.34.56'):
                with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, 'draft Release'):
                    release.publish(tag)
            command.assert_not_called()
            process.assert_not_called()

    def test_old_cli_returns_actionable_migration_without_prompting(self):
        with patch.object(sys, 'argv', ['release.py', 'publish', 'v0.4.2']), \
                patch('builtins.input') as prompt, patch.object(release, 'run') as command, \
                contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(release.main(), 1)
            self.assertIn('python-tools-release.yml', error.getvalue())
            self.assertIn('aggregate version Tag', error.getvalue())
            prompt.assert_not_called()
            command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
