---
artefact:id: P05-TOC-001
artefact:version: 1.0.0
artefact:as-of: 2026-11-20
artefact:review-date: 2027-02-20
project: P05 DCAT-AP-UK (proposed)
grade: G3
profile: public sector > central > work
---

# Theory of change: DCAT-AP-UK (proposed)

> **How to read this.** Facts marked V were read from this repository on 20 November 2026. Assumptions, measures and risks are proposals written for this kit, not findings. U means unconfirmed. Where another document in this repository already covers a topic, this one links to it rather than repeating it.

## Problem
UK public sector catalogues describe datasets and data services in different ways, so records can't be found, judged or shared across catalogues; the endorsed xGov MEM has an open backlog.

## Long-term outcome
Catalogues across the public sector exchange records that validate against one profile, so critical data assets are described once and found everywhere.

## Chain

| Inputs | Activities | Outputs | Short-term outcomes | Medium-term outcomes |
|---|---|---|---|---|
| W3C DCAT 3; DCAT-AP 3.0.1; the xGov MEM and its backlog; EU frequency list; data.gov.uk themes; MIWG review | Specify the profile in one YAML source; generate SHACL, JSON Schema, JSON-LD context and codelists; provide a builder, validator, bulk checker, adoption toolkit, sector extensions and model contract clauses | Profile and its generated artefacts; portal pages (builder, validate, bulk, downloads, adopt, extensions, governance, strategy); a conformance kit | MIWG can review a complete, testable proposal; early adopters validate records | A decision on adoption; catalogues export harvestable records; contracts require conformance |

## Assumptions (proposed; each one testable)

| # | Assumption | How to test it | Evidence today |
|---|---|---|---|
| A1 | Aligning with DCAT-AP lowers cost for suppliers | Supplier conformance trials | ADR 0012 (design rationale) |
| A2 | One validator implementation used everywhere avoids drift (ADR 0009) | Parity tests across builder, CLI and site | tests/test_profile.py |
| A3 | Catalogue managers can map their records with the crosswalk | Usability round with 3 catalogue managers | Not tested |

## Measures (proposed)
- Every requirement in content/requirements.yaml traced to a rule and a test (checkable)
- Records from at least 3 real catalogues validated (trial log)
- MIWG decision recorded (governance page)

No target is set before a baseline exists.

## What would prove this wrong
If MIWG decides to keep the xGov MEM, convert DCAT-AP-UK into a MEM extension and close the portal's adoption pages.

## Status
Proposed, not endorsed; 1.3.0-rc.1 for MIWG review (V: README). Live site: https://cyberdudeuk.github.io/dcat-ap-uk/
