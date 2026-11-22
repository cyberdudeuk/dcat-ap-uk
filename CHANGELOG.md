# Change log

All notable changes to DCAT-AP-UK. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow semantic versioning.

## [Unreleased]

### Added (ADR 0023, accepted 22 November 2026; change request #34)

- **Sharing agreement.** A dataset or data service can link the agreement it is shared under through a qualified relation (`dcat:qualifiedRelation`) with the new role `ukcl:relation-role/sharing-agreement`, for example its entry in the Digital Economy Act register. Qualified relation is now allowed on data services too.
- **Sharing method** (`dcatuk:sharingMethod`, optional, 0..n) on datasets and data services, from the new sharing-method codelist: the nine methods the Digital Economy Act register uses, read on 22 November 2026. Give every method the data moves by; where one is API, link the API through a distribution's access service.
- A class can now take a property's values from its own codelist. Role (`dcat:hadRole`) takes the new relation-role list on a relationship and keeps the responsible-role list on an attribution. Records that put a responsible role on a relationship no longer conform; no worked example did. Under the versioning rules this narrowing could count as major; it is treated as minor because the old binding was a mistake (ADR 0023).
- A crosswalk from the register's agreement fields, and glossary entries for sharing agreement and sharing method.

### Changed (ADR 0022, accepted 22 November 2026)

- The quality score now uses the method of the EU metadata quality assessment, as data.europa.eu publishes it: every check passes or fails, weighted 1, 0.5 or 0.25; datasets, distributions and data services each score out of 7.5 and are averaged into the dataset score; bands are sufficient, good (from 2.5) and excellent (from 5). It gives two readings: the EU reading (the EU's own checks, with UK values matched to the EU lists they equal, so publishers see what data.europa.eu will score) and the UK reading (every property weighted by its DCAT-AP-UK obligation). It replaces the earlier 405-point model, which the EU has retired.
- Level 3 (Exemplary) now needs a UK reading of 5 or more out of 7.5, instead of 351 or more out of 405.
- Licences carry their exact EU licence-list equivalents (OGL v3.0, NCGL v2.0, CC BY 4.0, CC0), checked at source; the Open Parliament Licence v3.0 has none. The profile export (profile.json) gives each codelist value's exact EU equivalent as `eu`.
- `V.fair()` keeps its name; it now returns `uk` and `eu` readings, with `score`, `max` (7.5) and `rating` taken from the UK reading. `V.conformance()` adds `max` and `eu`.

### Changed

- The statistics extension (proposed) now follows StatDCAT-AP 3.0.0, the latest version, by the owner's decision of 22 November 2026 (O-13). Its namespace moves from the `(xyz)` placeholder to `http://data.europa.eu/s1n/`, and the property `statMeasure`, which is in no StatDCAT-AP version, becomes `measure` (`s1n:measure`, the phenomenon observed). Records using `statMeasure` need the new name. StatDCAT-AP 3.0.0 is still a draft, so the terms are re-checked when it is released; `tools/check_crosswalk_names.py` checks them against the draft on every build.
- The DCAT-US example in the metadata weaver is now a real US federal record (the NIST NICE Framework, from the Department of Commerce data.json, checked 22 November 2026) instead of an invented one.
- Ab Initio is no longer shown as a Leader in the Gartner Magic Quadrant for Master Data Management (2025), because that position could not be confirmed at source.

### Fixed

- The provenance issue (#4) could never close (D-048). Comparing the worked examples with their publisher's record happens at every review, so those items could never be ticked off, and the upkeep routine had no step to close the issue. Review items are now listed separately (in the review reminder and in a "When" column on the Status page), the routine lists only what needs a person now and closes the issue when that list is empty, and the Status page heading gives both counts. Regression tests: `tests/test_provenance.py` ReviewCycle.
- Modules imported a second time inside functions (CodeQL alerts 48 and 49, and three more found by the new check) are imported once (D-049). Regression test: `tests/test_lint.py` NoReimports.
- Python dependencies are pinned and hashed, including every transitive package, and CI enforces the hashes; workflows grant write scopes only to the job that needs them (D-050, Scorecard alerts 31, 33 to 36 and 46). Edit `requirements.in`; the `.txt` files are generated. Regression tests: `tests/test_lint.py` SupplyChain.
- Seven CodeQL quality findings are corrected with no change in behaviour (D-051, alerts 5, 10, 11, 21, 23, 43, 44).

## [1.3.0-rc.1] - 2026-11-20

A minor release candidate: it adds a candidate extension (geodesy) and the changes below, so it is minor under the
versioning rules in CONTRIBUTING.md.

### Fixed

- The release workflow no longer fails when the release already exists (made by hand): it attaches the assets to it instead. Regression test `tests/test_release_workflow.py` (issue #20).

### Added (repository standards for the move to gds-dtx, 17 November 2026)

- Pre-commit hooks: detect-secrets against a new `.secrets.baseline`, YAML and JSON checks, whitespace fixes, and gitlint for GDS Way commit messages (`.gitlint`).
- `.secrets.baseline` with every candidate audited, and the audit recorded in `docs/compliance/secrets-audit.md`.

### Added
- From a like-for-like review of the retired GOV.UK Metadata Weaver prototype (Figma Make), the features it did better:
  - Knowledge: an A to Z over the glossary (letters with no term are shown, unlinked) and search over the glossary
    and the thesaurus.
  - Knowledge: a namespace register of every prefix the profile and its extensions use, with how many properties and
    classes come from each, counted from the profile. The prototype's counts were invented; these are computed.
  - Weaver: open a record from a file (read in the browser, never uploaded, 2 MB limit) and swap From and To, with
    a message when a model can only be read or only be written.
  - The prototype's catalogue, metrics, sign-ins, SDK packages and status banner were not carried over: none of them
    existed. The two packages it told people to install have no such names on PyPI or npm.

### Fixed
- The reference HTTP service no longer returns internal error text to callers; Copy buttons restore their label without re-parsing HTML; host and closing-tag checks are exact (D-040, code scanning).
- Two defects were numbered D-037, and the knowledge page had its Taxonomy heading twice after two pull requests landed in parallel, so the build on main failed. The duplicate is removed, the Adopt page defect is now D-038, and a test rejects a repeated register id (D-039).
- The Adopt page's Words for contracts box showed the literal text `{E(pc)}` instead of the procurement clauses, and Copy the clauses copied that. The clauses now show, and check C-16 now looks inside `pre` blocks for the build's own placeholders (D-038).

### Changed
- Ruff (Python) and ESLint (JavaScript) run in CI and fail on any finding; the lint pass removed dead code and made the validator comparisons in the tests strict (D-038). Part of applying the secure development standard to every project.

### Fixed
- D-037: the first draft of the namespace register linked each namespace. Several do not resolve (the StatDCAT-AP
  namespace contains a literal "(xyz)", and w3id.org/dcat-ap-uk is not registered yet, O-17), so the links would have
  sent people to errors. Namespaces are now shown as code. Check C-26, with a deliberate break.
- Where each product runs is now sourced product by product, each with a check date (D-036). Most lists were
  confirmed at the vendor's own documentation; open-source and cloud-service entries cite the repository they pin.
  Secoda now shows its documented self-hosted, on-premises option. Actian's product page (SaaS) and a 2025 press
  release (also on premises) disagree, and the card says so. Ab Initio's leader position was rechecked and is still
  unconfirmed: Gartner's public abstract lists Ab Initio as evaluated but not where it was placed.

### Added
- Cloud, SaaS, on-premises and open-source vendors on the connectors page, now 31 products in four groups, with a
  "Runs as" filter (SaaS, cloud platform, on premises, self-hosted).
  - Snowflake (Horizon Catalog and Open Catalog), AWS Glue Data Catalog, Amazon SageMaker Catalog (DataZone),
    Oracle OCI Data Catalog, SAP Datasphere, Cloudera, Teradata, Qlik Talend, Precisely, Select Star, Secoda,
    Actian, Apache Polaris, OpenLineage, Amundsen and Egeria.
  - The weaver reads and writes Apache Iceberg REST (Snowflake Open Catalog, Polaris), AWS Glue, SageMaker Catalog,
    OCI Data Catalog and OpenLineage, losing nothing on a round trip.
  - Five new add-on kits: Iceberg table properties, Glue parameters, a SageMaker Catalog metadata form type, an
    OpenLineage facet schema and OCI custom properties.
- The vendor connectors page leads with "Find your product": a matrix of what each product offers (field mapping,
  kit, weaver, MCP server, Claude), filterable by kind, report and need. It also has a map linking reports, products
  and ways to connect, and numbered "How to connect" steps for each product. OvalEdge (open-source MCP server and
  Claude Code plugin), Ataccama and DataGalaxy (MCP servers) join the register. Vendor crosswalks appear in the
  lineage explorer, and a test proves the command-line step works for every vendor format.
- "In Claude" on the vendor connectors page: each vendor's connectors in the Claude connector directory and plugins
  and skills in the plugin directories (Atlan, Collibra, Informatica, DataHub, Databricks for Unity Catalog, Google
  BigQuery, Microsoft Learn), with MCP server, tools, skills, use and source commit. None were found for Alation, IBM,
  data.world, Apache Atlas or OpenMetadata.

### Fixed
- D-035: the OpenLineage facet the weaver writes named an old schema version. `tools/check_vendor_shapes.py` now
  validates weaver output for Glue, SageMaker Catalog, Iceberg REST, OpenLineage and OpenMetadata, plus the OCI and
  DataHub kits, against each vendor's own schema at the cited commit. It runs in CI with ten deliberate breaks.
  Products that pass are marked "Schema-checked".
- D-034: cited vendor commits were padded with invented characters. Citations are now full commit IDs, and
  `tools/check_vendor_repos.py` fetches every one from GitHub in CI.
- Vendor connectors and AI agents (ADR 0021): a page and `downloads/connectors/` for the products in the Gartner Magic
  Quadrants for metadata management and for data and analytics governance, and the Forrester Waves for data governance
  and enterprise data catalogues, plus the platform catalogues beside them (Purview, Apache Atlas, OpenMetadata,
  DataHub, Unity Catalog, Dataplex). Each entry links the vendor's public repositories at a named commit, its MCP
  server, tools and agent skills, a crosswalk mapped from its published model, and an add-on kit in its own extension
  format. The weaver reads and writes Collibra, OpenMetadata, DataHub, Unity Catalog, Dataplex, data.world and Atlas,
  losing nothing on a round trip.
- Trials: new ideas run as time-limited trials declared in `ops/automation.yaml`, each with a hypothesis, an envelope,
  a measure, an abort rule, an end date at most 90 days away and its own kill switch (`TRIAL_<ID>`). `tools/trials.py`
  checks and gates them; the build fails on an expired or malformed trial (ADR 0018).
- Near misses: an occurrence issue form and label, reported without blame; the weekly digest lists occurrences and trials.
- The Status page shows trials and how to report a near miss.

- A provenance register (`tools/provenance.py`, ADR 0020): every labelled fact, worked example, extension example and
  tool sample, where it comes from and what needs a person, on the Status page and in `downloads/provenance.json`.
  The upkeep routine keeps one `provenance` issue up to date, and the digest lists it.

### Changed
- Vendor facts verified at the source and relabelled:
  - Atlan's and Informatica's leader positions now cite their own announcements.
  - Atlan's 2026 governance leader position is added.
  - Snowflake Open Catalog's basis in Apache Polaris and Cloudera's use of Apache Atlas now cite the vendors' own
    documentation.
  - The Iceberg `comment` property cites `TableProperties.COMMENT` in Iceberg's source at the pinned commit.
- Real records replace invented ones wherever a public record exists: the census series and the 2021 release (ONS
  TS007a, with the ONS age variable as reference data), and the OpenAPI, CKAN, schema.org, Dublin Core and DDI samples
  (Food Standards Agency, Environment Agency, The National Archives, ONS). Each names its source and the date checked.
- Every synthetic example says why it cannot be real, and none names a real organisation (D-033). Placeholder company
  and charity numbers are now zeros.
- A plainer look for readers who are not technical, after the xGov MEM site: a white masthead with search up front,
  quieter navigation, plain headings, light cards and tables, and quieter change flags. Every page, tool and check stays (ADR 0019).
- Model maps, after Morgan Maps: the profile page and every class page show how classes connect as cards with a type
  chip and curved links named by the property that makes them. Selecting a card opens its facts and connections.
  The maps work without JavaScript and are checked (a new browser check and deliberate break, `map`).
- Class pages follow the xGov MEM order: the map first, then properties as plain tables by obligation (name, what it
  is, value, how many), then the detail. The codelists a class uses are listed under its map.
- The lineage explorer's trace uses the same card style.
- Publishing is faster: each browser deliberate break stops at its first problem, and four run at once. A break that is
  not caught still runs every check and fails the step. `tests/test_browser_breaks.py` fails if the workflow stops
  running any break listed in `tools/check_browser.py`. Locally, all 18 breaks are still caught.

## [1.2.0-rc.1] - 2026-11-06

A minor release: a new name, tools for suppliers and buyers, and a richer portal. No property changes meaning. Proposed, not endorsed.

### Changed
- Renamed DCAT-AP-UK (the DCAT Application Profile for the UK), after DCAT-AP-NO, -SE and -NL (ADR 0011).
  The profile file is `profile/dcat-ap-uk.yaml` and the proposed namespace is `https://w3id.org/dcat-ap-uk/`.
  The `dcatuk:` prefix stays. The repository was renamed `dcat-ap-uk`, and the site moved to `https://cyberdudeuk.github.io/dcat-ap-uk/` (closes O-16).
- Display options moved to the masthead, beside search and help.

### Added
- A requirements stream (`content/requirements.yaml`, the requirements page, `downloads/requirements.csv` and `.json`
  and a blank template): requirements by theme, layer and status, evidenced and traced, with a proposed work
  programme, L0 to L4 layering, release gates and the chain from evidence to release. Communities are named by kind only (ADR 0015).
- The weaver reads Apache Atlas entities (the Microsoft Purview data map) and never invents a value: no default
  description, licence, language, contact name or classification (RQ-21, RQ-22).
- A candidate geodesy extension: reference frame, coordinate epoch, vertical reference, observation technique and
  uncertainty with confidence level (RQ-23).
- `dcatuk:MissingValue`: say why a property is empty (unknown, withheld, not applicable, not collected, not yet
  available), mapped to the GML and INSPIRE nil reasons. Rule Q-02 warns when it is used for a mandatory property,
  contradicts a value, or names a property the class does not have. A recommended property explained this way is not
  flagged as missing.
- Catalogue records can carry a security classification of their own.
- NATO Core Metadata Specification and the GML nil reasons on the standards map.
- Check C-22: no protective markings or handling caveats anywhere public.
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
- A reuse page: 21 public standards, models, registers, catalogues and toolkits across UK government that fit with
  DCAT-AP-UK, found by scanning the GitHub Repos Asset Catalogue (12,251 repositories) and read at source; the Data Standards
  Authority's 11 endorsed standards, with the address to give in conforms to; what government code actually uses; and the 2023
  Data Marketplace records checked against the profile (97 problems, all fixed or flagged by the existing tools).
- The record builder offers the endorsed standards as one-press suggestions for conforms to.
- Change flags, as the Data Quality Commons has them: every section is fingerprinted at a release, and sections that are
  new or updated since are flagged on their heading, in the page drawer (items and groups), under the page title and in the
  global bar; What's new lists them all, and `downloads/changes-since.json` publishes them (ADR 0016, check C-24).
- Routines do the upkeep and a person keeps control (ADR 0017): every workflow has a tier in `ops/automation.yaml`;
  the change flags reset themselves after each release; a weekly upkeep routine refreshes the organisation list, repairs a
  lagging baseline and reminds about the review date; triage labels waiting issues; a weekly digest issue is the owner's
  one place to look; releases are one button press; `AUTOMATION=off` stops every tier 1 change. Dependency review and
  OpenSSF Scorecard as in the DAM playbooks, and every action pinned to a commit.
- A Status page, as the DAM playbooks have one, with the five self-* routines the GitHub Repos Asset Catalogue runs:
  verification, assessment (including the repository files a well-kept repository needs), staleness, reporting (a health run
  on every build) and repair (`downloads/status.json`).
- Check C-23: no old directorate name and no personal or team details anywhere.
- The geospatial extension says how data is represented (`adms:representationTechnique`, from the INSPIRE spatial
  representation types) and requires geospatial data services to state the OGC standards they conform to (RQ-24).
- Catalogue records can point to the record they were harvested from (`dct:source`) and list the properties they
  enriched (`dcatuk:enrichedProperty`), with a worked example (RQ-08).
- CI checks the generated LinkML file with LinkML's own validator and linter (`tools/check_linkml.py`, with a
  deliberate break), so it agrees with the SHACL, JSON Schema and portal validators (closes O-09).
- Redirect rules for `https://w3id.org/dcat-ap-uk/` (`docs/w3id/`), submitted to w3id.org as pull request 7100 (O-17).
  They follow w3id.org's rules: 303 with content negotiation for terms and codelists, 302 elsewhere, no `Options`.

### Fixed
- D-017 to D-032; see the defect register. The health run now treats a site that refuses automated checking as
  blocked, not broken, as the DAM health run does.
- The geodesy example names the ETRF2000 realisation (EPSG 9067), not the ETRS89 ensemble, as its own guidance asks.
- The EU access-right and data-theme mappings were checked at source and relabelled S (open register O-04).
- Closed O-05 (merged into O-17), O-09, O-12, O-16, O-18, O-24 and O-27; opened O-28 (required checks on main). O-12: the xGov MEM owners were asked, on its
  rename issue (78), to point that repository and its open issues here. O-17: the w3id.org pull request is open (7100).

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
- See the [crosswalk](https://cyberdudeuk.github.io/dcat-ap-uk/changes.html#crosswalk). Every xGov MEM property maps.

### Fixed (xGov MEM issues)
- 69, 71, 72, 76 and the missing IRI for security classification. See the [backlog register](docs/registers.md#backlog-from-the-xgov-mem).
