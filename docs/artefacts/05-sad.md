---
artefact:id: P05-SAD-001
artefact:version: 1.0.0
artefact:as-of: 2026-11-20
artefact:review-date: 2027-02-20
project: P05 DCAT-AP-UK (proposed)
grade: G3
profile: public sector > central > work
---

# Solution architecture (SAD): DCAT-AP-UK (proposed)

> **How to read this.** Facts marked V were read from this repository on 20 November 2026. Assumptions, measures and risks are proposals written for this kit, not findings. U means unconfirmed. Where another document in this repository already covers a topic, this one links to it rather than repeating it.

## Context
UK public sector catalogues describe datasets and data services in different ways, so records can't be found, judged or shared across catalogues; the endorsed xGov MEM has an open backlog.

The solution is described in [03-prd.md](03-prd.md). It connects with: xGov MEM (endorsed model); W3C DCAT 3 / DCAT-AP 3.0.1; Vendor catalogue tools; NDL PubSec MCP; w3id.org.

## Architecturally significant decisions
These are the decisions already recorded in this repository (V):

- [0001-a-new-repository-not-a-rename.md](../adr/0001-a-new-repository-not-a-rename.md)
- [0002-generate-from-one-yaml-file-with-our-own-script-not-linkml.md](../adr/0002-generate-from-one-yaml-file-with-our-own-script-not-linkml.md)
- [0003-contact-form-preferred-over-email-in-contact-points.md](../adr/0003-contact-form-preferred-over-email-in-contact-points.md)
- [0004-obligations-for-critical-data-assets-as-conditionals.md](../adr/0004-obligations-for-critical-data-assets-as-conditionals.md)
- [0005-eu-frequency-list-and-data-gov-uk-themes.md](../adr/0005-eu-frequency-list-and-data-gov-uk-themes.md)
- [0006-a-proposed-w3id-org-namespace.md](../adr/0006-a-proposed-w3id-org-namespace.md)
- [0007-sector-extensions-that-only-add-or-raise.md](../adr/0007-sector-extensions-that-only-add-or-raise.md)
- [0008-cross-border-flows-as-two-properties-and-a-rule.md](../adr/0008-cross-border-flows-as-two-properties-and-a-rule.md)
- [0009-one-validator-implementation-used-everywhere.md](../adr/0009-one-validator-implementation-used-everywhere.md)
- [0010-quantum-ready-means-ready-to-migrate.md](../adr/0010-quantum-ready-means-ready-to-migrate.md)
- [0011-name-the-profile-dcat-ap-uk.md](../adr/0011-name-the-profile-dcat-ap-uk.md)
- [0012-integrations-through-a-conformance-kit-and-one-reference-implementation.md](../adr/0012-integrations-through-a-conformance-kit-and-one-reference-implementation.md)
- [0013-model-contract-clauses-for-open-standards-and-exit.md](../adr/0013-model-contract-clauses-for-open-standards-and-exit.md)
- [0014-a-global-bar-that-fits-a-laptop-screen.md](../adr/0014-a-global-bar-that-fits-a-laptop-screen.md)
- [0015-a-requirements-stream-for-a-family-of-profiles-with-controlled-layers-kept-out-of-the-public-repository.md](../adr/0015-a-requirements-stream-for-a-family-of-profiles-with-controlled-layers-kept-out-of-the-public-repository.md)
- [0016-share-the-build-change-flag-and-self-check-patterns-of-the-connected-solutions.md](../adr/0016-share-the-build-change-flag-and-self-check-patterns-of-the-connected-solutions.md)
- [0017-routines-do-the-upkeep-a-person-keeps-control.md](../adr/0017-routines-do-the-upkeep-a-person-keeps-control.md)
- [0018-run-the-estate-as-flight-operations-test-flights-with-an-envelope-near-misses-reported-without-blame.md](../adr/0018-run-the-estate-as-flight-operations-test-flights-with-an-envelope-near-misses-reported-without-blame.md)
- [0019-a-plainer-look-and-model-maps-for-how-things-connect.md](../adr/0019-a-plainer-look-and-model-maps-for-how-things-connect.md)
- [0020-say-where-every-fact-comes-from-and-use-real-records-wherever-they-can-be-shown.md](../adr/0020-say-where-every-fact-comes-from-and-use-real-records-wherever-they-can-be-shown.md)
- [0021-vendor-connectors-from-published-models-only-with-each-vendor-s-ai-offer-beside-them.md](../adr/0021-vendor-connectors-from-published-models-only-with-each-vendor-s-ai-offer-beside-them.md)

## Quality attributes

| Attribute | How it is met |
|---|---|
| Browser checks and deliberate-break tests | Browser checks and deliberate-break tests (tests/test_browser_breaks.py) |
| Releases through a reviewed workflow | Releases through a reviewed workflow (tests/test_release_workflow.py) |
| Proposed w3id.org namespace | Proposed w3id.org namespace (ADR 0006) |
| Contact | By form only; no email address anywhere (estate rule) |
| Documentation | This kit, checked in CI by `tools/artefact_check.py` |

## Constraints
- Proposed, not endorsed; 1.3.0-rc.1 for MIWG review (V: README).
- No personal data unless a DPIA has been done first.
- Contact by form only.

## Risks (proposed ratings)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Read as endorsed when it is not | Medium | High | Banner and governance status page |
| Two models in parallel confuse adopters | High | High | Clear 'endorsed model remains xGov MEM' message; decision date |
| Single maintainer | High | Medium | Routines, ADRs, this kit |
