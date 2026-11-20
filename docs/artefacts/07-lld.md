---
artefact:id: P05-LLD-001
artefact:version: 1.0.0
artefact:as-of: 2026-11-20
artefact:review-date: 2027-02-20
project: P05 DCAT-AP-UK (proposed)
grade: G3
profile: public sector > central > work
---

# Low-level design (LLD): DCAT-AP-UK (proposed)

> **How to read this.** Facts marked V were read from this repository on 20 November 2026. Assumptions, measures and risks are proposals written for this kit, not findings. U means unconfirmed. Where another document in this repository already covers a topic, this one links to it rather than repeating it.

## Build and check commands (V: README)
```
python3 -I tools/generate.py
python3 -I tools/build.py
python3 -I -m pytest tests
```

## Scripts (V: file tree)
- `tools/build.py`
- `tools/check_browser.py`
- `tools/check_linkml.py`
- `tools/check_site.py`
- `tools/check_vendor_repos.py`
- `tools/check_vendor_shapes.py`
- `tools/generate.py`
- `tools/health.py`
- `tools/import_orgs.py`
- `tools/provenance.py`
- `tools/routine.py`
- `tools/section_baseline.py`
- `tools/sections.py`
- `tools/trials.py`
- `tools/ukap.py`
- `tools/vendor_icons.py`

## Tests (V: file tree)
- `tests/test_automation.py`
- `tests/test_browser_breaks.py`
- `tests/test_check_site.py`
- `tests/test_integrations.py`
- `tests/test_lint.py`
- `tests/test_profile.py`
- `tests/test_provenance.py`
- `tests/test_publiccode.py`
- `tests/test_release_workflow.py`
- `tests/test_toolkit.py`
- `tests/test_vendors.py`

## Workflows (V: .github/workflows)
- `codeql.yml`
- `dependency-review.yml`
- `digest.yml`
- `labels.yml`
- `pages.yml`
- `release.yml`
- `scorecard.yml`
- `triage.yml`
- `upkeep.yml`

## Repository size
128 files tracked on 20 November 2026.

## Documentation kit
- `docs/artefacts/manifest.yaml` lists every core document, where it is, and its review date.
- `tools/artefact_check.py` checks the kit (rules AC-01 to AC-08, each with a negative test). Run `python3 tools/artefact_check.py --self-test` then `python3 tools/artefact_check.py .`.

## Handover
Someone new can rebuild and verify with the commands above, then read [03-prd.md](03-prd.md) and [05-sad.md](05-sad.md).
