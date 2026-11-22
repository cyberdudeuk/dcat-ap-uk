#!/usr/bin/env python3
"""Check that every element a verified crosswalk names exists in that standard's own published definition (D-045).

profile/crosswalks.yaml gives, for each crosswalk marked V, the addresses it was checked at (`checked_at`, several
joined by " and "). This fetches them and fails if any element named in the rows is not found in that text, so a
renamed or removed element is caught at the next build rather than published. Whether each pairing is the best one
stays a judgement for each community (open register O-04); this only checks that the names are real.

    python3 -I tools/check_crosswalk_names.py

Needs network access; CI runs it on every build. Exit 1 on any missing element.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PREFIXES = ('extras ', 'resource ', 'organization and extras ')


def elements(crosswalk_id, theirs):
    """The element names one row's 'their' column claims exist, in the form the standard's own text spells them."""
    if theirs.strip() in ('(none)', '(class)'):
        return []
    out = []
    for part in theirs.split(' and '):
        part = re.sub(r'\s*\(.*?\)', '', part).strip()
        for p in PREFIXES:
            if part.startswith(p):
                part = part[len(p):]
        if crosswalk_id == 'croissant' and part.startswith('related '):
            continue
        if part and part not in ('extras', 'organization'):
            out.append(part)
    return out


def schema_paths(schema):
    """Every dotted property path a JSON Schema defines, following $ref, anyOf, oneOf and allOf."""
    defs = schema.get('$defs') or schema.get('definitions') or {}
    paths, seen = set(), set()

    def walk(node, prefix):
        if not isinstance(node, dict):
            return
        ref = node.get('$ref')
        if ref:
            key = (ref, prefix)
            if key in seen:
                return
            seen.add(key)
            walk(defs.get(ref.split('/')[-1], {}), prefix)
        for k in ('anyOf', 'oneOf', 'allOf'):
            for x in node.get(k, []):
                walk(x, prefix)
        for name, sub in (node.get('properties') or {}).items():
            path = f'{prefix}.{name}' if prefix else name
            paths.add(path)
            walk(sub, path)
        if isinstance(node.get('items'), dict):
            walk(node['items'], prefix)
    walk(schema, '')
    return paths


def missing(crosswalk_id, rows, text):
    """Every element named in rows that the definition does not have.

    A JSON Schema (HDR UK) is checked by full dotted path; a second path in a row ("startDate and endDate") shares the
    first one's parent. Labels (GEMINI, Dublin Core) match case-insensitively; other names match as written."""
    try:
        paths = schema_paths(json.loads(text))
    except ValueError:
        paths = None
    hay = text.lower() if crosswalk_id in ('gemini', 'dublin-core') else text
    gone = []
    for row in rows:
        parent = ''
        for e in elements(crosswalk_id, row[1]):
            if paths is not None:
                full = e if '.' in e or not parent else f'{parent}.{e}'
                parent = full.rsplit('.', 1)[0] if '.' in full else parent
                if full not in paths:
                    gone.append(full)
            elif (e.lower() if crosswalk_id in ('gemini', 'dublin-core') else e) not in hay:
                gone.append(e)
    return gone


def raw(url):
    """A GitHub blob address, pinned to a full commit, is read as its raw file."""
    m = re.match(r'https://github\.com/([^/]+/[^/]+)/blob/([0-9a-f]{40})/(.+)$', url)
    if m:
        return [f'https://raw.githubusercontent.com/{m[1]}/{m[2]}/{m[3]}']
    return [url]


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'dcat-ap-uk-crosswalks/1.0 (+https://github.com/cyberdudeuk/dcat-ap-uk)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', errors='ignore')


def main():
    cws = yaml.safe_load((ROOT / 'profile' / 'crosswalks.yaml').read_text(encoding='utf-8'))
    problems = 0
    for cid, cw in cws.items():
        if cw.get('prov') != 'V':
            continue
        text = ''.join(fetch(u) for part in str(cw['checked_at']).split(' and ') for u in raw(part.strip()))
        gone = missing(cid, cw['rows'], text)
        print(f'{cid}: ' + ('every element found' if not gone else 'not found: ' + ', '.join(gone)))
        problems += len(gone)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
