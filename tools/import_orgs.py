#!/usr/bin/env python3
"""Refresh profile/organisations.json, the organisation list for publisher and creator.

Reuse before building: the list is taken from the GitHub Repos Asset Catalogue (register R3 key, the GOV.UK organisation slug),
which read the GOV.UK organisations API on 31 October 2026. Pass the catalogue's build/dama/hier.json:

    python3 -I tools/import_orgs.py PATH/TO/github-repos-asset-catalogue/build/dama/hier.json

Closed organisations are kept and flagged, so records that name them still resolve after machinery of government changes.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    src = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    orgs = []
    for row in src['orgs']:
        slug, title, abbr, otype, status = row[:5]
        orgs.append({'slug': slug, 'title': title, 'abbr': abbr or None, 'type': otype, 'status': status,
                     'uri': f'https://www.gov.uk/government/organisations/{slug}'})
    out = {'source': src['source']['url'], 'read': src['source']['read'], 'via': 'GitHub Repos Asset Catalogue, build/dama/hier.json',
           'prov': 'P', 'count': len(orgs), 'orgs': sorted(orgs, key=lambda o: o['slug'])}
    if len(orgs) != src['source']['n']:
        sys.exit(f'expected {src["source"]["n"]} organisations, got {len(orgs)}')
    (ROOT / 'profile' / 'organisations.json').write_text(json.dumps(out, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
    print(f'{len(orgs)} organisations written')


if __name__ == '__main__':
    main(sys.argv)
