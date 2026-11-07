"""The browser deliberate breaks stay complete and fail-fast cannot hide a miss.

The workflow runs the breaks in parallel and each stops at its first problem, to keep publishing fast. That is only
safe if every break in tools/check_browser.py is still run, and if stopping early happens only after a problem.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import check_browser  # noqa: E402


class Breaks(unittest.TestCase):
    def test_workflow_runs_every_break(self):
        t = (ROOT / '.github' / 'workflows' / 'pages.yml').read_text(encoding='utf-8')
        m = re.search(r"printf '%s\\n' ([a-z ]+?) \\", t)
        self.assertIsNotNone(m, 'the break list in pages.yml has moved; update this test')
        self.assertEqual(sorted(m.group(1).split()), sorted(check_browser.BREAKS))

    def test_fail_fast_stops_only_after_a_problem(self):
        f = check_browser._Fails(True)
        self.assertEqual(len(f), 0)
        with self.assertRaises(check_browser._Stop):
            f.append('a problem')
        self.assertEqual(list(f), ['a problem'])

    def test_negative_normal_runs_collect_every_problem(self):
        f = check_browser._Fails(False)
        f.append('one'); f.append('two')
        self.assertEqual(list(f), ['one', 'two'])


if __name__ == '__main__':
    unittest.main()
