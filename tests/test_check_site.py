"""D-038: the Adopt page's Words for contracts box showed {E(pc)} instead of the clauses, because the line was not an
f-string and check C-16 skipped everything inside <pre>. C-16 now flags the build's own signatures inside <pre>."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import check_site  # noqa: E402


def doc(html):
    return [(Path('adopt.html'), SimpleNamespace(text=html))]


class Unrendered(unittest.TestCase):
    def test_placeholder_inside_pre_is_caught(self):
        self.assertTrue(check_site.c_unrendered(None, doc('<pre id="proc" tabindex="0">{E(pc)}</pre>')))
        self.assertTrue(check_site.c_unrendered(None, doc('<pre>{self.counts()}</pre>')))

    def test_code_examples_in_pre_still_pass(self):
        self.assertEqual([], check_site.c_unrendered(None, doc('<pre>{"@context": {"dcat": "http://www.w3.org/ns/dcat#"}}</pre>')))
        self.assertEqual([], check_site.c_unrendered(None, doc('<pre>{ "title": "x" }</pre>')))

    def test_page_text_still_checked(self):
        self.assertTrue(check_site.c_unrendered(None, doc('<p>{layers}</p>')))


class RegisterIds(unittest.TestCase):
    # D-039: two defects were numbered D-037 by pull requests prepared in parallel.
    def test_register_ids_are_unique(self):
        import collections
        import yaml
        d = yaml.safe_load((ROOT / 'content' / 'portal.yaml').read_text(encoding='utf-8'))
        ids = []

        def walk(o):
            if isinstance(o, dict):
                if isinstance(o.get('id'), str) and o['id'][:2] in ('D-', 'O-', 'C-'):
                    ids.append(o['id'])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(d)
        dupes = [k for k, n in collections.Counter(ids).items() if n > 1]
        self.assertEqual([], dupes, 'register ids used more than once')
        self.assertIn('D-039', ids)


if __name__ == '__main__':
    unittest.main()
