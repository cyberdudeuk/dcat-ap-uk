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

    # Claims found on 20 November 2026 (issue 21) that the cited source does not make. Re-reading the National Data
    # Library progress update showed it never says data.gov.uk is becoming the Library. Keep them out unless a source is cited.
    UNSOURCED = ('data.gov.uk is becoming',)

    def unsourced_claims(self, texts):
        return [(name, c) for name, t in texts.items() for c in self.UNSOURCED if c.lower() in t.lower()]

    def test_no_claim_the_cited_source_does_not_make(self):
        texts = {p.name: p.read_text(encoding='utf-8') for p in (ROOT / 'content').glob('*.yaml')}
        self.assertEqual(self.unsourced_claims(texts), [])

    def test_negative_an_unsourced_claim_is_caught(self):
        self.assertTrue(self.unsourced_claims({'portal.yaml': "notes: 'data.gov.uk is becoming the National Data Library.'"}))

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


class ReviewCycle(unittest.TestCase):
    """The provenance issue stayed open for ever: comparing real examples with their publisher at each review can never be
    ticked off. Those items are now at_review, kept out of needs_action, and the routine closes the issue when nothing is left."""

    def test_review_items_are_not_counted_as_needing_action_now(self):
        import provenance
        reg = provenance.register()
        again = [r for r in reg['items'] if r['at_review']]
        self.assertTrue(again, 'the worked examples are compared at each review')
        self.assertTrue(all(r['action'] in provenance.REVIEW_ACTIONS for r in again))
        self.assertEqual(reg['needs_action'], sum(1 for r in reg['items'] if r['action'] and not r['at_review']))
        self.assertFalse(any(r['at_review'] for r in reg['items'] if r['prov'] == 'K'), 'facts to verify are never deferred to review')

    def test_routine_closes_the_issue_when_nothing_is_left(self):
        import routine
        calls = []
        orig_sh, orig_reg = routine.sh, None
        import provenance
        orig_reg = provenance.register
        try:
            provenance.register = lambda today=None: {'items': [{'action': "compare with the publisher's record each review", 'at_review': True, 'item': 'x', 'file': 'f', 'prov': 'U'}],
                                                       'counts': {}, 'needs_action': 0, 'at_review': 1, 'unexplained_synthetic': 0, 'misattributed': []}
            routine.sh = lambda *a, **k: calls.append(a) or ('4' if 'list' in a else 0)
            import os
            saved = os.environ.get('GH_TOKEN')
            os.environ['GH_TOKEN'] = 'test'
            routine.provenance_issue(False)
        finally:
            routine.sh, provenance.register = orig_sh, orig_reg
            if saved is None:
                os.environ.pop('GH_TOKEN', None)
            else:
                os.environ['GH_TOKEN'] = saved
        self.assertTrue(any(a[:3] == ('gh', 'issue', 'close') and a[3] == '4' for a in calls), calls)
        self.assertFalse(any('create' in a or 'edit' in a for a in calls))

    def test_status_heading_matches_the_register(self):
        # D-048: the heading said "To verify or replace (6)" when nothing needed verifying now; all six were review items.
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_integrations import built
        built()
        html = (ROOT / 'site' / 'status.html').read_text(encoding='utf-8')
        reg = provenance.register()
        self.assertIn(f'Needs a person: {reg["needs_action"]} now, {reg["at_review"]} at each review', html)
        self.assertNotIn('To verify or replace', html)
