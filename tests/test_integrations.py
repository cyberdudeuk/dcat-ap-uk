"""Tests for 1.2: the weaver, the lineage graph, the standards map, the conformance kit, the CLI, the reference API and lock-in content.

Run: python3 -I -m unittest discover -s tests   (the kit, lineage and API tests use a built site: python3 -I tools/build.py)
"""
import copy
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
        self.assertEqual({'ukap', 'mem', 'ckan', 'dcatus', 'schemaorg', 'dc', 'ddi', 'atlas'}, set(samples))
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
    def test_every_standard_is_drawn_on_the_map(self):
        """D-028: a group missing from the layout could not be drawn; adding its first standard broke the build."""
        sd = yaml.safe_load((ROOT / 'content' / 'standards.yaml').read_text(encoding='utf-8'))
        html = (SITE / 'standards.html').read_text(encoding='utf-8')
        drawn = set(re.findall(r'class="sm-n[^"]*" data-id="([^"]+)"', html))
        self.assertEqual([], sorted({s['id'] for s in sd['standards']} - drawn - {'ukap'}))

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


class RepoAsCode(unittest.TestCase):
    """D-023: a label colour of digits only was read by YAML as a number and broke the labels workflow."""

    def check(self, labels):
        bad = [l['name'] for l in labels if not (isinstance(l['color'], str) and re.fullmatch(r'[0-9a-f]{6}', l['color']))]
        return bad

    def test_every_label_colour_is_six_hex_digits_as_text(self):
        self.assertEqual(self.check(yaml.safe_load((ROOT / '.github' / 'labels.yml').read_text(encoding='utf-8'))), [])

    def test_check_catches_a_numeric_colour(self):
        self.assertEqual(self.check(yaml.safe_load('- {name: x, color: 942514, description: y}')), ['x'])


class RequirementsStream(unittest.TestCase):
    """RQ-18 and ADR 0015: the requirements catalogue is public, so its shape allows only kinds of community, never people,
    meetings or documents; and every claim of status is backed by something checkable."""

    RQ = yaml.safe_load((ROOT / 'content' / 'requirements.yaml').read_text(encoding='utf-8'))
    KEYS = {'id', 'theme', 'statement', 'rationale', 'communities', 'evidence', 'sources', 'priority', 'layer', 'acceptance', 'validation',
            'traces', 'status', 'gap', 'added'}

    def shape_problems(self, reqs):
        rq, bad = self.RQ, []
        cm = {c['id'] for c in rq['communities']}
        for r in reqs:
            extra = set(r) - self.KEYS
            if extra:
                bad.append(f'{r["id"]}: fields not allowed in a public catalogue: {sorted(extra)}')
            if not set(r['communities']) <= cm:
                bad.append(f'{r["id"]}: raised by something that is not a kind of community: {sorted(set(r["communities"]) - cm)}')
            if not set(r['evidence']) <= set(rq['evidence']):
                bad.append(f'{r["id"]}: unknown evidence code')
            if r['status'] == 'partly' and not r.get('gap'):
                bad.append(f'{r["id"]}: partly met but says no gap')
            if r['status'] == 'met' and r['validation'].lower().startswith('planned'):
                bad.append(f'{r["id"]}: met, but its validation is only planned')
            if r['status'] == 'controlled' and r['validation'] != 'Outside this repository':
                bad.append(f'{r["id"]}: controlled, but claims validation here')
            for k in r['traces'].get('properties', []):
                if k not in P.props:
                    bad.append(f'{r["id"]}: traces unknown property {k}')
            for s in r.get('sources', []):
                if s not in {x['id'] for x in rq['public_sources']}:
                    bad.append(f'{r["id"]}: unknown public source {s}')
        return bad

    def test_catalogue_is_well_formed_and_public_safe(self):
        self.assertEqual([], self.shape_problems(self.RQ['requirements']))

    def test_shape_check_catches_a_named_raiser_and_an_unsupported_claim(self):
        r = dict(self.RQ['requirements'][0], raised_by='a named person', communities=['a named forum'], status='partly')
        r.pop('gap', None)
        msgs = ' '.join(self.shape_problems([r]))
        self.assertIn('fields not allowed', msgs)
        self.assertIn('not a kind of community', msgs)
        self.assertIn('says no gap', msgs)

    def test_every_requirement_is_on_the_page_and_in_the_lineage(self):
        html = (SITE / 'requirements.html').read_text(encoding='utf-8')
        lg = json.loads((SITE / 'downloads' / 'lineage.json').read_text(encoding='utf-8'))
        ids = {n['id'] for n in lg['nodes']}
        for r in self.RQ['requirements']:
            self.assertIn(f'id="{r["id"].lower()}"', html)
            self.assertIn('req:' + r['id'], ids, f'{r["id"]} is not linked to anything in the lineage')


class AtlasReader(unittest.TestCase):
    """RQ-21: the Apache Atlas (Purview) reader carries what the entity holds and invents nothing."""

    def weave(self, ent):
        return js('return V.weave(P,"atlas","ukap",d);', {'entity': ent})

    def test_dates_keywords_and_classification(self):
        r = self.weave({'typeName': 'azure_sql_table', 'guid': 'g-1', 'labels': ['a'], 'sensitivityLabel': 'OFFICIAL - SENSITIVE',
                        'attributes': {'name': 'T', 'description': 'D', 'createTime': 1767225600000}})['record']
        self.assertEqual('2026-01-01', r['issued'])
        self.assertEqual(['a'], r['keyword'])
        self.assertEqual('ukcl:security-classification/official-sensitive', r['securityClassification'])

    def test_nothing_is_invented(self):
        out = self.weave({'typeName': 'azure_sql_table', 'guid': 'g-2', 'attributes': {'name': 'T', 'qualifiedName': 'mssql://server/db/t'}})
        r = out['record']
        for k in ('description', 'licence', 'language', 'securityClassification', 'accessRights', 'publisher', 'contactPoint', 'distribution'):
            self.assertNotIn(k, r, f'{k} was invented')
        self.assertTrue(any('not assumed to be OFFICIAL' in n for n in out['notes']))

    def test_above_official_and_personal_are_flagged_not_mapped(self):
        out = self.weave({'typeName': 'x', 'sensitivityLabel': 'Highly Confidential', 'classifications': [{'typeName': 'Microsoft.Personal.Name'}],
                          'attributes': {'name': 'T', 'owner': 'someone'}})
        self.assertNotIn('securityClassification', out['record'])
        self.assertNotIn('personalData', out['record'])
        self.assertNotIn('someone', json.dumps(out['record']))
        text = ' '.join(out['notes'])
        self.assertIn('above OFFICIAL', text)
        self.assertIn('personal data', text)
        self.assertIn('names people', text)


class GeospatialServices(unittest.TestCase):
    """RQ-24: with the geospatial extension, a data service must say which standards (such as OGC APIs) it conforms to."""

    def test_service_without_conformance_fails_and_with_it_passes(self):
        svc = copy.deepcopy([e for e in P.examples if e['record']['class'] == 'DataService'][0]['record'])
        svc.pop('conformsTo', None)
        r = js('return V.validate(V.withExtensions(P,["geospatial"]), d);', svc)
        self.assertIn('conformsTo', {i['prop'] for i in r['issues'] if i['rule'] == 'M-01'})
        svc['conformsTo'] = ['http://www.opengis.net/spec/ogcapi-features-1/1.0']
        r = js('return V.validate(V.withExtensions(P,["geospatial"]), d);', svc)
        self.assertNotIn('conformsTo', {i['prop'] for i in r['issues'] if i['rule'] == 'M-01'})


class W3idRedirects(unittest.TestCase):
    """O-17: the prepared w3id.org redirects point only at files and anchors the portal publishes."""

    def test_every_redirect_target_exists(self):
        ht = (ROOT / 'docs' / 'w3id' / 'dcat-ap-uk' / '.htaccess').read_text(encoding='utf-8')
        targets = set(re.findall(r'https://cyberdudeuk\.github\.io/dcat-ap-uk/([^\s#$]*)', ht))
        missing = sorted(t for t in targets if t and not (SITE / t).exists())
        self.assertEqual([], missing)
        html = (SITE / 'codelists.html').read_text(encoding='utf-8')
        for k in P.codelists:
            if k not in ('organisations',):
                self.assertIn(f'id="cl-{k}"', html, k)
        ext = (SITE / 'extensions.html').read_text(encoding='utf-8')
        for k in P.extensions:
            self.assertIn(f'id="ext-{k}"', ext, k)


class SiteAddressAfterRename(unittest.TestCase):
    """O-16: the repository was renamed dcat-ap-uk. The old Pages address no longer serves the site, so no source may link to it."""

    OLD = ('github.io/dcat-' + 'uk-ap', 'github.com/cyberdudeuk/dcat-' + 'uk-ap')  # split so this file does not match itself

    def test_no_old_address(self):
        found = []
        for path in ROOT.rglob('*'):
            if not path.is_file() or any(part in ('.git', 'site', 'node_modules') for part in path.parts):
                continue
            if path.suffix not in ('.py', '.js', '.yaml', '.yml', '.md', '.cff', '.json', '.html', '.txt') and path.name != '.htaccess':
                continue
            text = path.read_text(encoding='utf-8', errors='ignore')
            found += [f'{path.relative_to(ROOT)}: {o}' for o in self.OLD if o in text]
        self.assertEqual(found, [], 'old repository address still linked')



class ReuseAcrossGovernment(unittest.TestCase):
    """The reuse page: every asset is a public repository with a kind, an owner, a use and a date; the test counts add up;
    nothing linked to national security work is named (scan of the GitHub Repos Asset Catalogue, 6 November 2026)."""

    RU = yaml.safe_load((ROOT / 'content' / 'reuse.yaml').read_text(encoding='utf-8'))

    def test_assets_are_complete(self):
        groups = {g['id'] for g in self.RU['groups']}
        for a in self.RU['assets']:
            with self.subTest(asset=a['id']):
                self.assertIn(a['group'], groups)
                self.assertTrue(a['url'].startswith('https://github.com/'))
                for k in ('name', 'owner', 'what', 'use', 'licence'):
                    self.assertTrue(a.get(k), k)
                self.assertRegex(a['updated'], r'^\d{4}-\d{2}-\d{2}$')
                self.assertIn(a['prov'], ('V', 'P', 'S'))

    def test_counts_add_up(self):
        t = self.RU['test']
        self.assertEqual(sum(r['count'] for r in t['results']), t['total'])

    def test_no_restricted_names(self):
        text = (ROOT / 'content' / 'reuse.yaml').read_text(encoding='utf-8')
        for bad in ('GC' + 'HQ', 'DE' + 'AG', 'DI' + 'WG', 'ND' + 'SDG', 'SIT' + 'CEN', 'FV' + 'EY'):
            self.assertNotIn(bad, text)

    def test_page_is_built_and_linked(self):
        built()
        html = (SITE / 'reuse.html').read_text(encoding='utf-8')
        for anchor in ('assets', 'dsa', 'evidence', 'test', 'method'):
            self.assertIn(f'id="{anchor}"', html)
        self.assertIn('href="reuse.html"', (SITE / 'index.html').read_text(encoding='utf-8'))


class OrganisationsFresh(unittest.TestCase):
    """D-031: the organisation list missed the July 2026 machinery of government change (DSIT closed) because it was read from
    a snapshot. It must be no more than 120 days older than the release, and is refreshed with import_orgs.py --govuk."""

    def test_read_recently(self):
        from datetime import date
        o = json.loads((ROOT / 'profile' / 'organisations.json').read_text(encoding='utf-8'))
        as_of = date.fromisoformat(str(P.meta['as_of']))
        self.assertLessEqual((as_of - date.fromisoformat(o['read'])).days, 120, 'organisations.json is stale: run tools/import_orgs.py --govuk')

    def test_closed_department_is_closed(self):
        o = {x['slug']: x for x in json.loads((ROOT / 'profile' / 'organisations.json').read_text(encoding='utf-8'))['orgs']}
        self.assertEqual(o['department-for-science-innovation-and-technology']['status'], 'closed')
        self.assertEqual(o['department-for-digital-culture-media-and-sport']['status'], 'live')


class ChangeFlags(unittest.TestCase):
    """New and Updated flags (the Data Quality Commons pattern): fingerprints count words only, the baseline names a
    release in the change log, and the built site flags what changed (7 November 2026)."""

    def setUp(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        import sections
        self.S = sections

    def test_words_count_markup_does_not(self):
        a = self.S.sections('<h2 id="x">Title</h2><p>Some <strong>words</strong>.</p>')
        b = self.S.sections('<h2 id="x" class="new">Title<span class="secflag new">New</span></h2><p class="lede">Some words.</p><svg><text>9</text></svg>')
        c = self.S.sections('<h2 id="x">Title</h2><p>Some other words.</p>')
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_compare(self):
        self.assertEqual(self.S.compare(None, {'a': '1'}), {'a': 'new'})
        self.assertEqual(self.S.compare({'a': '1', 'b': '2'}, {'a': '1', 'b': '3', 'c': '4'}), {'b': 'updated', 'c': 'new'})

    def test_baseline_names_a_release(self):
        b = self.S.load_baseline()
        self.assertTrue(b['since'])
        self.assertIn(f'## [{b["since"]}]', (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'))
        self.assertGreater(len(b['pages']), 40)

    def test_site_is_flagged(self):
        built()
        ch = json.loads((SITE / 'downloads' / 'changes-since.json').read_text(encoding='utf-8'))
        self.assertEqual(ch['pages']['reuse']['page'], 'new')
        wn = (SITE / 'whats-new.html').read_text(encoding='utf-8')
        self.assertIn('id="changed"', wn)
        self.assertIn('href="reuse.html"', wn)


class StatusPage(unittest.TestCase):
    """The Status page (the DAM playbooks pattern) with the five self-* routines (the catalogue's pattern)."""

    def test_status_page_and_json(self):
        built()
        html = (SITE / 'status.html').read_text(encoding='utf-8')
        for a in ('routines', 'verification', 'assessment', 'staleness', 'health', 'repair'):
            self.assertIn(f'id="{a}"', html)
        st = json.loads((SITE / 'downloads' / 'status.json').read_text(encoding='utf-8'))
        self.assertEqual(len(st['routines']), 5)
        self.assertEqual(len(st['checks']), len(re.findall(r'"""C-\d\d ', (ROOT / 'tools' / 'check_site.py').read_text(encoding='utf-8'))))
        self.assertTrue(all(st['repository_files'].values()), st['repository_files'])
