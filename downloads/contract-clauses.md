# Open standards and portability clauses for data, digital, cyber and technology contracts

From DCAT Application Profile for the UK 1.2.0-rc.1. A starting point, not legal or commercial advice. Adapt with your commercial and legal teams.

1. Open standards
  1.1 The Supplier shall comply with the open standards in the Schedule of Standards at the requirement level shown, and with any later minor version within six months of its publication.
  1.2 Where the Supplier's product holds, publishes or exchanges metadata about datasets, data services or catalogues, it shall import and export records that conform to DCAT-AP-UK version 1.2 or later, in Turtle and JSON-LD, including every sector extension named in the Order.
  1.3 The Supplier shall not substitute a proprietary format, vocabulary or identifier scheme where the Schedule names an open one, and shall not add private fields where a standard property exists.
  1.4 Where the Supplier believes a requirement cannot be met by an open standard, it shall say so in writing before contract award, with the reason and the proposed alternative, for the Buyer's decision.

2. Conformance and evidence
  2.1 Before acceptance, and with each major release, the Supplier shall run the published DCAT-AP-UK conformance kit and give the Buyer the results: every pass case accepted, every fail case rejected with the rule named, and a round trip that keeps every property.
  2.2 The Supplier shall state the conformance level (1, 2 or 3) its product supports and shall not claim a level its evidence does not show.
  2.3 The Buyer may run the conformance kit, the SHACL shapes or the JSON Schema against the product at any time.

3. Data and metadata ownership and portability
  3.1 All metadata, records, identifiers, codelists, usage policies and lineage created or held for the Buyer are the Buyer's, whatever product holds them.
  3.2 The Supplier shall provide a complete export of all of it in DCAT-AP-UK, and of the data in open formats, on request, at any time, within ten working days, without charge.
  3.3 Identifiers shall be ones the Buyer controls, or open registered identifiers; the Supplier's internal identifiers shall not be the only key.
  3.4 The Supplier shall publish a harvestable catalogue file and a documented open API (OpenAPI) for reading and writing records, with no charge per connection or per partner.

4. Exit and transition
  4.1 At exit the Supplier shall give a full, tested export as above, an account of every field mapping and any loss, and reasonable help to the incoming supplier, at the rates in the contract.
  4.2 The Supplier shall not delete the Buyer's metadata until the Buyer confirms the export is complete and conforms.
  4.3 An exit plan, including the export, shall be kept up to date and tested at least once a year.

5. Change, versions and technical debt
  5.1 The Supplier shall support each new minor version of DCAT-AP-UK and of the standards in the Schedule within six months, and each major version within an agreed migration period.
  5.2 The Supplier shall tell the Buyer of any change to its product that affects conformance, before it is released.
  5.3 The Supplier shall keep a register of deviations from the Schedule, with a plan and date to remove each, and report it quarterly.

6. Security, privacy and the future
  6.1 The Supplier shall record the cryptographic algorithms protecting the Buyer's data and services as identifiers, support strong checksums (SHA-256 or stronger), and provide a plan to migrate to post-quantum cryptography in line with the NCSC timeline.
  6.2 The Supplier shall keep each record's security classification, personal data status, jurisdictions and transfer safeguard, and shall not move data outside the jurisdictions recorded without the Buyer's written agreement.
  6.3 The Supplier shall not use the Buyer's data or metadata to train, fine-tune or evaluate AI models except as the record's use for AI and usage policy allow.

7. Accessibility and openness
  7.1 User interfaces shall meet WCAG 2.2 at level AA, with a published accessibility statement.
  7.2 Contact points shall be stored as team names and contact form addresses; the product shall not require a named person or a personal email address.

## Schedule of standards

- DCAT-AP-UK: Must. Wherever the product holds, publishes or exchanges metadata. https://cyberdudeuk.github.io/dcat-ap-uk/
- W3C DCAT 3: Must. Wherever the product holds, publishes or exchanges metadata. https://www.w3.org/TR/vocab-dcat-3/
- DCAT-AP 3.0.1: Must. Wherever the product holds, publishes or exchanges metadata. https://semiceu.github.io/DCAT-AP/releases/3.0.1/
- DCAT-AP HVD: Must. Wherever the product holds, publishes or exchanges metadata. https://semiceu.github.io/DCAT-AP/releases/3.0.0-hvd/
- xGov MEM v0.1.0: Must. Wherever the product holds, publishes or exchanges metadata. https://github.com/co-cddo/ukgov-metadata-exchange-model
- Data Marketplace schemas: Must. Wherever the product holds, publishes or exchanges metadata. https://github.com/co-cddo/data-catalogue-metadata
- Future pan-UK metadata architecture: Must. Wherever the product holds, publishes or exchanges metadata. https://github.com/co-cddo/future-panuk-metadata-architecture
- Dublin Core Terms: Must. As DCAT-AP-UK uses them; no private substitutes. https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
- SKOS: Must. As DCAT-AP-UK uses them; no private substitutes. https://www.w3.org/TR/skos-reference/
- FOAF: Must. As DCAT-AP-UK uses them; no private substitutes. http://xmlns.com/foaf/spec/
- vCard ontology: Must. As DCAT-AP-UK uses them; no private substitutes. https://www.w3.org/TR/vcard-rdf/
- ADMS: Must. As DCAT-AP-UK uses them; no private substitutes. https://semiceu.github.io/ADMS/releases/2.00/
- PROV-O: Must. As DCAT-AP-UK uses them; no private substitutes. https://www.w3.org/TR/prov-o/
- DQV: Must. As DCAT-AP-UK uses them; no private substitutes. https://www.w3.org/TR/vocab-dqv/
- SPDX: Must. As DCAT-AP-UK uses them; no private substitutes. https://spdx.org/
- ISA Core Location: Must. As DCAT-AP-UK uses them; no private substitutes. https://semiceu.github.io/Core-Location-Vocabulary/
- GeoSPARQL: Must. As DCAT-AP-UK uses them; no private substitutes. https://www.ogc.org/standards/geosparql/
- ODRL 2.2: Must. As DCAT-AP-UK uses them; no private substitutes. https://www.w3.org/TR/odrl-model/
- EU Vocabularies: Must. As DCAT-AP-UK uses them; no private substitutes. https://op.europa.eu/en/web/eu-vocabularies
- ISO 3166 country codes: Must. As DCAT-AP-UK uses them; no private substitutes. https://www.iso.org/iso-3166-country-codes.html
- IANA media types: Must. As DCAT-AP-UK uses them; no private substitutes. https://www.iana.org/assignments/media-types/
- HealthDCAT-AP R7: Must, where the sector applies. When the buyer names the sector extension. https://healthdataeu.pages.code.europa.eu/healthdcat-ap/
- GeoDCAT-AP 3.1: Must, where the sector applies. When the buyer names the sector extension. https://semiceu.github.io/GeoDCAT-AP/
- StatDCAT-AP: Must, where the sector applies. When the buyer names the sector extension. https://semiceu.github.io/StatDCAT-AP/
- mobilityDCAT-AP: Must, where the sector applies. When the buyer names the sector extension. https://mobilitydcat-ap.github.io/mobilityDCAT-AP/
- MLDCAT-AP 3.x: Must, where the sector applies. When the buyer names the sector extension. https://semiceu.github.io/MLDCAT-AP/
- BRegDCAT-AP: Must, where the sector applies. When the buyer names the sector extension. https://interoperable-europe.ec.europa.eu/collection/access-base-registries/solution/bregdcat-ap
- Dataspace Protocol: Must, where the sector applies. When the buyer names the sector extension. https://projects.eclipse.org/projects/technology.dataspace-protocol-base
- UK GEMINI 2.3: Must, where the sector applies. When the buyer names the sector extension. https://www.agi.org.uk/gemini/
- MEDIN: Must, where the sector applies. When the buyer names the sector extension. https://www.medin.org.uk/medin-discovery-metadata-standard
- HDR UK Gateway schema: Must, where the sector applies. When the buyer names the sector extension. https://github.com/HDRUK/schemata
- Ofgem Data Best Practice: Must, where the sector applies. When the buyer names the sector extension. https://www.ofgem.gov.uk/
- ISO 19115: Must, where the sector applies. When the buyer names the sector extension. https://www.iso.org/standard/53798.html
- INSPIRE metadata: Must, where the sector applies. When the buyer names the sector extension. https://inspire.ec.europa.eu/
- GML and INSPIRE nil reasons: Must. As DCAT-AP-UK uses them; no private substitutes. https://dd.eionet.europa.eu/vocabulary/common/NilReasonType/view
- NATO Core Metadata Specification (ADatP-5636): Must, where the sector applies. When the buyer names the sector extension. https://nhqc3s.hq.nato.int/apps/architecture/nisp/volume1/apd.html
- DCAT-US 3.0: Should. Accept for exchange with partner countries. https://resources.data.gov/
- DCAT-AP-NO: Should. Accept for exchange with partner countries. https://data.norge.no/specification/dcat-ap-no
- DCAT-AP.de: Should. Accept for exchange with partner countries. https://www.dcat-ap.de/
- DCAT-AP-NL 3.0: Should. Accept for exchange with partner countries. https://www.geonovum.nl/
- DCAT-AP_IT: Should. Accept for exchange with partner countries. https://www.dati.gov.it/
- schema.org Dataset: Should. Import and export, through the weaver mappings or natively. https://schema.org/Dataset
- Croissant 1.1: Should. Import and export, through the weaver mappings or natively. https://docs.mlcommons.org/croissant/
- Dublin Core 15 elements: Should. Import and export, through the weaver mappings or natively. https://www.dublincore.org/specifications/dublin-core/dces/
- DDI Codebook: Should. Import and export, through the weaver mappings or natively. https://ddialliance.org/Specification/DDI-Codebook/2.5/
- CKAN and ckanext-dcat: Should. Import and export, through the weaver mappings or natively. https://github.com/ckan/ckanext-dcat
- OpenAPI: Must. For publishing, validation and interfaces. https://spec.openapis.org/oas/latest.html
- SHACL: Must. For publishing, validation and interfaces. https://www.w3.org/TR/shacl/
- JSON Schema 2020-12: Must. For publishing, validation and interfaces. https://json-schema.org/
- JSON-LD 1.1: Must. For publishing, validation and interfaces. https://www.w3.org/TR/json-ld11/
- RDF 1.1 Turtle: Must. For publishing, validation and interfaces. https://www.w3.org/TR/turtle/
- LinkML: Must. For publishing, validation and interfaces. https://linkml.io/
- Model Context Protocol: Must. For publishing, validation and interfaces. https://modelcontextprotocol.io/
- llms.txt: Must. For publishing, validation and interfaces. https://llmstxt.org/
- Data Asset Management Policy: Must comply. As law, policy or guidance requires. https://cyberdudeuk.github.io/dam-capability-playbooks/
- Government Security Classifications: Must comply. As law, policy or guidance requires. https://www.gov.uk/government/publications/government-security-classifications
- UK GDPR and ICO transfer guidance: Must comply. As law, policy or guidance requires. https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/
- Open Government Licence v3.0: Must comply. As law, policy or guidance requires. https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
- NCSC post-quantum timeline: Must comply. As law, policy or guidance requires. https://www.ncsc.gov.uk/guidance/pqc-migration-timelines
- FIPS 203: Must comply. As law, policy or guidance requires. https://csrc.nist.gov/projects/post-quantum-cryptography
- Code of Practice for Statistics: Must comply. As law, policy or guidance requires. https://code.statisticsauthority.gov.uk/
- WCAG 2.2: Must comply. As law, policy or guidance requires. https://www.w3.org/TR/WCAG22/
- org-id.guide: Must comply. As law, policy or guidance requires. https://org-id.guide/
