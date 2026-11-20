---
artefact:id: P05-HLD-001
artefact:version: 1.0.0
artefact:as-of: 2026-11-20
artefact:review-date: 2027-02-20
project: P05 DCAT-AP-UK (proposed)
grade: G3
profile: public sector > central > work
---

# High-level design (HLD): DCAT-AP-UK (proposed)

> **How to read this.** Facts marked V were read from this repository on 20 November 2026. Assumptions, measures and risks are proposals written for this kit, not findings. U means unconfirmed. Where another document in this repository already covers a topic, this one links to it rather than repeating it.

## Building blocks
Derived from the repository's top-level structure (V: git tree, 20 Nov 2026).

| Part | Role | Files |
|---|---|---|
| `docs/` | Documentation and registers | 26 |
| `.github/` | Workflows, issue forms and repository health files | 21 |
| `tools/` | Build, check and routine scripts | 16 |
| `content/` | Content source files (single source) | 13 |
| `tests/` | Automated tests | 13 |
| `profile/` | Profile specification | 5 |
| `integrations/` | Integration kits | 4 |
| `site_src/` | Site source | 4 |
| `examples/` | Examples | 1 |
| `ops/` | Operations: agents, routines, audit | 1 |

## How it fits together
1. Content and data live in the source folders above. They are the single source of truth.
2. The build and check commands in [07-lld.md](07-lld.md) generate the published output from those sources. Generated folders are never edited by hand. (D-KIT-02: an earlier draft named the first command as 'the build', which was wrong for repositories whose first command is a test run.)
3. Checks and tests run locally and in CI before anything is published.
4. Publication happens through the repository's workflow (pages.yml, release.yml).
5. People change things through pull requests and GitHub issue forms. Routines report; a person decides anything irreversible.

## Integrations
- **xGov MEM (endorsed model):** Crosswalk and migration (Live)
- **W3C DCAT 3 / DCAT-AP 3.0.1:** Alignment (Live)
- **Vendor catalogue tools:** Connectors from published models only (ADR 0021) (Partial)
- **NDL PubSec MCP:** Assistants read the profile (Planned)
- **w3id.org:** Persistent identifiers (Proposed (ADR 0006))

## Environments
- **Local:** run the build and checks below.
- **CI:** GitHub Actions. Note: on 20 November 2026 no Actions jobs could start on this account because of a billing block; local checks are the evidence until that is fixed.
- **Live:** https://cyberdudeuk.github.io/dcat-ap-uk/

For the architecture rationale, see [05-sad.md](05-sad.md).
