"""Tests for 1.2: the weaver, the lineage graph, the standards map, the conformance kit, the CLI, the reference API and lock-in content.

Run: python3 -I -m unittest discover -s tests   (the kit, lineage and API tests use a built site: python3 -I tools/build.py)
"""
import json
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

import yaml  # noqa: E402

from test_toolkit import FILES, P, PROF, js  # noqa: E402

SITE = ROOT / 'site'
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')


def built():
    if not (SITE / 'downloads' / 'conformance-kit.json').exists():
        subprocess.run([sys.executable, '-I', str(ROOT / 'tools' / 'build.py')], check=True, capture_output=True)


class Weaver(unittest.TestCase):
    def test_every_reader_and_writer(self):
        built()
        html = (SITE / 'weaver.html').read_text(encoding='utf-8')
        samples = {m.group(1): json.loads(m.group(2).replace('<\\/', '</')) for m in re.finditer(r'<script type="application/json" id="w-sample-([a-z]+)">(.*?)</script>', html, re.S)}
        self.assertEqual({'ukap', 'mem', 'ckan', 'dcatus', 'schemaorg', 'dc', 'ddi'}, set(samples))
        writers = js('return V.writers;', None)
        for fr, rec in samples.items():
            for to in writers:
                with self.subTest(source=fr, target=to):
                    w = js('return V.weave(P, d.f, d.t, d.r);', {'f': fr, 't': to, 'r': rec})
                    self.assertTrue(any(m[1] for m in w['mapIn']), 'no thread was woven')
                    self.assertIsNone(EMAIL.search(json.dumps(w['out'])), 'an email address was carried')
                    self.assertTrue(all(m[0] for m in w['mapOut']))

    def test_round_trip_keeps_title_and_licence(self):
        rec = next(e['record'] for e in P.examples if e['key'] == 'dataset-postcodes')
        for to in ('ckan', 'dcatus', 'schemaorg'):
            back = {'ckan': 'ckan', 'dcatus': 'dcatus', 'schemaorg': 'schemaorg'}[to]
            r = js('var o=V.weave(P,"ukap",d.t,d.r).out; return V.weave(P,d.b,"ukap",o).record;', {'t': to, 'b': back, 'r': rec})
            with self.subTest(model=to):
                self.assertEqual(rec['title'], r['title'])
                self.assertTrue(r.get('licence'), 'licence lost on the round trip')

    def test_mem_sample_has_no_email_on_the_site(self):
        built()
        self.assertIsNone(EMAIL.search((SITE / 'weaver.html').read_text(encoding='utf-8')))

    def test_no_shadowed_functions(self):
        # D-017: a weaver helper named finish() replaced the validator's own finish(), so nested objects crashed validation
        src = (ROOT / 'site_src' / 'validator.js').read_text(encoding='utf-8')
        names = re.findall(r'^  function ([A-Za-z_]\w*)\(', src, re.M)
        self.assertEqual(sorted(set(n for n in names if names.count(n) > 1)), [], 'two top-level functions share a name')
        rec = next(e['record'] for e in P.examples if e['key'] == 'dataset-postcodes')
        self.assertTrue(js('return V.validate(P,d).ok;', rec))


class Lineage(unittest.TestCase):
    def test_graph_is_whole(self):
        built()
        g = json.loads((SITE / 'downloads' / 'lineage.json').read_text(encoding='utf-8'))
        ids = {n['id'] for n in g['nodes']}
        for a, b in g['edges']:
            self.assertIn(a, ids)
            self.assertIn(b, ids)
        for k in P.props:
            with self.subTest(prop=k):
                self.assertIn('prop:' + k, ids)
                self.assertTrue(any(b == 'prop:' + k for a, b in g['edges']), f'{k} has no source in the lineage')
        for kind in ('standard', 'issue', 'test', 'rule', 'extension', 'crosswalk', 'defect', 'mem'):
            self.assertIn(kind, g['kinds'])

    def test_every_rule_traces_to_a_test(self):
        g = json.loads((SITE / 'downloads' / 'lineage.json').read_text(encoding='utf-8'))
        for r in P.rules:
            with self.subTest(rule=r['id']):
                self.assertTrue(any(a == 'rule:' + r['id'] and b.startswith('test:') for a, b in g['edges']))


class Standards(unittest.TestCase):
    def test_links_name_known_standards_and_relations(self):
        sd = yaml.safe_load((ROOT / 'content' / 'standards.yaml').read_text(encoding='utf-8'))
        ids = {s['id'] for s in sd['standards']}
        self.assertEqual(len(ids), len(sd['standards']), 'duplicate standard id')
        groups = {g['id'] for g in sd['groups']}
        for s in sd['standards']:
            self.assertIn(s['group'], groups)
        for a, r, b in sd['links']:
            with self.subTest(link=(a, r, b)):
                self.assertIn(a, ids)
                self.assertIn(b, ids)
                self.assertIn(r, sd['relations'])
        linked = {a for a, r, b in sd['links']} | {b for a, r, b in sd['links']}
        self.assertEqual(set(), ids - linked, 'a standard with no relationship')

    def test_schedule_covers_every_standard(self):
        built()
        html = (SITE / 'lockin.html').read_text(encoding='utf-8')
        sd = yaml.safe_load((ROOT / 'content' / 'standards.yaml').read_text(encoding='utf-8'))
        for s in sd['standards']:
            if s['group'] != 'tool':
                self.assertIn(s['label'].replace('&', '&amp;'), html, f'{s["label"]} missing from the schedule')
        self.assertTrue((SITE / 'downloads' / 'contract-clauses.md').exists())


class ConformanceKit(unittest.TestCase):
    def test_kit_verdicts(self):
        built()
        man = json.loads((SITE / 'downloads' / 'conformance-kit.json').read_text(encoding='utf-8'))
        cases = [dict(c, record=json.loads((SITE / 'downloads' / 'conformance' / c['file']).read_text(encoding='utf-8'))) for c in man['cases']]
        out = js('return d.map(function(c){var Q=c.extensions.length?V.withExtensions(P,c.extensions):P;var r=V.validate(Q,c.record);'
                 'return [c.id,c.expect,r.ok,r.issues.filter(function(i){return i.level==="error";}).map(function(i){return i.rule;}),c.rule||null];});', cases)
        for cid, expect, ok, rules, rule in out:
            with self.subTest(case=cid):
                if expect == 'pass':
                    self.assertTrue(ok)
                else:
                    self.assertFalse(ok)
                    self.assertIn(rule, rules)
        self.assertGreater(len(out), 40)


class CommandLine(unittest.TestCase):
    def test_cli_exit_codes(self):
        built()
        prof = str(SITE / 'downloads' / 'profile.json')
        ok = subprocess.run(['node', str(ROOT / 'integrations' / 'cli' / 'validate.js'), '--profile', prof, str(SITE / 'downloads' / 'conformance' / 'pass-dataset-postcodes.json')], capture_output=True, text=True)
        self.assertEqual(0, ok.returncode, ok.stdout + ok.stderr)
        bad = subprocess.run(['node', str(ROOT / 'integrations' / 'cli' / 'validate.js'), '--profile', prof, '--format', 'github', str(SITE / 'downloads' / 'conformance' / 'fail-missing-title.json')], capture_output=True, text=True)
        self.assertEqual(1, bad.returncode)
        self.assertIn('::error', bad.stdout)

    def test_action_metadata(self):
        a = yaml.safe_load((ROOT / 'action.yml').read_text(encoding='utf-8'))
        self.assertEqual('composite', a['runs']['using'])
        self.assertIn('files', a['inputs'])


class ReferenceAPI(unittest.TestCase):
    def test_endpoints(self):
        built()
        s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
        proc = subprocess.Popen(['node', str(ROOT / 'integrations' / 'http' / 'server.js'), '--profile', str(SITE / 'downloads' / 'profile.json'), '--port', str(port)], stdout=subprocess.PIPE, text=True)
        try:
            proc.stdout.readline()
            base = f'http://127.0.0.1:{port}'
            h = json.load(urllib.request.urlopen(base + '/health', timeout=5))
            self.assertEqual(P.meta['version'], h['version'])
            rec = next(e['record'] for e in P.examples if e['key'] == 'dataset-postcodes')
            req = urllib.request.Request(base + '/validate', data=json.dumps(rec).encode(), method='POST')
            self.assertTrue(json.load(urllib.request.urlopen(req, timeout=5))['validation']['ok'])
            req = urllib.request.Request(base + '/weave?from=ukap&to=dcatus', data=json.dumps(rec).encode(), method='POST')
            self.assertEqual(rec['title'], json.load(urllib.request.urlopen(req, timeout=5))['out']['title'])
            api = json.loads((SITE / 'downloads' / 'integration-api.openapi.json').read_text(encoding='utf-8'))
            self.assertEqual({'/health', '/profile', '/codelists/{name}', '/validate', '/score', '/weave'}, set(api['paths']))
        finally:
            proc.terminate()
            proc.wait(5)


if __name__ == '__main__':
    unittest.main()


class MemPortalFeatures(unittest.TestCase):
    """Features brought over from the xGov MEM portal stay complete."""

    def test_every_class_page_has_a_diagram_linking_its_ranges(self):
        for ck, c in P.classes.items():
            html = (SITE / f'class-{re.sub(r"[^a-z0-9]+", "-", ck.lower()).strip("-")}.html').read_text(encoding='utf-8')
            self.assertIn('id="diagram"', html, ck)
            for x, prop in P.class_props(ck):
                r = prop.get('range')
                if r in P.classes and r != ck:
                    self.assertRegex(html, r'<svg class="graph cls"[\s\S]*class-' + re.escape(r.lower()), f'{ck} diagram misses {r}')

    def test_types_page_lists_every_kind_used(self):
        html = (SITE / 'types.html').read_text(encoding='utf-8')
        for k in {v['kind'] for v in P.props.values()}:
            self.assertIn(f'id="t-{k}"', html)

    def test_licence_page_and_feedback_link(self):
        self.assertIn('Open Government Licence v3.0', (SITE / 'licence.html').read_text(encoding='utf-8'))
        self.assertIn('Suggest a change to this page', (SITE / 'index.html').read_text(encoding='utf-8'))
