"""D-038: no linter ran in CI. These tests keep both linters, pinned, in the Build, check and publish workflow."""
import ast
import json
import re
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


def _reimports(source):
    """Modules imported at the top of a file and imported again inside a function or class."""
    tree = ast.parse(source)
    top = {a.asname or a.name for n in tree.body if isinstance(n, ast.Import) for a in n.names}
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Import):
                    found |= {f'{a.asname or a.name} (line {inner.lineno})' for a in inner.names if (a.asname or a.name) in top}
    return sorted(found)


class NoReimports(unittest.TestCase):
    """D-049: CodeQL alerts 48 and 49 found provenance imported again inside test functions; ruff has no rule for it."""

    def test_no_module_is_imported_twice(self):
        skip = {'node_modules', '.git', 'site', '_site', 'dist'}
        for path in ROOT.rglob('*.py'):
            if skip & set(path.relative_to(ROOT).parts):
                continue
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertEqual(_reimports(path.read_text(encoding='utf-8')), [])

    def test_negative_a_reimport_is_caught(self):
        self.assertEqual(_reimports('import os\n\ndef f():\n    import os\n'), ['os (line 4)'])
        self.assertEqual(_reimports('import os\n\ndef f():\n    import sys\n'), [])


def _unhashed(text):
    """Requirements in a pip lock file that carry no --hash (pip-compile puts the hashes on continuation lines)."""
    found, current, hashed = [], None, False
    for line in text.splitlines() + ['']:
        if line and not line.startswith((' ', '#')):
            if current and not hashed:
                found.append(current)
            current, hashed = line.split('==')[0].strip(' \\'), '--hash=' in line
        elif '--hash=' in line:
            hashed = True
        elif not line and current:
            if not hashed:
                found.append(current)
            current = None
    return found


def _top_level_writes(workflow):
    """Write scopes granted to the whole workflow, outside any job."""
    if re.search(r'^permissions: read-all$', workflow, re.M):
        return []
    m = re.search(r'^permissions:\n((?:  .*\n)+)', workflow, re.M)
    return re.findall(r'^  ([a-z-]+): write', m.group(1), re.M) if m else ['(no top-level permissions block)']


class SupplyChain(unittest.TestCase):
    """D-050: Scorecard (alerts 33-36, 46) found pip installing unpinned transitive dependencies, and CodeQL's workflow
    granted security-events: write to the whole workflow (alert 31). Every Python dependency is now pinned and hashed,
    every install enforces the hashes, and write scopes are granted per job only."""

    def test_every_python_dependency_is_hashed(self):
        for name in ('requirements.txt', 'requirements-linkml.txt'):
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding='utf-8')
                self.assertIn('pip-compile', text)
                self.assertEqual(_unhashed(text), [])

    def test_installs_enforce_the_hashes(self):
        for wf in sorted((ROOT / '.github' / 'workflows').glob('*.yml')):
            for line in wf.read_text(encoding='utf-8').splitlines():
                if re.search(r'pip install\b.*-r ', line):
                    with self.subTest(workflow=wf.name, line=line.strip()):
                        self.assertIn('--require-hashes', line)

    def test_the_two_locks_agree(self):
        pins = lambda p: dict(re.findall(r'^([A-Za-z0-9_.-]+)==(\S+)', (ROOT / p).read_text(encoding='utf-8'), re.M))
        a, b = pins('requirements.txt'), pins('requirements-linkml.txt')
        self.assertEqual({k: (a[k], b[k]) for k in a.keys() & b.keys() if a[k] != b[k]}, {})

    def test_no_workflow_grants_write_to_every_job(self):
        for wf in sorted((ROOT / '.github' / 'workflows').glob('*.yml')):
            with self.subTest(workflow=wf.name):
                self.assertEqual(_top_level_writes(wf.read_text(encoding='utf-8')), [])

    def test_negatives(self):
        self.assertEqual(_unhashed('attrs==1.0 \\\n    --hash=sha256:ab\nrdflib==7.0\n'), ['rdflib'])
        self.assertEqual(_top_level_writes('on: push\npermissions:\n  contents: read\n  security-events: write\njobs:\n'), ['security-events'])
        self.assertEqual(_top_level_writes('on: push\npermissions:\n  contents: read\njobs:\n'), [])
        self.assertEqual(_top_level_writes('on: push\npermissions: write-all\njobs:\n'), ['(no top-level permissions block)'])


def _imprecise_asserts(source):
    """assertTrue or assertFalse wrapped round a single comparison, which hides both values when it fails."""
    out = []
    for n in ast.walk(ast.parse(source)):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ('assertTrue', 'assertFalse')
                and n.args and isinstance(n.args[0], ast.Compare) and len(n.args[0].ops) == 1):
            out.append(n.lineno)
    return out


class NoImpreciseAsserts(unittest.TestCase):
    """D-053: CodeQL alert 50 found assertTrue(a >= b) in a test added the same day D-051 fixed the same kind of finding
    (alert 5). D-051 relied on CodeQL alone, which only reports after a merge; this check runs before."""

    def test_no_assert_hides_a_comparison(self):
        for path in sorted((ROOT / 'tests').glob('*.py')):
            with self.subTest(path=path.name):
                self.assertEqual(_imprecise_asserts(path.read_text(encoding='utf-8')), [])

    def test_negative_a_wrapped_comparison_is_caught(self):
        self.assertEqual(_imprecise_asserts('self.assertTrue(len(x) >= 2)\nself.assertTrue(any(y))\nself.assertFalse(a in b)\n'), [1, 3])

