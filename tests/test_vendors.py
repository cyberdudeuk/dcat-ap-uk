"""Vendor connectors (ADR 0021): the register in content/vendors.yaml, the weaver's vendor models and the add-on kits."""
import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

import build  # noqa: E402
from test_toolkit import P, js  # noqa: E402

VD = yaml.safe_load((ROOT / 'content' / 'vendors.yaml').read_text(encoding='utf-8'))
MODELS = ('collibra', 'openmetadata', 'datahub', 'unity', 'dataplex', 'dataworld', 'atlas')
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')


class Fake:
    """Enough of the site builder to run its vendor checks without building."""
    WEAVE_MODELS = build.Site.WEAVE_MODELS
    KITS = build.Site.KITS
    vendor_problems = build.Site.vendor_problems
    vendor_kits = build.Site.vendor_kits

    def __init__(self, vd):
        self.vd, self.p = vd, P


class Register(unittest.TestCase):
    def test_register_is_whole(self):
        self.assertEqual([], Fake(VD).vendor_problems())

    def test_each_break_is_caught(self):
        def broken(f):
            vd = copy.deepcopy(VD)
            f(vd)
            return Fake(vd).vendor_problems()
        cases = {
            'unknown property in a crosswalk': lambda v: v['vendors'][0]['crosswalk'].append(['noSuchProperty', 'x', '']),
            'repository without a commit': lambda v: v['vendors'][0]['repos'][0].pop('commit'),
            'crosswalk without a verified model': lambda v: v['vendors'][0]['model'].update(prov='K'),
            'leader without a source': lambda v: v['reports'][0]['leaders'][0].update(source='http://x'),
            'report that does not exist': lambda v: v['vendors'][0]['reports'].append('no-such-report'),
            'weave that does not exist': lambda v: v['vendors'][0].update(weave='nosuch'),
            'no crosswalk and no reason': lambda v: [x.pop('gap') for x in v['vendors'] if x['id'] == 'alation'],
            'an email address': lambda v: v['vendors'][0].update(extend='write to someone@example.org'),
            'AI offer without a source': lambda v: v['vendors'][0]['ai'].pop('source'),
            'a shortened commit (D-034)': lambda v: v['vendors'][0]['repos'][0].update(commit=v['vendors'][0]['repos'][0]['commit'][:12]),
            'a Claude entry with a shortened commit (D-034)': lambda v: v['vendors'][0]['claude'][0]['repo'].update(commit='17b7ae3b4852'),
            'a Claude entry with no tools or skills': lambda v: v['vendors'][0]['claude'][0].pop('skills'),
            'a Claude entry of unknown type': lambda v: v['vendors'][0]['claude'][0].update(type='app'),
        }
        for name, f in cases.items():
            with self.subTest(break_=name):
                self.assertTrue(broken(f), name + ' was not caught')

    def test_crosswalk_agrees_with_the_weaver(self):
        # The YAML says what the JS does: every native field the weaver maps is in that vendor's crosswalk, with the same path.
        spec = js('var o={};Object.keys(V.vendors).forEach(function(k){o[k]=V.vendors[k].fields.map(function(f){return [f[0],f[1].join(".")];});});return o;', None)
        for x in VD['vendors']:
            if not x.get('crosswalk'):
                continue
            rows = {(r[0], r[1].replace('[].', '.').replace('attributes["Description"]', 'attributes.Description')) for r in x['crosswalk']}
            for prop, path in spec[x['weave']]:
                with self.subTest(vendor=x['id'], prop=prop):
                    self.assertTrue(any(r[0] == prop and (r[1] == path or r[1].startswith(path)) for r in rows) or x['weave'] == 'atlas',
                                    f'{prop} -> {path} is woven but not in the {x["id"]} crosswalk')

    def test_ranked_vendors_come_from_a_report(self):
        for x in VD['vendors']:
            if x['kind'] == 'ranked':
                self.assertTrue(x['reports'], x['id'])


class CitedCommits(unittest.TestCase):
    # D-034: a commit ID padded with invented characters looked valid. The checker fetches each ID from GitHub.
    def setUp(self):
        import subprocess
        try:
            subprocess.run(['git', 'ls-remote', 'https://github.com/atlanhq/agent-toolkit', 'HEAD'], check=True, capture_output=True, timeout=30)
        except Exception:
            self.skipTest('github.com is not reachable here; CI runs tools/check_vendor_repos.py')

    def test_a_padded_commit_fails(self):
        import check_vendor_repos as cvr
        real = VD['vendors'][0]['claude'][0]['repo']
        self.assertTrue(cvr.exists(real['repo'], real['commit']))
        self.assertFalse(cvr.exists(real['repo'], real['commit'][:12] + 'a' * 28))
        self.assertFalse(cvr.exists(real['repo'], real['commit'][:12]))


class Weaving(unittest.TestCase):
    def test_round_trip_loses_nothing(self):
        for e in P.examples:
            rec = e['record']
            for m in MODELS:
                with self.subTest(example=e['key'], model=m):
                    back = js('var o=V.weave(P,"ukap",d.m,d.r).out; return V.weave(P,d.m,"ukap",o).record;', {'m': m, 'r': rec})
                    self.assertEqual(json.loads(json.dumps(rec)), back)

    def test_the_documented_command_line_step_works(self):
        # The connectors page tells people to run the CLI with --from <model>; prove each vendor format checks as DCAT-AP-UK.
        import subprocess
        import tempfile
        rec = next(e['record'] for e in P.examples if e['key'] == 'dataset-postcodes')
        for m in MODELS:
            with self.subTest(model=m), tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
                json.dump(js('return V.weave(P,"ukap",d.m,d.r).out;', {'m': m, 'r': rec}), f)
                f.flush()
                out = subprocess.run(['node', str(ROOT / 'integrations' / 'cli' / 'validate.js'), '--from', m, f.name], capture_output=True, text=True)
                self.assertEqual(0, out.returncode, out.stdout + out.stderr)
                self.assertIn('pass', out.stdout)

    def test_people_are_not_carried(self):
        src = {'openmetadata': {'displayName': 'A table', 'owners': [{'name': 'a.person'}]},
               'datahub': {'name': 'A dataset', 'owners': ['urn:li:corpuser:someone']},
               'unity': {'name': 'a_table', 'owner': 'someone', 'comment': 'x'},
               'collibra': [{'resourceType': 'Asset', 'name': 'A', 'responsibilities': [{'user': 'someone'}]}],
               'dataworld': {'title': 'A', 'owner': 'someone'}}
        for m, x in src.items():
            with self.subTest(model=m):
                w = js('return V.weave(P,d.m,"ukap",d.x);', {'m': m, 'x': x})
                self.assertNotIn('someone', json.dumps(w['record']))
                self.assertTrue(any('people' in n for n in w['notes']))

    def test_no_email_survives(self):
        w = js('return V.weave(P,"openmetadata","ukap",d);', {'displayName': 'A', 'description': 'Write to a.person@example.org', 'extension': {'title': 'x'}})
        self.assertIsNone(EMAIL.search(json.dumps(w['record'])))


class Kits(unittest.TestCase):
    def test_every_kit_defines_every_dataset_property(self):
        kits = Fake(VD).vendor_kits()
        props = [x['p'] for x, _ in P.class_props('Dataset')]
        self.assertEqual(set(kits), set(build.Site.KITS))
        for k, body in kits.items():
            text = body if isinstance(body, str) else json.dumps(body)
            for p_ in props:
                with self.subTest(kit=k, prop=p_):
                    self.assertRegex(text, r'["\s.]' + re.escape(p_) + r'\b')

    def test_kit_names_match_the_weaver(self):
        # Unity and DataHub keep the bag flat with the dcat_ap_uk. prefix; their kits must use the same names.
        kits = Fake(VD).vendor_kits()
        out = js('return V.weave(P,"ukap","unity",d).out;', next(e['record'] for e in P.examples if e['key'] == 'dataset-postcodes'))
        for k in out['properties']:
            if k not in ('dcat_ap_uk.class', 'dcat_ap_uk.id'):
                self.assertIn(k, kits['unity-properties']['properties'])
        dh = {x['id'] for x in yaml.safe_load(kits['datahub-structured-properties'])}
        out = js('return V.weave(P,"ukap","datahub",d).out;', next(e['record'] for e in P.examples if e['key'] == 'dataset-postcodes'))
        for k in out['customProperties']:
            if k not in ('dcat_ap_uk.class', 'dcat_ap_uk.id'):
                self.assertIn(k, dh)


if __name__ == '__main__':
    unittest.main()
