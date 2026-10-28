import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'skills/task-guide/scripts/create_task_guide.py'


class TaskGuideLanguageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='guide-language-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.input = self.directory / 'guide.json'
        self.data = {'title': 'Validation guide', 'scope': ['Preserve literal 來源優先序 and X-7'],
                     'read_by_task': [{'need': 'Identity rule', 'evidence': 'ref/rules.md#identity'}],
                     'source_authority': ['Confirmed source, revision one']}
        self.write_input()

    def write_input(self):
        self.input.write_text(json.dumps(self.data, ensure_ascii=False), encoding='utf-8')

    def invoke(self, *arguments):
        return subprocess.run([sys.executable, '-B', str(SCRIPT), str(self.input), *arguments],
                              capture_output=True, encoding='utf-8', timeout=15)

    def test_default_ai_labels_are_english_without_translating_literals(self):
        original = self.input.read_bytes()
        result = self.invoke('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('## Read by task', result.stdout)
        self.assertIn('## Source authority', result.stdout)
        self.assertIn('Preserve literal 來源優先序 and X-7', result.stdout)
        self.assertNotIn('## 來源優先序', result.stdout)
        self.assertEqual(self.input.read_bytes(), original)

    def test_explicit_human_chinese_labels_retain_the_same_content(self):
        result = self.invoke('--language', 'zh-TW', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('## 依任務讀取', result.stdout)
        self.assertIn('## 來源優先序', result.stdout)
        self.assertIn('Preserve literal 來源優先序 and X-7', result.stdout)

    def test_preview_and_language_change_do_not_overwrite_existing_output(self):
        target = self.directory / 'guide.md'
        preview = self.invoke('--output', str(target), '--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse(target.exists())
        created = self.invoke('--output', str(target))
        self.assertEqual(created.returncode, 0, created.stderr)
        original = target.read_bytes()
        rejected = self.invoke('--output', str(target), '--language', 'zh-TW')
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(target.read_bytes(), original)

    def test_language_does_not_change_allocated_ids_or_input(self):
        example = json.loads((ROOT / 'skills/task-guide/assets/task-guide.example.json').read_text(encoding='utf-8'))
        self.data = example
        self.write_input()
        original = self.input.read_bytes()
        en = self.invoke('--allocate-ids')
        zh = self.invoke('--allocate-ids', '--language', 'zh-TW')
        self.assertEqual(en.returncode, 0, en.stderr)
        self.assertEqual(zh.returncode, 0, zh.stderr)
        self.assertEqual(json.loads(en.stdout), json.loads(zh.stdout))
        self.assertEqual(self.input.read_bytes(), original)

    def test_unsupported_language_is_rejected_without_output(self):
        target = self.directory / 'guide.md'
        result = self.invoke('--output', str(target), '--language', 'invalid')
        self.assertEqual(result.returncode, 2)
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
