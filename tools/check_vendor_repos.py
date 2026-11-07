#!/usr/bin/env python3
"""Check that every repository commit cited in content/vendors.yaml exists on GitHub (D-034, ADR 0021).

Each citation is a full 40-character commit ID, fetched by ID from the public repository, so an ID that was shortened,
padded or made up fails. Exit 1 on any miss. Needs network access to github.com; CI runs it on every build.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def citations(vd):
    for x in vd['vendors']:
        for r in x.get('repos', []):
            yield x['id'], r['repo'], str(r.get('commit', ''))
        for c in x.get('claude', []):
            if c.get('repo'):
                yield x['id'], c['repo']['repo'], str(c['repo'].get('commit', ''))


def exists(repo, sha):
    if len(sha) != 40 or any(ch not in '0123456789abcdef' for ch in sha):
        return False
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['git', 'init', '-q', tmp], check=True)
        r = subprocess.run(['git', '-C', tmp, 'fetch', '-q', '--depth', '1', '--filter=blob:none', f'https://github.com/{repo}', sha],
                           capture_output=True, text=True, timeout=120, env={'GIT_TERMINAL_PROMPT': '0', 'PATH': '/usr/bin:/bin:/usr/local/bin'})
        return r.returncode == 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--file', default=str(ROOT / 'content' / 'vendors.yaml'))
    a = ap.parse_args(argv)
    vd = yaml.safe_load(Path(a.file).read_text(encoding='utf-8'))
    bad = 0
    seen = set()
    for vid, repo, sha in citations(vd):
        if (repo, sha) in seen:
            continue
        seen.add((repo, sha))
        ok = exists(repo, sha)
        bad += not ok
        print(('pass' if ok else 'FAIL') + f' {vid}: {repo}@{sha[:12]}')
    print(f'{len(seen) - bad} of {len(seen)} cited commits found on GitHub')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
