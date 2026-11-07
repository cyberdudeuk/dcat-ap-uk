"""Every fact, example and sample says where it comes from (ADR 0020).

Synthetic content must give its reason and must never name a real organisation as its publisher; every example.org
address in the tools' built-in samples must be declared; real examples carry their source and the date checked.
Each guardrail has a negative test that shows it fails when it should.
"""
import copy
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import provenance  # noqa: E402


class Provenance(unittest.TestCase):
    def test_no_unexplained_or_misattributed_synthetic_content(self):
        reg = provenance.register()
        self.assertEqual(reg['unexplained_synthetic'], 0, [r for r in reg['items'] if r['prov'] == 'synthetic' and not r.get('synthetic')])
        self.assertEqual(reg['misattributed'], [])

    def test_real_examples_carry_source_and_date(self):
        for e in yaml.safe_load((ROOT / 'examples' / 'examples.yaml').read_text(encoding='utf-8')):
            if provenance.FAKE.search(json.dumps(e['record'])):
                with self.subTest(example=e['key']):
                    self.assertIsInstance(e.get('synthetic'), str, 'a synthetic example states its reason in words')
            elif e.get('source'):
                with self.subTest(example=e['key']):
                    dt.date.fromisoformat(e['source']['checked'])
                    self.assertTrue(e['source']['url'].startswith('https://'))

    def test_samples_are_declared(self):
        decl = yaml.safe_load((ROOT / 'content' / 'samples.yaml').read_text(encoding='utf-8'))
        for d in decl:
            with self.subTest(sample=d['id']):
                self.assertTrue(d.get('synthetic') or (d.get('prov') == 'V' and d.get('checked') and d.get('url')), 'a sample is verified with a date, or says why it is synthetic')

    def test_negative_a_synthetic_record_under_a_real_publisher_is_caught(self):
        rows = [{'prov': 'synthetic', 'file': 'x', 'path': 'y', 'record': {'publisher': 'https://www.gov.uk/government/organisations/hm-revenue-customs'}}]
        self.assertTrue(provenance.misattributed(rows))
        rows[0]['record']['publisher'] = 'https://example.org/organisations/example-department'
        self.assertFalse(provenance.misattributed(rows))

    def test_negative_an_unexplained_synthetic_example_is_caught(self):
        orig = provenance.examples

        def broken():
            rows = copy.deepcopy(orig())
            for r in rows:
                if r['prov'] == 'synthetic':
                    r['synthetic'] = None
                    break
            return rows
        provenance.examples = broken
        try:
            self.assertGreater(provenance.register()['unexplained_synthetic'], 0)
        finally:
            provenance.examples = orig

    def test_negative_stale_and_unverified_facts_need_action(self):
        today = dt.date(2026, 11, 7)
        old = {'prov': 'V', 'note': 'Checked 1 January 2026: fine.'}
        self.assertEqual(provenance.checked_on(old), dt.date(2026, 1, 1))
        rows = provenance.labelled(today + dt.timedelta(days=400))
        self.assertTrue(any(r['action'] and 're-check' in r['action'] for r in rows), 'a V check older than the limit asks to be re-checked')
        self.assertTrue(all(r['action'] for r in rows if r['prov'] in ('K', 'U')))

    def test_status_page_and_download_show_it(self):
        site = ROOT / 'site'
        if not (site / 'status.html').exists():
            self.skipTest('site not built')
        html = (site / 'status.html').read_text(encoding='utf-8')
        self.assertIn('id="provenance"', html)
        data = json.loads((site / 'downloads' / 'provenance.json').read_text(encoding='utf-8'))
        self.assertEqual(data['unexplained_synthetic'], 0)


if __name__ == '__main__':
    unittest.main()
