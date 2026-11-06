"""Tests for the 1.1 toolkit: sector extensions, quality score and levels, converters, exports, policies and the MCP server.

Run: python3 -I -m unittest discover -s tests   (from the repository root; the MCP test needs a built site: python3 -I tools/build.py)

Each extension's example must pass, and each of its deliberate breaks must fail, in all three validators (SHACL, JSON Schema, browser).
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
PROF = json.loads(FILES['profile.json'])
VJS = str(ROOT / 'site_src' / 'validator.js')


def js(body, data):
    """Run a function body against the browser validator in Node. `V`, `P` and `d` are in scope; return a JSON-able value."""
    src = ("const V=require(process.argv[1]);const x=JSON.parse(require('fs').readFileSync(0,'utf8'));const P=x.P,d=x.d;"
           "process.stdout.write(JSON.stringify((function(){" + body + "})()));")
    out = subprocess.run(['node', '-e', src, VJS], input=json.dumps({'P': PROF, 'd': data}), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def three(eid, rec):
    q = P.with_extensions([eid])
    shapes = Graph().parse(data=FILES[f'extensions/{eid}.shacl.ttl'], format='turtle')
    ok, _, text = shacl_validate(ukap.to_graph(q, rec), shacl_graph=shapes, allow_warnings=True)
    schema = jsonschema.Draft202012Validator(json.loads(FILES[f'extensions/{eid}.schema.json']))
    errs = [e.message for e in schema.iter_errors(rec)]
    j = js('return V.validate(V.withExtensions(P,[d.e]), d.r);', {'e': eid, 'r': rec})
    return ok, text, errs, j


class Extensions(unittest.TestCase):
    def test_examples_pass_all_three(self):
        for eid in P.extensions:
            with self.subTest(extension=eid):
                ok, text, errs, j = three(eid, P.ext_example(eid))
                self.assertTrue(ok, text)
                self.assertEqual([], errs)
                self.assertTrue(j['ok'], j['issues'])

    def test_breaks_fail_all_three(self):
        for eid, e in P.extensions.items():
            for b in e['breaks']:
                with self.subTest(extension=eid, brk=b['key']):
                    ok, _, errs, j = three(eid, P.ext_break(eid, b))
                    self.assertFalse(ok, 'SHACL accepted a deliberate break')
                    self.assertTrue(errs, 'JSON Schema accepted a deliberate break')
                    self.assertIn(b['rule'], {i['rule'] for i in j['issues'] if i['level'] == 'error'}, j['issues'])

    def test_extension_example_needs_its_extension(self):
        # the base profile does not know the health terms, so the browser validator rejects them without the extension
        j = js('return V.validate(P, d);', P.ext_example('health'))
        self.assertIn('S-04', {i['rule'] for i in j['issues']})

    def test_extension_may_not_weaken(self):
        raw = copy.deepcopy(P._raw)
        ext = raw[5]
        ext['extensions'][0]['classes']['Dataset'].append({'p': 'title', 'ob': 'O', 'card': '0..n'})
        q = ukap.Profile(*raw)
        with self.assertRaises(ukap.ProfileError) as cm:
            q.with_extensions([ext['extensions'][0]['id']])
        self.assertIn('would weaken', str(cm.exception))

    def test_unknown_extension_refused(self):
        with self.assertRaises(ukap.ProfileError):
            P.with_extensions(['astrology'])


class Integrity(unittest.TestCase):
    def test_codelist_code_must_be_text(self):
        # D-013: YAML reads the bare code no (Norway) as false
        raw = copy.deepcopy(P._raw)
        raw[1]['jurisdiction']['concepts'][0]['code'] = False
        with self.assertRaises(ukap.ProfileError) as cm:
            ukap.Profile(*raw).check()
        self.assertIn('is not text', str(cm.exception))
        self.assertIn('no', [c['code'] for c in P.codelists['jurisdiction']['concepts']])

    def test_crosswalk_unknown_property_refused(self):
        raw = copy.deepcopy(P._raw)
        q = ukap.Profile(*raw)
        q.crosswalks = copy.deepcopy(P.crosswalks)
        q.crosswalks['ckan']['rows'].append(['ghost', 'x', ''])
        with self.assertRaises(ukap.ProfileError) as cm:
            q.check()
        self.assertIn('unknown property ghost', str(cm.exception))

    def test_unknown_key_with_space_serialises(self):
        # D-014: an unknown key containing a space made Turtle serialisation crash instead of being reported
        rec = dict(P.examples[0]['record'], **{'not a property': 'x'})
        self.assertIn('unknown-not%20a%20property', ukap.to_graph(P, rec).serialize(format='turtle'))

    def test_commonwealth_and_territories_complete(self):
        g = [c for c in P.codelists['jurisdiction']['concepts']]
        self.assertEqual(55, sum(1 for c in g if 'commonwealth' in c['groups']), '56 members including the UK')
        self.assertEqual(14, sum(1 for c in g if 'overseas-territory' in c['groups']))
        self.assertEqual(3, sum(1 for c in g if 'crown-dependency' in c['groups']))


class QualityAndLevels(unittest.TestCase):
    def test_scores(self):
        out = js('return d.map(function(r){return [V.fair(P,r), V.conformance(P,r)];});', [e['record'] for e in P.examples])
        for e, (q, c) in zip(P.examples, out):
            with self.subTest(example=e['key']):
                self.assertEqual(405, q['max'])
                self.assertEqual(q['score'], sum(d['score'] for d in q['dimensions']))
                self.assertGreaterEqual(c['level'], 1, 'every example conforms')

    def test_missing_keywords_lose_thirty_points(self):
        rec = copy.deepcopy(P.examples[0]['record'])
        a = js('return V.fair(P,d).score;', rec)
        rec.pop('keyword')
        b = js('return V.fair(P,d).score;', rec)
        self.assertEqual(30, a - b)

    def test_break_is_level_zero(self):
        rec = copy.deepcopy(P.examples[0]['record'])
        rec.pop('title')
        self.assertEqual(0, js('return V.conformance(P,d).level;', rec))

    def test_weak_checksum_warns_but_conforms(self):
        d = {'class': 'Distribution', 'accessURL': ['https://example.org/f'], 'checksum': {'algorithm': 'spdx:checksumAlgorithm_md5', 'checksumValue': 'ab'}}
        r = js('return V.validate(P,d);', d)
        self.assertTrue(r['ok'])
        self.assertIn('Q-01', {i['rule'] for i in r['issues'] if i['level'] == 'warning'})
        d['checksum']['algorithm'] = 'spdx:checksumAlgorithm_sha384'
        r = js('return V.validate(P,d);', d)
        self.assertNotIn('Q-01', {i['rule'] for i in r['issues']})


class Converters(unittest.TestCase):
    def test_template_round_trip(self):
        out = js('var c=V.fromCSV(P,d);return [c.records, c.records.map(function(r){return V.validate(P,r);})];', FILES['template.csv'])
        recs, res = out
        self.assertEqual(1, len(recs))
        self.assertTrue(res[0]['ok'], res[0]['issues'])
        self.assertEqual(['postcode', 'address', 'location'], recs[0]['keyword'])
        self.assertEqual(generate.TEMPLATE_COLUMNS, FILES['template.csv'].splitlines()[0].split(','))

    def test_csv_quotes_and_commas(self):
        rows = js('return V.parseCSV(d);', 'a,b\n"x, y","say ""hi"""\n')
        self.assertEqual([['a', 'b'], ['x, y', 'say "hi"']], rows)

    def test_openapi_never_copies_email(self):
        oas = {'openapi': '3.1.0', 'info': {'title': 'T', 'version': '1', 'contact': {'name': 'Team', 'email': 'team' + '@' + 'example.org', 'url': 'https://example.org/c'},
                                            'license': {'url': 'http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'}},
               'servers': [{'url': 'https://api.example.org/v1'}], 'components': {'securitySchemes': {'key': {'type': 'apiKey'}}}}
        out = js('return V.fromOpenAPI(P,d);', oas)
        self.assertNotIn('@', json.dumps(out['record']))
        self.assertEqual(['https://api.example.org/v1'], out['record']['endpointURL'])
        self.assertEqual(['https://spec.openapis.org/oas/v3.1.0'], out['record']['conformsTo'])
        self.assertTrue(any('email' in n for n in out['notes']))
        self.assertTrue(any('security' in n for n in out['notes']))

    def test_mem_conversion_still_works(self):
        mem = yaml.safe_load((ROOT / 'tests' / 'fixtures' / 'mem-dataset.yaml').read_text(encoding='utf-8'))
        self.assertTrue(js('return V.validate(P, V.fromMem(P,d).record).ok;', mem))


class Exports(unittest.TestCase):
    def test_schema_org_and_croissant(self):
        out = js('return [V.toSchemaOrg(P,d), V.toCroissant(P,d), V.toTurtle(P,d)];', P.examples[0]['record'])
        sdo, cr, ttl = out
        self.assertEqual('Dataset', sdo['@type'])
        self.assertEqual(P.examples[0]['record']['title'], sdo['name'])
        self.assertEqual('http://mlcommons.org/croissant/1.1', cr['dct:conformsTo'])
        self.assertTrue(all(d['@type'] == 'cr:FileObject' for d in cr['distribution']))
        g = Graph().parse(data=ttl, format='turtle')
        self.assertGreater(len(g), 20)

    def test_turtle_matches_python(self):
        # the browser's Turtle and the build's RDF describe the same triples
        for e in P.examples:
            with self.subTest(example=e['key']):
                ttl = js('return V.toTurtle(P,d);', e['record'])
                a = Graph().parse(data=ttl, format='turtle')
                b = ukap.to_graph(P, e['record'])
                from rdflib.compare import isomorphic
                self.assertTrue(isomorphic(a, b), 'browser Turtle and build RDF differ (D-015)')

    def test_policies_parse(self):
        for name, pol in generate.odrl_policies(P).items():
            with self.subTest(policy=name):
                g = Graph().parse(data=json.dumps(pol), format='json-ld')
                self.assertGreater(len(g), 5)


class MCPServer(unittest.TestCase):
    def test_tools(self):
        prof = ROOT / 'build' / 'test-profile.json'
        prof.parent.mkdir(exist_ok=True)
        prof.write_text(FILES['profile.json'], encoding='utf-8')
        msgs = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}}, {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
                {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'validate_record', 'arguments': {'record': P.examples[0]['record']}}},
                {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'validate_record', 'arguments': {'record': P.ext_example('health'), 'extensions': ['health']}}},
                {'jsonrpc': '2.0', 'id': 5, 'method': 'tools/call', 'params': {'name': 'describe_property', 'arguments': {'name': 'nope'}}},
                {'jsonrpc': '2.0', 'id': 6, 'method': 'no/such'}]
        out = subprocess.run(['node', str(ROOT / 'integrations' / 'mcp' / 'server.js'), '--profile', str(prof)], input='\n'.join(json.dumps(m) for m in msgs) + '\n',
                             capture_output=True, text=True, check=True, timeout=30)
        res = {r['id']: r for r in map(json.loads, out.stdout.splitlines())}
        self.assertEqual({1, 2, 3, 4, 5, 6}, set(res), 'a notification must get no reply')
        self.assertEqual(9, len(res[2]['result']['tools']))
        self.assertTrue(json.loads(res[3]['result']['content'][0]['text'])['validation']['ok'])
        self.assertTrue(json.loads(res[4]['result']['content'][0]['text'])['validation']['ok'])
        self.assertTrue(res[5]['result']['isError'])
        self.assertEqual(-32601, res[6]['error']['code'])


if __name__ == '__main__':
    unittest.main()
