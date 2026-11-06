# Security policy

Please report security problems privately. Do not open a public issue.

- **GitHub private vulnerability reporting:** [report a vulnerability](https://github.com/cyberdudeuk/dcat-ap-uk/security/advisories/new).
  This works once the repository owner has switched on private vulnerability reporting.
- **Cabinet Office vulnerability disclosure programme:** for anything affecting government systems, use the
  [Cabinet Office vulnerability disclosure policy](https://vdp.cabinetoffice.gov.uk/).

No email address is published, by the owner's decision (contact is by form only). This departs from the GDS Way's request for a
security contact email; the two private forms above are offered instead.

## What is in scope

The portal is a static site with no server, no accounts, no cookies and no personal data. The most likely issues are cross-site
scripting through generated pages, a Content Security Policy gap, or a supply-chain problem in the build. Every rendered value is
escaped, inline scripts are forbidden by the Content Security Policy, and checks C-01, C-02 and C-11 test this on every build.
