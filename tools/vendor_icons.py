#!/usr/bin/env python3
"""Vendor the Lucide icons the portal uses into site_src/icons.json (pinned, ISC licence), so pages load nothing from another host.

    npm ci && python3 -I tools/vendor_icons.py

Add a name to ICON_NAMES, rerun, and commit site_src/icons.json. Never edit icons.json by hand: the build fails on a missing icon.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICON_NAMES = sorted(set('''
house database plug file-down layers library-big file-text building-2 message-square map-pin calendar-range fingerprint link badge-check
search menu x chevron-down chevron-right chevron-left sun moon contrast info circle-alert triangle-alert circle-check circle-x list-checks
book-open wrench hammer shield-check scale compass users-round graduation-cap network download share-2 copy printer keyboard
git-pull-request git-branch history route target flag landmark lightbulb heart-handshake eye languages accessibility megaphone
sparkles sliders-horizontal filter arrow-up-down table-2 code-xml braces file-json file-code-2 clipboard-check clipboard-list
map globe workflow boxes blocks puzzle radar refresh-cw clock milestone signpost external-link circle-help mail-x lock lock-open
user-round-x scroll-text pencil-ruler arrow-right arrow-left check minus plus tags tag waypoints split merge gauge leaf mountain
'''.split()))


def main():
    src = ROOT / 'node_modules' / 'lucide-static'
    meta = json.loads((src / 'package.json').read_text())
    out = {'source': 'lucide-static', 'version': meta['version'], 'licence': meta['license'], 'icons': {}}
    missing = []
    for n in ICON_NAMES:
        f = src / 'icons' / f'{n}.svg'
        if not f.exists():
            missing.append(n)
            continue
        body = re.search(r'<svg[^>]*>(.*)</svg>', f.read_text(), re.S).group(1)
        out['icons'][n] = re.sub(r'\s+', ' ', body).strip()
    if missing:
        sys.exit('missing icons: ' + ', '.join(missing))
    (ROOT / 'site_src' / 'icons.json').write_text(json.dumps(out, indent=0, sort_keys=True) + '\n')
    print(len(out['icons']), 'icons vendored from lucide-static', meta['version'])


if __name__ == '__main__':
    main()
