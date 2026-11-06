# Change log

All notable changes to DCAT-UK AP. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow semantic versioning.

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
