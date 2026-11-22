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


def _split_flow_values(text):
    """D-043: an unquoted comma inside a {key: value} flow mapping ends the value; the rest becomes a key with no value,
    so the page shows the statement cut short. Return every such orphan key (an explicit `key: null` is not flagged)."""
    import yaml
    found = []

    def walk(node):
        if isinstance(node, yaml.MappingNode):
            for k, v in node.value:
                if node.flow_style and isinstance(v, yaml.ScalarNode) and v.value == '' and v.style is None:
                    found.append(f'line {k.start_mark.line + 1}: {k.value!r}')
                walk(v)
        elif isinstance(node, yaml.SequenceNode):
            for v in node.value:
                walk(v)
    walk(yaml.compose(text))
    return found


class NoSplitFlowValues(unittest.TestCase):
    def test_no_yaml_file_has_a_value_split_at_a_comma(self):
        for p in sorted(ROOT.glob('**/*.y*ml')):
            if 'node_modules' in p.parts or '.git' in p.parts:
                continue
            with self.subTest(file=str(p.relative_to(ROOT))):
                self.assertEqual(_split_flow_values(p.read_text(encoding='utf-8')), [], 'quote values that contain a comma')

    def test_catches_the_published_split(self):
        # The FIPS label as it was on main: published as "FIPS 203".
        self.assertEqual(len(_split_flow_values("- {id: fips, label: FIPS 203, 204 and 205, group: policy}\n")), 1)
        self.assertEqual(_split_flow_values("- {id: fips, label: 'FIPS 203, 204 and 205', mem: null}\n"), [])
