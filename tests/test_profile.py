"""Tests for the profile, its generated schemas and the browser validator.

Run: python3 -I -m unittest discover -s tests   (from the repository root)

Three validators must agree on every example and every deliberate break:
  - the SHACL shapes (pySHACL)
  - the JSON Schema (jsonschema, Draft 2020-12)
  - the browser validator (site_src/validator.js, run in Node)
A valid example rejected by any of them, or a break accepted by any of them, fails the suite.
"""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

import jsonschema  # noqa: E402
import yaml  # noqa: E402
from pyshacl import validate as shacl_validate  # noqa: E402
from rdflib import Graph  # noqa: E402

import generate  # noqa: E402
import ukap  # noqa: E402

P = ukap.load()
FILES = generate.generate(P)
SHAPES = Graph().parse(data=FILES['dcat-uk-ap.shacl.ttl'], format='turtle')
SCHEMA = json.loads(FILES['dcat-uk-ap.schema.json'])
JS = jsonschema.Draft202012Validator(SCHEMA)
INVALID = yaml.safe_load((ROOT / 'tests' / 'fixtures' / 'invalid.yaml').read_text(encoding='utf-8'))
NODE = """
const V = require(process.argv[1]);
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const recs = P.__records; delete P.__records;
process.stdout.write(JSON.stringify(recs.map(r => V.validate(P, r))));
"""


def js_validate(records):
    prof = json.loads(FILES['profile.json'])
    prof['__records'] = records
    out = subprocess.run(['node', '-e', NODE, str(ROOT / 'site_src' / 'validator.js')], input=json.dumps(prof),
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def shacl_ok(record):
    g = ukap.to_graph(P, record)
    conforms, _, text = shacl_validate(g, shacl_graph=SHAPES, allow_warnings=True)
    return conforms, text


class ValidExamples(unittest.TestCase):
    def test_every_example_passes_all_three(self):
        recs = [e['record'] for e in P.examples]
        js = js_validate(recs)
        for e, j in zip(P.examples, js):
            with self.subTest(example=e['key']):
                ok, text = shacl_ok(e['record'])
                self.assertTrue(ok, text)
                self.assertEqual([], [x.message for x in JS.iter_errors(e['record'])])
                self.assertTrue(j['ok'], j['issues'])


class DeliberateBreaks(unittest.TestCase):
    """VER-05: every check is trusted only because a deliberate break proves it fails."""

    def test_every_break_fails_all_three(self):
        js = js_validate([x['record'] for x in INVALID])
        for x, j in zip(INVALID, js):
            with self.subTest(fixture=x['key']):
                ok, _ = shacl_ok(x['record'])
                self.assertFalse(ok, 'SHACL accepted a deliberate break')
                if x.get('json_schema') == 'cannot':
                    self.assertFalse(list(JS.iter_errors(x['record'])), 'fixture says JSON Schema cannot catch this; if it now can, remove the flag')
                else:
                    self.assertTrue(list(JS.iter_errors(x['record'])), 'JSON Schema accepted a deliberate break')
                self.assertFalse(j['ok'], 'browser validator accepted a deliberate break')
                self.assertIn(x['rule'], {i['rule'] for i in j['issues'] if i['level'] == 'error'},
                              f'browser validator did not report rule {x["rule"]}: {j["issues"]}')

    def test_every_rule_has_a_break(self):
        broken = {x['rule'] for x in INVALID}
        for r in P.rules:
            with self.subTest(rule=r['id']):
                self.assertIn(r['id'], broken, f'rule {r["id"]} has no deliberate break in tests/fixtures/invalid.yaml')


class ProfileIntegrity(unittest.TestCase):
    """The loader refuses a broken profile. Each case breaks it on purpose."""

    def broken(self, mutate):
        prof = yaml.safe_load((ROOT / 'profile' / 'dcat-uk-ap.yaml').read_text(encoding='utf-8'))
        cls = yaml.safe_load((ROOT / 'profile' / 'codelists.yaml').read_text(encoding='utf-8'))
        lin = copy.deepcopy(P.lineage)
        ex = copy.deepcopy(P.examples)
        mutate(prof, cls, lin, ex)
        return ukap.Profile(prof, cls, None, lin, ex)

    def assertRefused(self, mutate, needle):
        with self.assertRaises(ukap.ProfileError) as cm:
            self.broken(mutate).check()
        self.assertIn(needle, str(cm.exception))

    def test_unknown_property_in_class(self):
        self.assertRefused(lambda p, c, l, e: p['classes']['Dataset']['properties'].append({'p': 'nope', 'ob': 'O', 'card': '0..1'}), 'unknown property nope')

    def test_mandatory_with_optional_cardinality(self):
        def m(p, c, l, e):
            p['classes']['Dataset']['properties'][0]['card'] = '0..n'
        self.assertRefused(m, 'mandatory but cardinality')

    def test_conditional_without_condition(self):
        def m(p, c, l, e):
            p['classes']['Dataset']['properties'][0].update(ob='C', card='0..n')
        self.assertRefused(m, 'conditional without a condition')

    def test_email_in_guidance(self):
        def m(p, c, l, e):
            p['properties']['title']['guidance'] = 'Write to team@example.org'
        self.assertRefused(m, 'contains an email address')

    def test_unknown_codelist(self):
        def m(p, c, l, e):
            p['properties']['theme']['codelist'] = 'themes-typo'
        self.assertRefused(m, 'unknown codelist')

    def test_backlog_points_at_missing_property(self):
        def m(p, c, l, e):
            l['backlog'][0]['where'].append('prop:ghost')
        self.assertRefused(m, 'unknown property ghost')

    def test_orphan_property(self):
        def m(p, c, l, e):
            p['properties']['orphan'] = {'uri': 'dct:subject', 'label': 'x', 'kind': 'text', 'definition': 'x', 'mem': {'change': 'new'}}
        self.assertRefused(m, 'not used by any class')


class Coverage(unittest.TestCase):
    def test_every_open_issue_is_registered(self):
        # 22 open issues in co-cddo on 6 November 2026 (read through the GitHub API)
        open_issues = {86, 78, 76, 72, 71, 70, 69, 63, 60, 49, 44, 30, 26, 25, 15, 13, 11, 5, 4, 3, 2, 1}
        self.assertTrue(open_issues <= {b['n'] for b in P.lineage['backlog']})

    def test_every_mem_slot_is_mapped(self):
        mem_slots = {'accessService', 'accessRights', 'address', 'alternativeTitle', 'byteSize', 'contactName', 'contactPoint', 'created',
                     'creator', 'description', 'distribution', 'downloadURL', 'email', 'endpointDescription', 'endpointURL', 'identifier',
                     'issued', 'keyword', 'licence', 'mediaType', 'modified', 'publisher', 'relatedResource', 'securityClassification',
                     'servesData', 'serviceStatus', 'serviceType', 'summary', 'telephone', 'theme', 'title', 'updateFrequency', 'version'}
        mapped = set(P.mem_slots())
        self.assertEqual(set(), mem_slots - mapped, 'xGov MEM slots with no DCAT-UK AP property')

    def test_dcat_ap_mandatory_kept(self):
        # DCAT-AP 3.0.1 mandatory properties (verified 6 November 2026). A UK record must be harvestable by European tools.
        need = {'Catalogue': ['publisher', 'description', 'title'], 'CatalogueRecord': ['modified', 'primaryTopic'],
                'Dataset': ['title', 'description'], 'DatasetSeries': ['title', 'description'], 'Distribution': ['accessURL'],
                'DataService': ['title', 'endpointURL'], 'Agent': ['name'], 'Checksum': ['algorithm', 'checksumValue'],
                'Relationship': ['hadRole', 'relation']}
        for ck, props in need.items():
            obs = {x['p']: x['ob'] for x in P.classes[ck]['properties']}
            for pr in props:
                with self.subTest(cls=ck, prop=pr):
                    self.assertEqual('M', obs.get(pr))

    def test_mem_conversion_of_original_example(self):
        mem = yaml.safe_load((ROOT / 'tests' / 'fixtures' / 'mem-dataset.yaml').read_text(encoding='utf-8'))
        prof = json.loads(FILES['profile.json'])
        node = ("const V=require(process.argv[1]);const d=JSON.parse(require('fs').readFileSync(0,'utf8'));"
                "const r=V.fromMem(d.P,d.m);process.stdout.write(JSON.stringify({r:r,v:V.validate(d.P,r.record)}));")
        out = json.loads(subprocess.run(['node', '-e', node, str(ROOT / 'site_src' / 'validator.js')], input=json.dumps({'P': prof, 'm': mem}),
                                        capture_output=True, text=True, check=True).stdout)
        rec = out['r']['record']
        self.assertEqual('eufreq:QUARTERLY', rec['accrualPeriodicity'])
        self.assertEqual('ukcl:access-rights/open', rec['accessRights'])
        self.assertEqual(['ukcl:theme/mapping'], rec['theme'])
        self.assertTrue(out['v']['ok'], out['v']['issues'])


if __name__ == '__main__':
    unittest.main()


class ReadmeCounts(unittest.TestCase):
    """The README is written by hand, so its counts are checked against the source (no hard-coded counts left unchecked)."""

    def test_backlog_counts_in_readme(self):
        import collections
        import re
        c = collections.Counter(b['status'] for b in P.lineage['backlog'])
        text = (ROOT / 'README.md').read_text(encoding='utf-8')
        m = re.search(r'All (\d+) open issues .*?: (\d+) resolved, (\d+) resolved but marked provisional .*?, (\d+) needs the owner', text)
        self.assertIsNotNone(m, 'README backlog sentence not found')
        self.assertEqual((len(P.lineage['backlog']), c['resolved'], c['provisional'], c['owner']), tuple(int(x) for x in m.groups()))
        self.assertEqual(P.lineage['totals']['issues_open'], len(P.lineage['backlog']))
