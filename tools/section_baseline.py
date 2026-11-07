#!/usr/bin/env python3
"""Record every page's sections at a release, so the portal can flag what is new or changed since.

    python3 -I tools/section_baseline.py --ref 975b3be --since 1.2.0-rc.1 --date 2026-11-06   # from a commit or tag
    python3 -I tools/section_baseline.py --since 1.2.0 --date 2027-01-15                      # from the working copy

With --ref, the portal is built from that commit in a temporary git worktree, then fingerprinted with today's
tools/sections.py, so old and new are always measured the same way. Run it once each release, after tagging, and
commit content/section-baseline.json in the same pull request. Automation never runs this: a person decides when
the flags reset.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import sections  # noqa: E402


def build_at(ref, tmp):
    wt = Path(tmp) / 'wt'
    subprocess.run(['git', 'worktree', 'add', '--detach', str(wt), ref], cwd=ROOT, check=True, capture_output=True)
    try:
        subprocess.run([sys.executable, '-I', str(wt / 'tools' / 'build.py')], cwd=wt, check=True, capture_output=True)
        site = wt / 'site'
        return {f.stem: sections.sections(f.read_text(encoding='utf-8')) for f in site.glob('*.html')}
    finally:
        subprocess.run(['git', 'worktree', 'remove', '--force', str(wt)], cwd=ROOT, capture_output=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--ref', help='git commit or tag to build the baseline from (default: the built site in site/)')
    ap.add_argument('--since', required=True, help='the release readers see, for example 1.2.0-rc.1')
    ap.add_argument('--date', required=True, help='the date of that release, yyyy-mm-dd')
    a = ap.parse_args(argv)
    if a.ref:
        with tempfile.TemporaryDirectory() as tmp:
            pages = build_at(a.ref, tmp)
    else:
        pages = {f.stem: sections.sections(f.read_text(encoding='utf-8')) for f in (ROOT / 'site').glob('*.html')}
    pages = {k: v for k, v in sorted(pages.items()) if k not in ('404',)}
    out = {'since': a.since, 'date': a.date, 'ref': a.ref or 'working copy', 'pages': pages}
    sections.BASELINE.write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(f'Baseline for {len(pages)} pages ({sum(len(v) for v in pages.values())} sections) written to '
          f'{sections.BASELINE.relative_to(ROOT)}, since {a.since} ({a.date})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
