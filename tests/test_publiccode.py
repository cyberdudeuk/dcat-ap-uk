"""publiccode.yml must agree with CITATION.cff, name no person and publish no email address.

The file describes the repository to public sector software catalogues. It repeats the version,
release date and licence held in CITATION.cff, so it can drift when a release updates one and not
the other. The official parser (publiccode-parser-go) checks the schema; this test checks what the
parser cannot: agreement with CITATION.cff and the contact-form-only, no-personal-details rules.
"""
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("publiccodeYmlVersion", "name", "url", "softwareVersion", "releaseDate", "platforms",
            "categories", "developmentStatus", "softwareType", "description", "legal", "maintenance",
            "localisation")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def problems(pc: dict, cff: dict, raw: str) -> list[str]:
    found = [f"missing key: {k}" for k in REQUIRED if k not in pc]
    if str(pc.get("softwareVersion")) != str(cff.get("version")):
        found.append("softwareVersion does not match CITATION.cff version")
    if str(pc.get("releaseDate")) != str(cff.get("date-released")):
        found.append("releaseDate does not match CITATION.cff date-released")
    if str(cff.get("license")) not in str(pc.get("legal", {}).get("license", "")):
        found.append("legal.license does not include the CITATION.cff licence")
    if EMAIL.search(raw):
        found.append("an email address is published: contact is by the contact form only")
    for contact in pc.get("maintenance", {}).get("contacts", []):
        if set(contact) - {"name"}:
            found.append("a maintenance contact carries more than a group name")
    for author in cff.get("authors", []):  # the anonymous authors in CITATION.cff stay anonymous here
        for key in ("given-names", "family-names"):
            if author.get(key) and author[key] in raw:
                found.append(f"a person is named: {author[key]}")
    short = pc.get("description", {}).get("en", {}).get("shortDescription", "")
    if len(short.strip()) > 150:
        found.append("shortDescription is longer than 150 characters")
    return found


def load():
    raw = (ROOT / "publiccode.yml").read_text(encoding="utf-8")
    return yaml.safe_load(raw), yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8")), raw


class PubliccodeAgrees(unittest.TestCase):
    def test_publiccode_agrees_with_citation_and_rules(self):
        self.assertEqual(problems(*load()), [])

    def test_check_catches_drift_and_disclosure(self):  # negative test: each rule has a deliberate break
        pc, cff, raw = load()
        cases = {
            "softwareVersion": ({**pc, "softwareVersion": "0.0.0"}, raw),
            "releaseDate": ({**pc, "releaseDate": "1999-01-01"}, raw),
            "legal.license": ({**pc, "legal": {"license": "GPL-3.0-only"}}, raw),
            "email address": (pc, raw + "\n# someone@example.gov.uk\n"),
            "maintenance contact": ({**pc, "maintenance": {"type": "community",
                                     "contacts": [{"name": "x", "email": "x"}]}}, raw),
            "missing key": ({k: v for k, v in pc.items() if k != "legal"}, raw),
        }
        for label, (mutated, text) in cases.items():
            with self.subTest(break_=label):
                self.assertTrue(any(label in p for p in problems(mutated, cff, text)), label)


if __name__ == "__main__":
    unittest.main()
