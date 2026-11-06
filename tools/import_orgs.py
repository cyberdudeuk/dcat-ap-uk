#!/usr/bin/env python3
"""Refresh profile/organisations.json, the organisation list for publisher and creator.

Reuse before building: the list is taken from the GitHub Repos Asset Catalogue (register R3 key, the GOV.UK organisation slug),
which read the GOV.UK organisations API on 31 October 2026. Pass the catalogue's build/dama/hier.json:

    python3 -I tools/import_orgs.py PATH/TO/github-repos-asset-catalogue/build/dama/hier.json

Or read the GOV.UK organisations API directly (added after the July 2026 machinery of government change, which the
catalogue's 31 October snapshot did not yet show):

    python3 -I tools/import_orgs.py --govuk

Closed organisations are kept and flagged, so records that name them still resolve after machinery of government changes.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def from_govuk():
    """Every organisation from the GOV.UK organisations API, in the same shape as the catalogue's rows."""
    import urllib.request
    from datetime import date
    rows, url = [], 'https://www.gov.uk/api/organisations?page=1'
    while url:
        req = urllib.request.Request(url, headers={'User-Agent': 'dcat-ap-uk-orgs/1.0 (+https://github.com/cyberdudeuk/dcat-ap-uk)'})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode('utf-8'))
        for o in d['results']:
            det = o['details']
            rows.append([det['slug'], o['title'], det.get('abbreviation'), o['format'], det['govuk_status']])
        url = d.get('next_page_url')
    return {'orgs': rows, 'source': {'url': 'https://www.gov.uk/api/organisations', 'read': date.today().isoformat(), 'n': len(rows)}}


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    if argv[1] == '--govuk':
        src = from_govuk()
        via = 'GOV.UK organisations API, read directly'
    else:
        src = None
        via = 'GitHub Repos Asset Catalogue, build/dama/hier.json'
    src = src or json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    orgs = []
    for row in src['orgs']:
        slug, title, abbr, otype, status = row[:5]
        orgs.append({'slug': slug, 'title': title, 'abbr': abbr or None, 'type': otype, 'status': status,
                     'uri': f'https://www.gov.uk/government/organisations/{slug}'})
    out = {'source': src['source']['url'], 'read': src['source']['read'], 'via': via,
           'prov': 'V' if argv[1] == '--govuk' else 'P', 'count': len(orgs), 'orgs': sorted(orgs, key=lambda o: o['slug'])}
    if len(orgs) != src['source']['n']:
        sys.exit(f'expected {src["source"]["n"]} organisations, got {len(orgs)}')
    (ROOT / 'profile' / 'organisations.json').write_text(json.dumps(out, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
    print(f'{len(orgs)} organisations written')


if __name__ == '__main__':
    main(sys.argv)
