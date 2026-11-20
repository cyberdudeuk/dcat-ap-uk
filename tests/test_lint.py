"""D-038: no linter ran in CI. These tests keep both linters, pinned, in the Build, check and publish workflow."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Lint(unittest.TestCase):
    def test_workflow_runs_both_linters(self):
        wf = (ROOT / '.github' / 'workflows' / 'pages.yml').read_text(encoding='utf-8')
        self.assertIn('ruff check .', wf)
        self.assertIn('npx eslint .', wf)

    def test_linters_are_pinned_and_configured(self):
        self.assertIn('ruff==', (ROOT / 'requirements.txt').read_text(encoding='utf-8'))
        dev = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))['devDependencies']
        self.assertRegex(dev.get('eslint', ''), r'^\d+\.\d+\.\d+$')
        self.assertTrue((ROOT / 'ruff.toml').exists())



def _no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup:
        raise ValueError(f'repeated key(s): {", ".join(dup)}')
    return dict(pairs)


class NoDuplicateKeys(unittest.TestCase):
    """D-041: parallel Dependabot merges left package.json with two eslint and two globals entries."""

    def test_every_json_file_has_unique_keys(self):
        skip = {'node_modules', '.git', '_site', 'dist'}
        for path in ROOT.rglob('*.json'):
            if skip & set(path.relative_to(ROOT).parts):
                continue
            with self.subTest(path=str(path.relative_to(ROOT))):
                json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_no_duplicates)

    def test_catches_the_merged_package_json(self):
        merged = '{"devDependencies": {"eslint": "9.39.5", "globals": "17.14.0", "eslint": "10.14.0", "globals": "16.5.0"}}'
        with self.assertRaisesRegex(ValueError, 'eslint, globals'):
            json.loads(merged, object_pairs_hook=_no_duplicates)


if __name__ == '__main__':
    unittest.main()
