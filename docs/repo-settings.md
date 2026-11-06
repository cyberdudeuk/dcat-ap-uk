# Repository settings: owner checklist

The build sets everything it can as files in the repository. These settings can only be changed by the repository owner,
in the repository settings. They were open register items O-16 and O-18. All were set on 6 November 2026, except required status checks (O-28).

| Setting | Value | Where | Status, 6 November 2026 |
|---|---|---|---|
| Rename the repository | `dcat-ap-uk` (ADR 0011). GitHub redirects the old name; update `site_url` and `repo_url` in `profile/dcat-ap-uk.yaml` afterwards | Settings → General | Done |
| Description | DCAT-AP-UK: the DCAT Application Profile for the UK. Proposed, not endorsed. | About (cog) | Done |
| Website | The Pages address | About (cog) | Done |
| Topics | dcat, dcat-ap, dcat-ap-uk, metadata, data-catalogue, linked-data, shacl, json-schema, open-standards, uk-government, interoperability | About (cog) | Done |
| Social preview | `site/og.png` from a build, if present | Settings → General | Not applicable: the build makes no `og.png` |
| Features | Issues on; Discussions on; Wiki off; Projects optional | Settings → General | Done (Issues and Discussions on, Wiki off) |
| Merge | Squash merging only; delete branches after merge; suggest updating branches | Settings → General | Done (squash only) |
| Pages | Source: deploy from a branch, `gh-pages`, folder `/` (the pages workflow pushes it) | Settings → Pages | Done |
| Branch protection for main | Require the pages and CodeQL checks; require linear history; no force pushes | Settings → Rules | Partly: ruleset "Protect main" blocks deletion and force pushes and requires linear history; required checks are a decision (O-28) |
| Private vulnerability reporting | On | Settings → Security | Done |
| Dependabot alerts and security updates | On | Settings → Security | Done |
| Secret scanning and push protection | On | Settings → Security | Done |
| CodeQL | Uses `.github/workflows/codeql.yml` (advanced setup); leave default setup off | Settings → Security | Done |
| Labels | Run the Labels workflow once | Actions → Labels | Done (Labels workflow ran) |

No email address belongs in any of these. Contact is by the contact form only.
