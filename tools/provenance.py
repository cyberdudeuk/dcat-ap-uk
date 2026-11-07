"""Provenance register: where every fact, example and sample in the portal comes from, and what needs a person (ADR 0020).

It reads the content and profile files and the build's built-in samples, and lists:
  - every item labelled with a provenance code (V verified, S sourced, K background knowledge, P supplied pack,
    O owner, U unconfirmed, E estimate), with its source address and, for V, the date it was last checked;
  - every worked example, extension example and tool sample, and whether it describes something real or is synthetic.

Something needs action when it is K or U (verify it against an authoritative source), when a V check is undated or
older than STALE_DAYS, or when synthetic content has no stated reason for being synthetic. Synthetic content is allowed
only where nothing genuine can be shown in public (an internal critical data asset, personal data shared across a
border), and must say so in its `synthetic:` field.

    python3 tools/provenance.py            # print the summary; exit 1 if synthetic content is unexplained
    python3 tools/provenance.py --json F   # also write the register to F
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STALE_DAYS = 180
LABELS = {'V': 'verified', 'S': 'sourced', 'K': 'background knowledge', 'P': 'supplied pack', 'O': 'owner', 'U': 'unconfirmed', 'E': 'estimate'}
MONTHS = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
                                       'november', 'december'], 1)}
FAKE = re.compile(r'https?://(?:[a-z0-9-]+\.)*example\.(?:org|com)\b')
# Built-in tool samples live in tools/build.py; each must be declared here with what it is and why.
SAMPLES_DECL = ROOT / 'content' / 'samples.yaml'


def checked_on(item):
    """The date a V item was last checked: a `checked:` field, or 'Checked 6 November 2026' in its note or text."""
    if item.get('checked'):
        try:
            return dt.date.fromisoformat(str(item['checked']))
        except ValueError:
            return None
    for f in ('note', 'text', 'evidence', 'what'):
        m = re.search(r'[Cc]hecked (\d{1,2}) ([A-Za-z]+) (\d{4})', str(item.get(f) or ''))
        if m and m.group(2).lower() in MONTHS:
            return dt.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
    return None


def name_of(item):
    for f in ('label', 'title', 'name', 'id', 'key', 'text', 'what'):
        if item.get(f):
            s = str(item[f])
            return s if len(s) <= 110 else s[:108] + '…'
    return '(unnamed)'


def walk(node, path, out):
    if isinstance(node, dict):
        if 'prov' in node and str(node['prov'])[:1] in LABELS:
            out.append((path, node))
        for k, v in node.items():
            walk(v, f'{path}.{k}', out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f'{path}[{i}]', out)


def labelled(today):
    """Facts with a provenance code. A V item takes its check date from its own `checked:` or note, else from its file's
    `as_of`; a source watched by the weekly health run (content/source-state.json) counts as re-checked every week."""
    rows = []
    watched = set(json.loads((ROOT / 'content' / 'source-state.json').read_text(encoding='utf-8')))
    files = sorted((ROOT / 'content').glob('*.yaml')) + sorted((ROOT / 'profile').glob('*.yaml'))
    for f in files:
        if f.name == 'samples.yaml':
            continue
        doc = yaml.safe_load(f.read_text(encoding='utf-8'))
        file_date = None
        if isinstance(doc, dict) and doc.get('as_of'):
            file_date = dt.date.fromisoformat(str(doc['as_of']))
        found = []
        walk(doc, '', found)
        for path, it in found:
            code = str(it['prov'])[:1]
            is_watched = f.name == 'lineage.yaml' and it.get('id') in watched
            when = (checked_on(it) or file_date) if code == 'V' else None
            age = (today - when).days if when else None
            need = None
            if code in ('K', 'U'):
                need = 'verify against an authoritative source and relabel V with the date checked'
            elif code == 'E':
                need = 'state the method, or replace with a published figure'
            elif code == 'V' and is_watched:
                need = None  # the weekly health run fingerprints it and opens an issue if it changes
            elif code == 'V' and when is None:
                need = 'record the date it was checked'
            elif code == 'V' and age > STALE_DAYS:
                need = f're-check: last checked {age} days ago'
            rows.append({'kind': 'fact', 'file': f.relative_to(ROOT).as_posix(), 'path': path.lstrip('.'), 'item': name_of(it), 'prov': code,
                         'url': it.get('url') or it.get('source') or '', 'checked': str(when) if when else ('watched weekly' if is_watched else None), 'action': need})
    return rows


def examples():
    rows = []
    for e in yaml.safe_load((ROOT / 'examples' / 'examples.yaml').read_text(encoding='utf-8')):
        fake = bool(FAKE.search(json.dumps(e['record'])))
        rows.append({'kind': 'worked example', 'file': 'examples/examples.yaml', 'path': e['key'], 'item': e['label'], 'prov': 'U' if not fake else 'synthetic',
                     'url': '' if fake else str(e['record'].get('id', '')), 'synthetic': e.get('synthetic') if isinstance(e.get('synthetic'), str) else None,
                     'source': e.get('source'), 'record': e['record'],
                     'action': ('state why it is synthetic, or replace it with a real public record' if fake and not e.get('synthetic') else
                                'compare with the publisher\'s record each review' if not fake else None)})
    ext = yaml.safe_load((ROOT / 'profile' / 'extensions.yaml').read_text(encoding='utf-8'))
    base = ext.get('synthetic_base') or {}
    if base:
        rows.append({'kind': 'extension base record', 'file': 'profile/extensions.yaml', 'path': 'synthetic_base', 'item': base.get('title', 'base record'),
                     'prov': 'synthetic', 'url': '', 'synthetic': ext.get('synthetic_reason'), 'record': base,
                     'action': None if ext.get('synthetic_reason') else 'state why it is synthetic'})
    for x in ext.get('extensions', []):
        e = x.get('example') or {}
        if not e:
            continue
        add = e.get('add', {})
        on_real = e.get('base') and not FAKE.search(json.dumps(add))
        rows.append({'kind': 'extension example', 'file': 'profile/extensions.yaml', 'path': f'{x["id"]}.example', 'item': add.get('title') or f'{x["label"]} example',
                     'prov': 'U' if on_real else 'synthetic', 'url': '', 'synthetic': None if on_real else (e.get('synthetic') or ext.get('synthetic_reason')),
                     'record': add, 'action': ('compare the added values with the publisher\'s own documentation' if on_real else
                                               None if (e.get('synthetic') or ext.get('synthetic_reason')) else 'state why it is synthetic')})
    return rows


def samples():
    """Built-in samples in tools/build.py: each example.org address there must be declared in content/samples.yaml."""
    decl = yaml.safe_load(SAMPLES_DECL.read_text(encoding='utf-8')) if SAMPLES_DECL.exists() else []
    src = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
    rows = []
    for d in decl:
        rows.append({'kind': 'tool sample', 'file': 'tools/build.py', 'path': d['id'], 'item': d['label'], 'prov': 'synthetic' if d.get('synthetic') else d.get('prov', 'U'),
                     'url': d.get('url', ''), 'synthetic': d.get('synthetic'), 'source': d.get('source'),
                     'action': ('replace with a real public record' if d.get('replace') else None if (d.get('synthetic') or d.get('prov') == 'V') else 'compare with the source each review')})
    declared = {u for d in decl for u in d.get('addresses', [])}
    undeclared = sorted({m.group(0) for m in re.finditer(r'https?://(?:[a-z0-9-]+\.)*example\.(?:org|com)[^\s\'"<>)]*', src)} - declared)
    for u in undeclared:
        rows.append({'kind': 'tool sample', 'file': 'tools/build.py', 'path': u, 'item': f'Undeclared example address {u}', 'prov': 'synthetic',
                     'url': '', 'synthetic': None, 'action': 'declare it in content/samples.yaml with its reason, or replace it with a real address'})
    return rows


REAL_ORG = re.compile(r'https?://www\.gov\.uk/government/organisations/[a-z0-9-]+')


def misattributed(rows):
    """Synthetic content must never name a real organisation as its publisher or creator."""
    bad = []
    for r in rows:
        if r['prov'] != 'synthetic' or not isinstance(r.get('record'), dict):
            continue
        for f in ('publisher', 'creator'):
            v = json.dumps(r['record'].get(f) or '')
            if REAL_ORG.search(v):
                bad.append(f"{r['file']} {r['path']}: {f} is a real organisation")
    return bad


def register(today=None):
    today = today or dt.date.today()
    rows = labelled(today) + examples() + samples()
    counts = {}
    for r in rows:
        counts[r['prov']] = counts.get(r['prov'], 0) + 1
    unexplained = [r for r in rows if r['prov'] == 'synthetic' and not r.get('synthetic')]
    wrong = misattributed(rows)
    for r in rows:
        r.pop('record', None)
    return {'misattributed': wrong,'generated': str(today), 'stale_days': STALE_DAYS, 'counts': counts, 'needs_action': sum(1 for r in rows if r['action']),
            'unexplained_synthetic': len(unexplained), 'items': rows}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--json')
    a = ap.parse_args(argv)
    reg = register()
    if a.json:
        Path(a.json).write_text(json.dumps(reg, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Provenance:', ', '.join(f'{k} {v}' for k, v in sorted(reg['counts'].items())), f'| needs action {reg["needs_action"]}',
          f'| unexplained synthetic {reg["unexplained_synthetic"]}')
    for r in reg['items']:
        if r['prov'] == 'synthetic' and not r.get('synthetic'):
            print('UNEXPLAINED', r['file'], r['path'], '-', r['item'])
    for m in reg['misattributed']:
        print('MISATTRIBUTED', m)
    return 1 if reg['unexplained_synthetic'] or reg['misattributed'] else 0


if __name__ == '__main__':
    sys.exit(main())
