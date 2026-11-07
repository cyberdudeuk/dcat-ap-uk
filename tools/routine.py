#!/usr/bin/env python3
"""Run a tier 1 routine safely (ADR 0017, ops/automation.yaml).

    python3 -I tools/routine.py flags-reset --tag v1.2.0     # after a release: change flags measure from this release
    python3 -I tools/routine.py upkeep                       # weekly: organisations, baseline lag, review reminder
    python3 -I tools/routine.py upkeep --dry-run             # say what would change, change nothing

Every routine follows the same steps, so a person can trust any of them the same way:
  1. Stop if the kill switch is off (repository variable AUTOMATION=off): report what would have changed.
  2. Make the change in the working copy.
  3. Build and run the checks. If anything fails, change nothing and fail loudly, so the digest shows it.
  4. Commit as github-actions with the routine named (trailer "Routine: <id>"), so it is one revert to undo.
  5. Push, then ask the Pages workflow to republish (a push by the workflow token does not start it by itself).
Changes too big to make alone become a pull request or an issue for a person (tier 2).
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
BOT = ('github-actions[bot]', '41898282+github-actions[bot]@users.noreply.github.com')
ORG_LIMIT = 25  # more organisation rows than this changing at once needs a person to look (tier 2)


def sh(*cmd, check=True, capture=False):
    r = subprocess.run(cmd, cwd=ROOT, check=check, text=True, capture_output=capture)
    return r.stdout.strip() if capture else r.returncode


def summary(text):
    print(text)
    p = os.environ.get('GITHUB_STEP_SUMMARY')
    if p:
        with open(p, 'a', encoding='utf-8') as f:
            f.write(text + '\n')


def automation_on():
    return os.environ.get('AUTOMATION', '').strip().lower() != 'off'


def verify():
    """Build and run the fast checks. The full browser suite runs in the Pages workflow before anything is published."""
    sh(PY, '-I', 'tools/build.py')
    sh(PY, '-I', 'tools/check_site.py')
    sh(PY, '-I', '-m', 'unittest', 'discover', '-s', 'tests')


def changed(paths):
    return bool(sh('git', 'status', '--porcelain', '--', *paths, capture=True))


def commit_and_publish(routine, paths, message, dry):
    if not changed(paths):
        summary(f'**{routine}**: nothing to change.')
        return False
    if dry or not automation_on():
        why = 'dry run' if dry else 'the kill switch is off (AUTOMATION=off)'
        summary(f'**{routine}**: would commit {", ".join(paths)} ({why}); changed nothing.')
        sh('git', 'checkout', '--', *paths)
        return False
    verify()
    sh('git', '-c', f'user.name={BOT[0]}', '-c', f'user.email={BOT[1]}', 'add', *paths)
    sh('git', '-c', f'user.name={BOT[0]}', '-c', f'user.email={BOT[1]}', 'commit', '-q', '-m', f'{message}\n\nRoutine: {routine}\nTier: 1 (ops/automation.yaml)')
    for attempt in range(3):  # main may have moved while the checks ran
        if sh('git', 'push', '-q', 'origin', 'HEAD:main', check=False) == 0:
            break
        sh('git', 'pull', '-q', '--rebase', 'origin', 'main')
    else:
        raise SystemExit(f'{routine}: could not push after 3 tries')
    if os.environ.get('GH_TOKEN'):
        sh('gh', 'workflow', 'run', 'pages.yml', '--ref', 'main', check=False)
    summary(f'**{routine}**: committed {", ".join(paths)} and asked Pages to republish. Undo: revert the commit "{message}".')
    return True


def flags_reset(tag, dry):
    since = tag[1:] if tag.startswith('v') else tag
    when = sh('git', 'log', '-1', '--format=%cs', tag, capture=True)
    base = json.loads((ROOT / 'content' / 'section-baseline.json').read_text(encoding='utf-8'))
    if base.get('since') == since:
        summary(f'**flags-reset**: the baseline already measures from {since}.')
        return False
    sh(PY, '-I', 'tools/section_baseline.py', '--ref', tag, '--since', since, '--date', when)
    return commit_and_publish('flags-reset', ['content/section-baseline.json'], f'Reset change flags to {since}', dry)


def latest_release_tag():
    tags = sh('git', 'tag', '--list', 'v*', '--sort=-v:refname', capture=True).split()
    return tags[0] if tags else None


def orgs(dry):
    p = ROOT / 'profile' / 'organisations.json'
    before = {o['slug']: o for o in json.loads(p.read_text(encoding='utf-8'))['orgs']}
    sh(PY, '-I', 'tools/import_orgs.py', '--govuk')
    after = {o['slug']: o for o in json.loads(p.read_text(encoding='utf-8'))['orgs']}
    rows = [k for k in set(before) | set(after) if before.get(k, {}).get('status') != after.get(k, {}).get('status')
            or before.get(k, {}).get('title') != after.get(k, {}).get('title') or (k in before) != (k in after)]
    if not rows:
        sh('git', 'checkout', '--', str(p.relative_to(ROOT)))
        summary('**organisations**: no organisation changed on GOV.UK.')
        return False
    detail = ', '.join(sorted(rows)[:12]) + (' and more' if len(rows) > 12 else '')
    if len(rows) > ORG_LIMIT:
        return propose('organisations', [str(p.relative_to(ROOT))], f'Refresh the organisation list ({len(rows)} changed)',
                       f'GOV.UK lists {len(rows)} changed organisations, more than the {ORG_LIMIT} a routine may change alone. Changed: {detail}.', dry)
    return commit_and_publish('organisations', [str(p.relative_to(ROOT))], f'Refresh organisations from GOV.UK ({len(rows)} changed: {detail})', dry)


def propose(routine, paths, title, body, dry):
    """Tier 2: put the change on a branch and open a pull request for a person; fall back to an issue if Actions may not open pull requests."""
    if dry or not automation_on():
        summary(f'**{routine}**: would propose "{title}"; changed nothing.')
        sh('git', 'checkout', '--', *paths)
        return False
    verify()
    branch = f'routine/{routine}-{date.today().isoformat()}'
    sh('git', 'checkout', '-q', '-b', branch)
    sh('git', '-c', f'user.name={BOT[0]}', '-c', f'user.email={BOT[1]}', 'commit', '-q', '-am', f'{title}\n\nRoutine: {routine}\nTier: 2 (ops/automation.yaml)')
    sh('git', 'push', '-q', 'origin', branch)
    note = body + '\n\nThe routine built the site and ran the checks on this change. A person decides whether to merge (tier 2, ops/automation.yaml).'
    if sh('gh', 'pr', 'create', '--base', 'main', '--head', branch, '--title', title, '--body', note, '--label', 'routine', check=False) != 0:
        sh('gh', 'issue', 'create', '--title', title, '--label', 'routine', '--body',
           note + f'\n\nThe change is on branch `{branch}`. Actions may not open pull requests in this repository, so open one from that branch.', check=False)
    summary(f'**{routine}**: proposed "{title}" for a person (tier 2).')
    return True


def review_reminder(dry):
    """Tier 0: an issue when the review date is within 30 days. Never changes the date: reviewing is a person's job."""
    import yaml
    meta = yaml.safe_load((ROOT / 'profile' / 'dcat-ap-uk.yaml').read_text(encoding='utf-8'))['meta']
    days = (date.fromisoformat(str(meta['review'])) - date.today()).days
    if days > 30:
        summary(f'**review**: {days} days until the review date.')
        return
    title = f'Content review due by {meta["review"]}'
    if dry or not os.environ.get('GH_TOKEN'):
        summary(f'**review**: would open "{title}".')
        return
    open_ = sh('gh', 'issue', 'list', '--label', 'review due', '--state', 'open', '--json', 'number', '--jq', '.[0].number', capture=True)
    body = (f'The review date in profile/dcat-ap-uk.yaml is {meta["review"]}, {days} days away. A person re-reads the pages, '
            'the sources marked watch: manual in content/lineage.yaml and the open register, then moves the review date on. '
            'Opened by the upkeep routine (tier 0).')
    if open_:
        sh('gh', 'issue', 'comment', open_, '--body', f'Still due: {days} days left.', check=False)
    else:
        sh('gh', 'issue', 'create', '--title', title, '--label', 'review due', '--body', body, check=False)
    summary(f'**review**: {days} days left; issue opened or updated.')


def provenance_issue(dry):
    """Tier 0: keep one issue (label provenance) listing what needs a person or a reviewed pull request: facts to verify
    (K, U), checks out of date, samples to replace. Never changes content: relabelling a fact needs its source checked."""
    sys.path.insert(0, str(ROOT / 'tools'))
    import provenance
    reg = provenance.register()
    todo = [x for x in reg['items'] if x['action']]
    if reg['unexplained_synthetic'] or reg['misattributed']:
        summary(f'**provenance**: {reg["unexplained_synthetic"]} unexplained synthetic, {len(reg["misattributed"])} misattributed (the tests fail on these).')
    if not todo:
        summary('**provenance**: nothing needs a person.')
        return
    lines = [f'{len(todo)} items need verifying or replacing. Counts: ' + ', '.join(f'{k} {v}' for k, v in sorted(reg['counts'].items())) + '.', '',
             'Verify each against an authoritative source, then relabel it V with the date and address checked, or correct it. '
             'Synthetic content stays only where nothing genuine can be shown in public, and must say why. The Status page lists the same items.', '']
    by = {}
    for x in todo:
        by.setdefault(x['file'], []).append(x)
    for f, xs in sorted(by.items()):
        lines.append(f'### {f} ({len(xs)})')
        lines += [f'- [ ] {x["item"]} ({x["prov"]}): {x["action"]}' for x in xs[:40]]
        lines.append('')
    lines.append('Opened and kept up to date by the upkeep routine (tier 0, ADR 0020).')
    body = '\n'.join(lines)
    title = 'Content to verify or replace'
    if dry or not os.environ.get('GH_TOKEN'):
        summary(f'**provenance**: would open or update "{title}" with {len(todo)} items.')
        return
    open_ = sh('gh', 'issue', 'list', '--label', 'provenance', '--state', 'open', '--json', 'number', '--jq', '.[0].number', capture=True)
    if open_:
        sh('gh', 'issue', 'edit', open_, '--body', body, check=False)
    else:
        sh('gh', 'issue', 'create', '--title', title, '--label', 'provenance', '--body', body, check=False)
    summary(f'**provenance**: {len(todo)} items listed in the provenance issue.')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('routine', choices=['flags-reset', 'upkeep'])
    ap.add_argument('--tag')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    if not automation_on():
        summary('Kill switch is off (AUTOMATION=off): reporting only.')
    if a.routine == 'flags-reset':
        flags_reset(a.tag or latest_release_tag(), a.dry_run)
    else:
        orgs(a.dry_run)
        tag = latest_release_tag()
        if tag:  # self-repair: the baseline lags the latest release if the flags-reset step after it failed
            flags_reset(tag, a.dry_run)
        review_reminder(a.dry_run)
        provenance_issue(a.dry_run)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
