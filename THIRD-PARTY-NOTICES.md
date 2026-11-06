# Third-party notices

| Component | Version | Licence | Where | Shipped in the site? |
|---|---|---|---|---|
| Lucide icons (lucide-static) | 1.69.0 | ISC | `site_src/icons.json`, vendored by `tools/vendor_icons.py` | Yes, as inline SVG paths |
| UK Cross-Government Metadata Exchange Model | v0.1.0 | Open Government Licence v3.0 | definitions and usage notes adapted in `profile/` | Yes, adapted text |
| GOV.UK organisations list, via the GitHub Repos Asset Catalogue | read 31 October 2026 | Open Government Licence v3.0 | `profile/organisations.json` | Yes |
| axe-core | 4.14.0 | MPL-2.0 | `node_modules/`, tests only | No |
| PyYAML, rdflib, pySHACL, jsonschema, segno, python-barcode, Playwright | see `requirements.txt` | MIT, BSD-3-Clause, Apache-2.0, BSD | build and tests only | No (QR and barcode SVG are generated output) |

The ISC licence for Lucide: Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part of Feather (MIT). All other
copyright (c) for Lucide are held by Lucide Contributors 2022. Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.
