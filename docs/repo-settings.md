# Repository settings: owner checklist

The build sets everything it can as files in the repository. These settings can only be changed by the repository owner,
in the repository settings. They are open register item O-18 (and O-16 for the rename).

| Setting | Value | Where |
|---|---|---|
| Rename the repository | `dcat-ap-uk` (ADR 0011). GitHub redirects the old name; update `site_url` and `repo_url` in `profile/dcat-ap-uk.yaml` afterwards | Settings → General |
| Description | DCAT-AP-UK: the DCAT Application Profile for the UK. Proposed, not endorsed. | About (cog) |
| Website | The Pages address | About (cog) |
| Topics | dcat, dcat-ap, dcat-ap-uk, metadata, data-catalogue, linked-data, shacl, json-schema, open-standards, uk-government, interoperability | About (cog) |
| Social preview | `site/og.png` from a build, if present | Settings → General |
| Features | Issues on; Discussions on; Wiki off; Projects optional | Settings → General |
| Merge | Squash merging only; delete branches after merge; suggest updating branches | Settings → General |
| Pages | Source: deploy from a branch, `gh-pages`, folder `/` (the pages workflow pushes it) | Settings → Pages |
| Branch protection for main | Require the pages and CodeQL checks; require linear history; no force pushes | Settings → Rules |
| Private vulnerability reporting | On | Settings → Security |
| Dependabot alerts and security updates | On | Settings → Security |
| Secret scanning and push protection | On | Settings → Security |
| CodeQL | Uses `.github/workflows/codeql.yml` (advanced setup); leave default setup off | Settings → Security |
| Labels | Run the Labels workflow once | Actions → Labels |

No email address belongs in any of these. Contact is by the contact form only.
