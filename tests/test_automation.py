"""The automation policy holds (ADR 0017, ops/automation.yaml).

Every workflow is declared with a tier; tier 1 routines honour the kill switch; third-party actions are pinned to a
commit; every workflow declares its permissions; nothing runs untrusted pull request code with write access; and the
routine runner refuses to change anything when the kill switch is off.
"""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

import datetime as dt

import yaml

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / '.github' / 'workflows'
POLICY = yaml.safe_load((ROOT / 'ops' / 'automation.yaml').read_text(encoding='utf-8'))


class Policy(unittest.TestCase):
    def test_every_workflow_is_declared(self):
        declared = {r['workflow'] for r in POLICY['routines']}
        for f in WF.glob('*.yml'):
            with self.subTest(workflow=f.name):
                self.assertIn(f.name, declared, 'add it to ops/automation.yaml with its tier')
        for r in POLICY['routines']:
            with self.subTest(routine=r['id']):
                self.assertTrue((WF / r['workflow']).exists())
                self.assertIn(r['tier'], (0, 1, 2, 3))
                for k in ('when', 'does', 'changes'):
                    self.assertTrue(r.get(k))

    def test_tier1_routines_honour_the_kill_switch(self):
        for f in WF.glob('*.yml'):
            t = f.read_text(encoding='utf-8')
            if 'tools/routine.py' in t:
                with self.subTest(workflow=f.name):
                    self.assertIn('AUTOMATION: ${{ vars.AUTOMATION }}', t)

    def test_actions_are_pinned_and_permissions_declared(self):
        for f in WF.glob('*.yml'):
            t = f.read_text(encoding='utf-8')
            with self.subTest(workflow=f.name):
                for use in re.findall(r'uses:\s*([^\s#]+)', t):
                    if not use.startswith('./'):
                        self.assertRegex(use, r'@[0-9a-f]{40}$', f'{use} is not pinned to a commit')
                self.assertRegex(t, r'(?m)^permissions:', 'declare permissions at the top')
                self.assertNotIn('pull_request_target', t, 'never run pull request code with write access')

    def test_never_list_is_kept(self):
        self.assertTrue(any('Merge' in n for n in POLICY['never']))
        self.assertTrue(any('settings' in n for n in POLICY['never']))


class KillSwitch(unittest.TestCase):
    def test_routine_reports_only_when_off(self):
        env = dict(os.environ, AUTOMATION='off')
        env.pop('GH_TOKEN', None)
        before = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True).stdout
        r = subprocess.run([sys.executable, '-I', 'tools/routine.py', 'flags-reset', '--tag', 'HEAD'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        after = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True).stdout
        self.assertEqual(before, after, r.stdout + r.stderr)
        self.assertIn('Kill switch is off', r.stdout)


sys.path.insert(0, str(ROOT / 'tools'))
import trials  # noqa: E402

GOOD = {'id': 'demo', 'hypothesis': 'A weekly link check finds broken links sooner', 'envelope': ['issues labelled trial'],
        'measure': 'broken links found per week', 'abort': 'more than 2 false alarms a week', 'started': '2026-11-07',
        'ends': '2026-12-07', 'owner': 'repository owner', 'tier': 0}


class Trials(unittest.TestCase):
    """ADR 0018: trials are test flights with an envelope, an end date and a kill switch."""

    def test_declared_trials_are_in_order(self):
        self.assertEqual(trials.problems(POLICY.get('trials') or []), [])

    def test_a_good_trial_passes_and_can_run(self):
        today = dt.date(2026, 11, 10)
        self.assertEqual(trials.problems([GOOD], today), [])
        ok, why = trials.gate('demo', [GOOD], {}, today)
        self.assertTrue(ok, why)

    def test_negative_each_guardrail_fails_when_it_should(self):
        today = dt.date(2026, 11, 10)
        cases = {
            'missing abort': (dict(GOOD, abort=''), 'missing abort'),
            'too long': (dict(GOOD, ends='2027-03-01'), 'the limit is 90'),
            'expired': (dict(GOOD, ends='2026-11-08'), 'ended'),
            'touches merge': (dict(GOOD, envelope=['merge its own pull requests']), 'merge'),
            'tier 1': (dict(GOOD, tier=1), 'only observe'),
            'bad id': (dict(GOOD, id='Demo Trial'), 'lower case'),
        }
        for name, (trial, needle) in cases.items():
            with self.subTest(case=name):
                p = trials.problems([trial], today)
                self.assertTrue(any(needle in x for x in p), p)
                self.assertFalse(trials.gate(trial['id'], [trial], {}, today)[0])

    def test_negative_kill_switches_stop_a_trial(self):
        today = dt.date(2026, 11, 10)
        self.assertEqual(trials.kill_variable('demo'), 'TRIAL_DEMO')
        self.assertFalse(trials.gate('demo', [GOOD], {'TRIAL_DEMO': 'off'}, today)[0])
        self.assertFalse(trials.gate('demo', [GOOD], {'AUTOMATION': 'off'}, today)[0])
        self.assertFalse(trials.gate('nope', [GOOD], {}, today)[0])

    def test_occurrences_are_reportable_without_blame(self):
        self.assertEqual(POLICY['occurrences']['label'], 'occurrence')
        labels = yaml.safe_load((ROOT / '.github' / 'labels.yml').read_text(encoding='utf-8'))
        self.assertIn('occurrence', {x['name'] for x in labels})
        form = yaml.safe_load((ROOT / '.github' / 'ISSUE_TEMPLATE' / 'occurrence.yml').read_text(encoding='utf-8'))
        self.assertEqual(form['labels'], ['occurrence'])
        text = str(form).lower()
        self.assertNotIn('your name', text)
        self.assertNotIn('email', text)
        self.assertIn("'occurrence'", (WF / 'digest.yml').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
