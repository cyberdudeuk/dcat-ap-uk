#!/usr/bin/env python3
"""Check the generated LinkML schema with LinkML's own validator (D-029; closed O-09).

Every worked example must pass, and every deliberate break of a single-property rule must fail, as they do for the
SHACL shapes, the JSON Schema and validator.js. Cross-property rules (R-01 to R-08) are not expressed in LinkML, so their
breaks are skipped and counted. Exit 1 on any disagreement.

    python3 tools/check_linkml.py            # uses site/downloads/dcat-ap-uk.linkml.yaml from the last build
    python3 tools/check_linkml.py --break     # proves the check fails when the schema is wrong
"""
import copy
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import ukap  # noqa: E402

from linkml.validator import validate  # noqa: E402

SINGLE_PROPERTY_RULES = {'M-01', 'V-01', 'D-01', 'U-01', 'N-01', 'N-02', 'B-01', 'S-04', 'R-06'}


def normalise(p, ck, rec):
    """The JSON form accepts one value or a list for multi-valued properties; LinkML wants a list."""
    out = {}
    slots = {x['p']: x for x in p.classes[ck]['properties']} if ck in p.classes else {}
    for k, v in rec.items():
        if k == 'class':
            continue
        x, prop = slots.get(k), p.props.get(k)
        if x and p.multi(x) and not isinstance(v, list):
            v = [v]
        if prop and prop['kind'] == 'object':
            def one(o):
                return normalise(p, prop['range'], o) if isinstance(o, dict) else o
            v = [one(o) for o in v] if isinstance(v, list) else one(v)
        out[k] = v
    return out


def problems(schema_path):
    p = ukap.load()
    sv = str(schema_path)
    bad, skipped = [], 0
    for e in p.examples:
        rec = e['record']
        rep = validate(normalise(p, rec['class'], rec), sv, rec['class'])
        if rep.results:
            bad.append(f'example {e["key"]} fails LinkML: {rep.results[0].message[:160]}')
    fx = yaml.safe_load((ROOT / 'tests' / 'fixtures' / 'invalid.yaml').read_text(encoding='utf-8'))
    for f in fx:
        if f['rule'] not in SINGLE_PROPERTY_RULES:
            skipped += 1
            continue
        rec = f['record']
        rep = validate(normalise(p, rec['class'], rec), sv, rec['class'])
        if not rep.results:
            bad.append(f'break {f["key"]} (rule {f["rule"]}) passes LinkML but must fail')
    return bad, skipped


def main():
    src = ROOT / 'site' / 'downloads' / 'dcat-ap-uk.linkml.yaml'
    if '--break' in sys.argv:
        # a schema that has forgotten the identifier slot, as the generator once did, must be caught
        doc = yaml.safe_load(src.read_text(encoding='utf-8'))
        doc['slots'].pop('id')
        for c in doc['classes'].values():
            c['slots'] = [s for s in c['slots'] if s != 'id']
        tmp = Path('/tmp/dcat-ap-uk.broken.linkml.yaml')
        tmp.write_text(yaml.safe_dump(doc, sort_keys=False), encoding='utf-8')
        bad, _ = problems(tmp)
        if bad:
            print(f'pass check_linkml catches its deliberate break ({len(bad)} problems)')
            return 0
        print('FAIL check_linkml did not catch its deliberate break')
        return 1
    bad, skipped = problems(src)
    for b in bad:
        print('FAIL', b)
    if bad:
        return 1
    print(f'pass LinkML agrees: every example passes, every single-property break fails ({skipped} cross-property breaks are SHACL-only)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
