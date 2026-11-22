"""D-045: crosswalk element names drifted from the standards they map to (HDR UK 4 and GEMINI 2.3 renamed five).

Offline tests of tools/check_crosswalk_names.py, which CI runs against the published definitions on every build."""
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import check_crosswalk_names as c  # noqa: E402

SCHEMA = '{"properties": {"summary": {"$ref": "#/$defs/S"}, "provenance": {"properties": {"temporal": {"properties": ' \
         '{"startDate": {}, "endDate": {}, "publishingFrequency": {}}}}}}, "$defs": {"S": {"properties": {"dataCustodian": {}}}}}'


class CrosswalkNames(unittest.TestCase):
    def test_every_verified_crosswalk_says_where_and_when(self):
        for cid, cw in yaml.safe_load((ROOT / 'profile' / 'crosswalks.yaml').read_text(encoding='utf-8')).items():
            if cw.get('prov') == 'V':
                with self.subTest(crosswalk=cid):
                    self.assertTrue(str(cw.get('checked_at', '')).startswith('https://'))
                    self.assertRegex(str(cw.get('checked', '')), r'^\d{4}-\d{2}-\d{2}$')
                    for part in cw['checked_at'].split(' and '):
                        if urlparse(part).hostname == 'github.com':  # whole host, not a substring (CodeQL #47)
                            self.assertRegex(part, r'/blob/[0-9a-f]{40}/', 'pin GitHub sources to a full commit')

    def test_a_renamed_json_schema_field_is_caught(self):
        rows = [['publisher', 'summary.publisher', ''], ['temporal', 'provenance.temporal.startDate and endDate', ''],
                ['accrualPeriodicity', 'provenance.temporal.accrualPeriodicity', '']]
        self.assertEqual(c.missing('hdruk', rows, SCHEMA), ['summary.publisher', 'provenance.temporal.accrualPeriodicity'])
        rows[0][1], rows[2][1] = 'summary.dataCustodian', 'provenance.temporal.publishingFrequency'
        self.assertEqual(c.missing('hdruk', rows, SCHEMA), [])

    def test_a_renamed_label_is_caught(self):
        text = '|1 |Title |36 |Resource identifier |53 |Maintenance information'
        self.assertEqual(c.missing('gemini', [['identifier', 'Unique resource identifier', '']], text), ['Unique resource identifier'])
        self.assertEqual(c.missing('gemini', [['identifier', 'Resource identifier', '']], text), [])

    def test_ckan_prefixes_are_not_element_names(self):
        self.assertEqual(c.elements('ckan', 'organization and extras publisher_uri'), ['publisher_uri'])
        self.assertEqual(c.elements('ckan', 'resource hash and hash_algorithm'), ['hash', 'hash_algorithm'])
        self.assertEqual(c.elements('ckan', '(none)'), [])


class ExtensionTerms(unittest.TestCase):
    """D-047: the statistics extension used statMeasure, a term in no StatDCAT-AP version."""
    PREFIXES = {'statdcatap': 'http://data.europa.eu/s1n/', 'mob': 'https://w3id.org/mobilitydcat-ap#'}

    def test_a_term_the_standard_does_not_define_is_caught(self):
        ext = {'properties': {'a': {'uri': 'statdcatap:measure'}, 'b': {'uri': 'statdcatap:statMeasure'}, 'c': {'uri': 'dcatuk:x'}}}
        ns, names = c.borrowed_terms(ext, self.PREFIXES)
        self.assertEqual((ns, names), ('http://data.europa.eu/s1n/', ['measure', 'statMeasure']))
        text = '<http://data.europa.eu/s1n/measure> a rdf:Property . <http://data.europa.eu/s1n/statUnitMeasure> a rdf:Property .'
        self.assertEqual(c.missing_terms(ns, names, text), ['statMeasure'])

    def test_a_wrong_namespace_is_caught(self):
        self.assertEqual(c.missing_terms('http://data.europa.eu/(xyz)/statdcat-ap/', [], 'http://data.europa.eu/s1n/measure'),
                         ['namespace http://data.europa.eu/(xyz)/statdcat-ap/'])

    def test_every_checked_extension_term_list_is_pinned_to_a_definition(self):
        exts = yaml.safe_load((ROOT / 'profile' / 'extensions.yaml').read_text(encoding='utf-8'))
        for e in exts['extensions']:
            for al in e.get('aligned_to', []):
                if al.get('prov') == 'V':
                    with self.subTest(extension=e['id'], standard=al['name']):
                        self.assertRegex(str(al.get('checked', '')), r'^\d{4}-\d{2}-\d{2}$')


class AlignmentBadges(unittest.TestCase):
    """D-047: the page showed the source page's V badge beside an alignment that was still K."""

    def test_each_alignment_shows_its_own_provenance(self):
        import re
        from test_integrations import built  # CI runs the tests before it builds the site
        built()
        html = (ROOT / 'site' / 'extensions.html').read_text(encoding='utf-8')
        exts = yaml.safe_load((ROOT / 'profile' / 'extensions.yaml').read_text(encoding='utf-8'))['extensions']
        for e in exts:
            for al in e.get('aligned_to', []):
                with self.subTest(extension=e['id'], standard=al['name']):
                    m = re.search(re.escape(al['name']) + r':\s*<a [^>]*>[^<]*</a>, alignment <abbr class="prov (\w+)"', html)
                    self.assertIsNotNone(m, 'alignment badge not rendered')
                    self.assertEqual(m.group(1), al['prov'])
