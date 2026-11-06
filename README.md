# DCAT Application Profile for the UK (DCAT-AP-UK)

> **Proposed, not endorsed.** DCAT-AP-UK 1.2.0-rc.1 is a proposal for review by the Metadata Implementation Working Group. It has not
> been endorsed by the Data Standards Authority, and it is not an official GOV.UK service or policy. The endorsed model remains the
> [UK Cross-Government Metadata Exchange Model](https://co-cddo.github.io/ukgov-metadata-exchange-model/) (xGov MEM) until a decision is made.

One way to describe UK public sector datasets and data services, so they can be found, judged and shared across every catalogue.
Built on the W3C [DCAT 3](https://www.w3.org/TR/vocab-dcat-3/) Recommendation, aligned with [DCAT-AP 3.0.1](https://semiceu.github.io/DCAT-AP/releases/3.0.1/),
and evolved from the xGov MEM, whose whole backlog it resolves.

**Portal:** https://cyberdudeuk.github.io/dcat-ap-uk/

The profile is named after other national DCAT-AP profiles (DCAT-AP-NO, DCAT-AP-SE, DCAT-AP-NL). The repository was first called `dcat-uk-ap` and was renamed `dcat-ap-uk` on 6 November 2026; GitHub redirects the old address, but the old GitHub Pages address no longer serves the site.

## Who it is for, and where to start

| You are | You want to | Start at |
|---|---|---|
| A catalogue manager | Export records central services can harvest | [What's changed](https://cyberdudeuk.github.io/dcat-ap-uk/changes.html#crosswalk), then [Check records](https://cyberdudeuk.github.io/dcat-ap-uk/validate.html) |
| A data owner or steward | Record a critical data asset once | [Build a record](https://cyberdudeuk.github.io/dcat-ap-uk/builder.html), with "critical data asset" ticked |
| A chief data officer or policy coordinator | Decide whether to adopt it | [Strategy](https://cyberdudeuk.github.io/dcat-ap-uk/strategy.html) and [governance](https://cyberdudeuk.github.io/dcat-ap-uk/governance.html#status) |
| An engineer or supplier | Validate and build to it | [Downloads](https://cyberdudeuk.github.io/dcat-ap-uk/downloads.html): SHACL, JSON Schema, JSON-LD context, codelists |
| New to metadata | Understand why it matters | [Your role](https://cyberdudeuk.github.io/dcat-ap-uk/roles.html#start), with an Easy Read summary |
| Any organisation, in any sector | Adopt it | [Adoption toolkit](https://cyberdudeuk.github.io/dcat-ap-uk/adopt.html), [sector extensions](https://cyberdudeuk.github.io/dcat-ap-uk/extensions.html) and [check many records](https://cyberdudeuk.github.io/dcat-ap-uk/bulk.html) |
| Sharing data across borders | Record where data goes and on what basis | [Cross-border data flows](https://cyberdudeuk.github.io/dcat-ap-uk/international.html) |
| A supplier or integrator | Prove a product conforms | [Integrations](https://cyberdudeuk.github.io/dcat-ap-uk/integrations.html): conformance kit, badges, command line, HTTP API and GitHub Action |
| A buyer or commercial lead | Avoid lock-in in a contract | [Avoiding lock-in](https://cyberdudeuk.github.io/dcat-ap-uk/lockin.html) and the model clauses |
| Building with AI | Know what data may be used for, and let assistants read the profile | [AI-ready metadata](https://cyberdudeuk.github.io/dcat-ap-uk/ai-ready.html) and the [MCP server](integrations/mcp/) |

## What changed from the xGov MEM

- Every property of the xGov MEM maps to the profile, so existing records convert automatically ([crosswalk](https://cyberdudeuk.github.io/dcat-ap-uk/changes.html#crosswalk)).
- All 22 open issues in the xGov MEM repository are dealt with: 19 resolved, 2 resolved but marked provisional pending research, 1 needs the owner (registering the w3id.org namespace). See the [backlog register](docs/registers.md#backlog-from-the-xgov-mem).
- New, from that backlog: geographic coverage, time period, schema, personal data, sensitive data, reference data, who can see a record.
- Critical data assets get the extra mandatory properties the April 2026 GOV.UK guidance lists.
- Codelists are linked data (SKOS), mapped to the EU vocabularies DCAT-AP uses. Themes are the data.gov.uk topics.
- Contact points prefer a contact form and never name a person.

## New in 1.2

- Renamed DCAT-AP-UK; namespace `https://w3id.org/dcat-ap-uk/` (ADR 0011).
- A metadata weaver: seven readers and nine writers (DCAT-AP-UK, xGov MEM, CKAN, DCAT-US, schema.org, Dublin Core, DDI, JSON-LD, Turtle, Croissant).
- A lineage explorer, a standards map of about 60 related standards, insights charts and a visual site map.
- For suppliers: a conformance kit with expected verdicts, level badges, and the validator as a command line, a local HTTP API and a GitHub Action.
- For buyers: how open standards prevent lock-in and technical debt, with model contract clauses.
- A user guide, guided tours and tutorials; display options in the masthead.
- A requirements stream: requirements by theme, layer (L0 to L4) and status, evidenced and traced to release, with release gates and a proposed work programme. Communities are named by kind only.
- The weaver reads Apache Atlas (Microsoft Purview data map) entities and invents nothing; a candidate geodesy module.
- Record-level security classification, and explicit missing values with a reason (rule Q-02).
- From the xGov MEM portal: class diagrams, value types, the profile in tables, a licence page and a feedback link on every page.

### Use it in a pipeline

```yaml
- uses: actions/checkout@v4
- uses: cyberdudeuk/dcat-ap-uk@main   # pin to a release tag or commit
  with:
    files: metadata/*.json
```

```sh
node integrations/cli/validate.js --format text records/*.json     # exits 1 on any error
node integrations/http/server.js                                    # POST /validate, /score, /weave on 127.0.0.1:8787
```

## New in 1.1

- Nine sector extensions (health, geospatial, statistics, transport, high-value datasets, AI-ready, data spaces, private and voluntary sector, energy), aligned with HealthDCAT-AP, GeoDCAT-AP and UK GEMINI, StatDCAT-AP, mobilityDCAT-AP, DCAT-AP HVD, MLDCAT-AP and Croissant, the Dataspace Protocol, org-id.guide and Ofgem Data Best Practice.
- Cross-border flows across the UK nations, Crown Dependencies, Overseas Territories, the Commonwealth and partners, with the UK GDPR transfer safeguard checked by rule R-08.
- A quality score modelled on the EU metadata quality assessment, and three conformance levels.
- AI-ready (usage policies, schema.org and Croissant, llms.txt, an MCP server) and quantum-ready (strong checksums, connection security for the post-quantum inventory).
- An adoption toolkit, a bulk CSV checker, an OpenAPI converter, and a scan of DCAT profiles around the world.
- It implements the [future pan-UK metadata architecture](https://github.com/co-cddo/future-panuk-metadata-architecture) (co-cddo; private repository). Reconciling the two is open register O-14.

## How this repository works

One source, everything else generated:

```
profile/dcat-ap-uk.yaml     the profile: classes, properties, obligations, rules  (edit here)
profile/codelists.yaml      the codelists                                          (edit here)
profile/extensions.yaml     sector extensions: only add properties or raise obligations    (edit here)
profile/crosswalks.yaml     crosswalks to CKAN, Dublin Core, UK GEMINI, HDR UK, Croissant  (edit here)
profile/organisations.json  GOV.UK organisations, reused from the GitHub Repos Asset Catalogue (tools/import_orgs.py)
content/lineage.yaml        sources, the xGov MEM backlog and how each item was dealt with
content/portal.yaml         roles, glossary, strategy, estate comparison, governance registers
content/toolkit.yaml        landscape scan, adoption toolkit, cross-border, AI and quantum content
examples/examples.yaml      worked examples, checked on every build
integrations/mcp/           MCP server for AI assistants, using site_src/validator.js
integrations/cli/, http/    command line and local HTTP API; action.yml is the GitHub Action
content/guide.yaml          user guide, tutorials and tours
content/standards.yaml      related standards and the typed links between them
content/integrations.yaml   integration patterns and products; content/lockin.yaml: lock-in and contract clauses
tools/                      ukap.py (load and check), generate.py (SHACL, JSON Schema, context, LinkML, SKOS, CSV), build.py (portal)
site_src/                   stylesheet, behaviour, and the browser validator shared with the tests
tests/                      the three validators held to the same verdict; deliberate breaks for every rule
docs/                       registers and decisions, generated from content/portal.yaml
```

### Build and check locally

```sh
pip install -r requirements.txt && npm ci && python3 -m playwright install chromium
python3 -I -m unittest discover -s tests        # profile, schemas and validator agree; every break fails
python3 -I tools/build.py                        # writes site/ and docs/
python3 -I tools/check_site.py                   # 22 structural checks
python3 -I tools/check_site.py --vaccinate       # proves each check catches its deliberate break
python3 -I tools/check_browser.py                # axe-core, widths 320-1920, light and dark, keyboard, tools, no-script
```

Every check is trusted only because a deliberate break proves it fails (`--vaccinate`, `--break NAME`). Every defect found gets a
check in the same commit as its fix, recorded in the [defect register](docs/registers.md#defect-register).

## Changing the profile

Raise a [change request](https://github.com/cyberdudeuk/dcat-ap-uk/issues/new?template=change-request.yml). Changes are assessed as major, minor or patch
(semantic versioning), reviewed by the Metadata Implementation Working Group, decided by the owning team and, for major changes, endorsed by the Data
Standards Authority. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Part of a wider estate

DCAT-AP-UK is the fourth of four open portals for data in the public sector, each with its own owner, purpose and status. They link and share keys; they do not merge.

| Bearing | Portal | Question |
|---|---|---|
| North | [DAM capability playbooks](https://cyberdudeuk.github.io/dam-capability-playbooks/) | What must we do, and who does it? |
| East | [Public Sector Data Quality Commons](https://cyberdudeuk.github.io/dq-commons/) | How do I do it well? |
| West | [GitHub Repos Asset Catalogue](https://cyberdudeuk.github.io/github-repos-asset-catalogue/) | What already exists? |
| South | DCAT-AP-UK (this) | How do we describe it so others can find it? |

The [estate compass](https://cyberdudeuk.github.io/dam-capability-playbooks/compass/) suggests a route across all four. Shared keys are in [`xref.json`](https://cyberdudeuk.github.io/dcat-ap-uk/xref.json).

## Contact

By form only: the [contact form](https://github.com/cyberdudeuk/dcat-ap-uk/issues/new?template=contact.yml). It is public, so do not include personal data.
Security problems: [report privately](SECURITY.md). No email address is published.

## Licence

Content and the profile: [Open Government Licence v3.0](LICENCE-CONTENT.md), derived from the xGov MEM (OGL v3.0). Code: [MIT](LICENSE).
Third-party components: [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

Built with help from Claude, an AI model by Anthropic. Every generated fact is checked by tests or labelled with its source:
V verified at the source (dated), K background knowledge, P from a supplied pack, U unconfirmed.
