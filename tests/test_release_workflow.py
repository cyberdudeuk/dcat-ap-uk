"""Issue #20: the release must not fail when a person has already made the release by hand."""
import unittest
from pathlib import Path

import yaml

WF = Path(__file__).resolve().parent.parent / ".github/workflows/release.yml"


def release_script(text: str) -> str:
    steps = yaml.safe_load(text)["jobs"]["release"]["steps"]
    return next(s["run"] for s in steps if "gh release create" in s.get("run", ""))


def guarded(script: str) -> bool:
    """An existing release is detected first and its assets are replaced, not re-created."""
    script = "\n".join(l for l in script.splitlines() if not l.strip().startswith("#"))  # comments don't count
    view, upload, create = (script.find(x) for x in ("gh release view", "gh release upload", "gh release create"))
    return -1 not in (view, upload, create) and view < create and "--clobber" in script


class ReleaseGuard(unittest.TestCase):
    def test_existing_release_is_updated_not_recreated(self):
        self.assertTrue(guarded(release_script(WF.read_text())))

    def test_check_fails_on_an_unguarded_release(self):  # negative test
        self.assertFalse(guarded('gh release create "$TAG" --generate-notes a.ttl'))


if __name__ == "__main__":
    unittest.main()
