---
artefact:id: P05-PRD-001
artefact:version: 1.0.0
artefact:as-of: 2026-11-20
artefact:review-date: 2027-02-20
project: P05 DCAT-AP-UK (proposed)
grade: G3
profile: public sector > central > work
---

# Product requirements (PRD): DCAT-AP-UK (proposed)

> **How to read this.** Facts marked V were read from this repository on 20 November 2026. Assumptions, measures and risks are proposals written for this kit, not findings. U means unconfirmed. Where another document in this repository already covers a topic, this one links to it rather than repeating it.

## Problem and outcome
UK public sector catalogues describe datasets and data services in different ways, so records can't be found, judged or shared across catalogues; the endorsed xGov MEM has an open backlog.

Outcome sought: Catalogues across the public sector exchange records that validate against one profile, so critical data assets are described once and found everywhere. See [01-theory-of-change.md](01-theory-of-change.md).

## Users
- Catalogue managers
- Data owners and stewards
- Chief data officers and policy coordinators
- Engineers and suppliers
- Buyers and commercial leads
- People building with AI

User evidence: [02-ur-bundle.md](02-ur-bundle.md).

## Scope
**In:**
- The profile and its generated artefacts
- Builder, validator, bulk checker
- Adoption toolkit and sector extensions
- Cross-border data flows
- Model contract clauses
- Governance and status pages

**Out:**
- Hosting a catalogue
- Claiming endorsement
- Controlled layers kept out of the public repository (ADR 0015)

## Requirements
Derived from what this repository says it does (V: README and ADRs). The last column is the check that proves each one, where one exists. U means no check was found that clearly covers it; that is a gap to close, not a pass.

| ID | Requirement | Priority | Verified by |
|---|---|---|---|
| P05-R01 | Generate every artefact from one YAML file with the project's own script (ADR 0002) | Must | tools/generate.py; tests/test_profile.py |
| P05-R02 | Critical data asset obligations as conditional rules (ADR 0004) | Must | tests/test_profile.py |
| P05-R03 | One validator implementation used everywhere (ADR 0009) | Must | tests/test_toolkit.py |
| P05-R04 | Sector extensions that only add or raise (ADR 0007) | Should | tests/test_profile.py |
| P05-R05 | Cross-border flows as two properties and a rule (ADR 0008) | Should | tests/test_profile.py |
| P05-R06 | Contact points use a contact form, not email (ADR 0003) | Must | tests/test_lint.py (U: confirm) |
| P05-R07 | Integrations through a conformance kit and one reference implementation (ADR 0012) | Should | tests/test_integrations.py |
| P05-R08 | Every fact sourced; real records where they can be shown (ADR 0020) | Must | tests/test_provenance.py |
| P05-R09 | Global bar fits a laptop screen (ADR 0014) | Must | tests/test_browser_breaks.py |

## Non-functional requirements
- Browser checks and deliberate-break tests (tests/test_browser_breaks.py)
- Releases through a reviewed workflow (tests/test_release_workflow.py)
- Proposed w3id.org namespace (ADR 0006)

## Status
Proposed, not endorsed; 1.3.0-rc.1 for MIWG review (V: README)
