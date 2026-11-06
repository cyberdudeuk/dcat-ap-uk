# Change log

All notable changes to DCAT-AP-UK. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow semantic versioning.

## [1.2.0-rc.1] - 2026-11-06

A minor release: a new name, tools for suppliers and buyers, and a richer portal. No property changes meaning. Proposed, not endorsed.

### Changed
- Renamed DCAT-AP-UK (the DCAT Application Profile for the UK), after DCAT-AP-NO, -SE and -NL (ADR 0011).
  The profile file is `profile/dcat-ap-uk.yaml` and the proposed namespace is `https://w3id.org/dcat-ap-uk/`.
  The `dcatuk:` prefix stays. The repository is renamed by its owner (open register O-16).
- Display options moved to the masthead, beside search and help.

### Added
- Pages: user guide, tutorials, metadata weaver, lineage explorer, standards map, insights, integrations,
  avoiding lock-in, value types and licence; a visual site map.
- Guided tours on seven pages.
- The weaver in `validator.js`: readers for DCAT-AP-UK, xGov MEM, CKAN, DCAT-US, schema.org, Dublin Core and DDI;
  writers for those plus JSON-LD, Turtle and Croissant. A DDI Codebook crosswalk.
- A conformance kit (`downloads/conformance/`), level badges, an OpenAPI description of the reference API,
  a command line (`integrations/cli/validate.js`), a local HTTP API (`integrations/http/server.js`) and a GitHub Action (`action.yml`).
- Model contract clauses for open standards and exit (`downloads/contract-clauses.md`, ADR 0013).
- From the xGov MEM portal: a class diagram on each class page, the profile in tables on the home page,
  and "Suggest a change to this page" in every footer.
- Checks C-19 (no style attributes), C-20 (tour stops exist) and C-21 (feedback link on every page),
  each with a deliberate break; a browser pass with the content security policy on.
- Repository: a conformance claim issue form, labels as code, release note categories, CodeQL, support and governance files.

### Fixed
- D-017 to D-023; see the defect register.

## [1.1.0-rc.1] - 2026-11-06

A minor release: new optional properties, a new rule for a new property, extensions and tools. Proposed, not endorsed.

### Added
- Nine sector extensions in `profile/extensions.yaml`: health (HealthDCAT-AP R7, HDR UK), geospatial (GeoDCAT-AP 3.1, UK GEMINI 2.3),
  statistics (StatDCAT-AP), transport (mobilityDCAT-AP), high-value datasets for EU exchange, AI-ready (MLDCAT-AP, Croissant 1.1),
  data spaces (Dataspace Protocol), private and voluntary sector (org-id identifiers) and energy (Ofgem Data Best Practice).
  Each generates its own SHACL shapes and JSON Schema, and has an example and deliberate breaks checked by all three validators.
- Properties: applicable legislation, usage policy (ODRL), where the data is held or sent, transfer safeguard, connection security.
- Rule R-08: personal data held in or sent outside the UK needs a transfer safeguard. Pattern rule P-01. Weak checksum warning Q-01.
- Codelists: jurisdictions (UK nations, Crown Dependencies, 14 Overseas Territories, the Commonwealth, the EEA, partners),
  transfer safeguards, checksum algorithms (SPDX), connection security, use for AI, statistics status, open data triage.
- A quality score modelled on the EU metadata quality assessment, and conformance levels 1 to 3.
- Pages: sector extensions, check many records (CSV), OpenAPI to data service, adoption toolkit, cross-border flows, AI-ready,
  quantum-ready, and profiles around the world.
- Crosswalks to CKAN, Dublin Core, UK GEMINI, HDR UK and Croissant; computed crosswalk to DCAT-AP and DCAT-US.
- ODRL usage policy templates, a spreadsheet template, schema.org and Croissant exports, llms.txt and llms-full.txt.
- An MCP server (`integrations/mcp/`) with nine tools, using the portal's validator (closes open register O-10).
- Link to the future pan-UK metadata architecture (co-cddo), which this profile implements.

### Changed
- The checksum algorithm is now a concept from the SPDX checksum algorithm list.

### Fixed
- D-013 to D-016; see the defect register.

## [1.0.0-rc.1] - 2026-11-06

First release candidate, for review by the Metadata Implementation Working Group. Proposed, not endorsed.

### Added
- The profile: 13 classes and 79 properties on DCAT 3, aligned with DCAT-AP 3.0.1, in one YAML source.
- Critical data asset rules from the April 2026 GOV.UK guidance.
- Twelve codelists as SKOS, mapped to EU vocabularies, and 1,271 GOV.UK organisations.
- Generated SHACL shapes, JSON Schema, JSON-LD context, LinkML, CSV data dictionary and crosswalks.
- A portal with a record builder, a validator that converts xGov MEM records, crosswalks, the backlog register, strategy, roles,
  knowledge layer, estate comparison and governance registers.
- Tests that hold SHACL, JSON Schema and the browser validator to the same verdict; deliberate breaks for every rule and check.

### Changed (from the xGov MEM v0.1.0)
- See the [crosswalk](https://cyberdudeuk.github.io/dcat-uk-ap/changes.html#crosswalk). Every xGov MEM property maps.

### Fixed (xGov MEM issues)
- 69, 71, 72, 76 and the missing IRI for security classification. See the [backlog register](docs/registers.md#backlog-from-the-xgov-mem).
