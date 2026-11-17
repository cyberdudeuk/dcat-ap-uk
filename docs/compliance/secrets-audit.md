# Secrets scan audit

Scanned on 17 November 2026 with detect-secrets 1.5.0 over every tracked file (excluding `node_modules`,
`vendor` and lock files). The results are recorded in [`.secrets.baseline`](../../.secrets.baseline).

- Candidates found: 293
- Audited as real secrets: 0

Each candidate was read in context and judged not to be a secret:

12-character section fingerprints (`content/section-baseline.json`), SHA-256 content hashes of tracked sources (`content/source-state.json`), Git commit SHAs of checked vendor repositories (`content/vendors.yaml`), and hashed name detectors in `tools/check_site.py` (hashes, not names).

New commits are checked by the detect-secrets pre-commit hook against this baseline. If the hook flags a
new string, read it, and either remove it or audit it into the baseline with `detect-secrets audit .secrets.baseline`.
Never audit a real credential as a false positive: remove it and rotate it.
