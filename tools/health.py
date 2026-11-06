#!/usr/bin/env python3
"""Weekly health run: are the sources still there and unchanged, is the review date close, are pages inside their weight envelope?

    python3 -I tools/health.py [--out build/health.json] [--record]

Reads every V-labelled source in content/lineage.yaml and compares a hash of its text with content/source-state.json.
--record stores the current hashes (do this in the same pull request that re-verifies a changed source).
Automation never changes content: it reports. Exit code 1 if anything needs a person.
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / 'content' / 'source-state.json'


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'dcat-ap-uk-health/1.0 (+https://github.com/cyberdudeuk/dcat-uk-ap)'})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode('utf-8', errors='ignore')
    text = re.sub(r'<script.*?</script>|<style.*?</style>|<[^>]+>', ' ', body, flags=re.S)
    return hashlib.sha256(re.sub(r'\s+', ' ', text).strip().encode()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'build' / 'health.json'))
    ap.add_argument('--record', action='store_true')
    a = ap.parse_args(argv)
    lin = yaml.safe_load((ROOT / 'content' / 'lineage.yaml').read_text(encoding='utf-8'))
    meta = yaml.safe_load((ROOT / 'profile' / 'dcat-ap-uk.yaml').read_text(encoding='utf-8'))['meta']
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    problems, report = [], {'run': date.today().isoformat(), 'sources': [], 'review': meta['review']}
    for s in lin['sources']:
        if s['prov'] != 'V':
            continue
        try:
            h = fetch(s['url'])
            changed = s['id'] in state and state[s['id']] != h
            report['sources'].append({'id': s['id'], 'ok': True, 'changed': changed})
            if changed:
                problems.append(f'Source changed: {s["title"]} ({s["url"]}). Re-verify what the profile relies on, then run health.py --record.')
            if a.record:
                state[s['id']] = h
        except Exception as e:  # noqa: BLE001 - every failure is reported, none is fatal
            report['sources'].append({'id': s['id'], 'ok': False, 'error': str(e)[:200]})
            problems.append(f'Source unreachable: {s["title"]} ({s["url"]}): {str(e)[:120]}')
    days = (date.fromisoformat(meta['review']) - date.today()).days
    if days < 0:
        problems.append(f'Review date {meta["review"]} has passed. Review the content, then move meta.review forward.')
    elif days < 14:
        problems.append(f'Review date {meta["review"]} is in {days} days.')
    site = ROOT / 'site'
    if site.exists():
        heavy = [f'{p.name}: {p.stat().st_size // 1000} KB' for p in site.glob('*.html') if p.stat().st_size > 1_500_000]
        problems += [f'Page over the 1,500 KB envelope: {h}' for h in heavy]
    report['problems'] = problems
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=1) + '\n')
    if a.record:
        STATE.write_text(json.dumps(state, indent=1, sort_keys=True) + '\n')
    print('\n'.join(problems) or 'Healthy: every source reachable and unchanged, review date not due, pages inside the envelope.')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
