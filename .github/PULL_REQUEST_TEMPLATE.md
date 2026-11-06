## What this changes

## Why

## Checks
- [ ] Edited the source only (`profile/`, `content/`, `examples/`, `site_src/`, `tools/`), not generated files
- [ ] `python3 -I -m unittest discover -s tests` passes
- [ ] `python3 -I tools/check_site.py` and `--vaccinate` pass
- [ ] Any defect fixed has a check with a deliberate break, and an entry in `content/portal.yaml` (governance.defects)
- [ ] No email address, no deck or film, no external script or font
- [ ] Change type stated: major / minor / patch
