"""D-045: crosswalk element names drifted from the standards they map to (HDR UK 4 and GEMINI 2.3 renamed five).

Offline tests of tools/check_crosswalk_names.py, which CI runs against the published definitions on every build."""
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
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
