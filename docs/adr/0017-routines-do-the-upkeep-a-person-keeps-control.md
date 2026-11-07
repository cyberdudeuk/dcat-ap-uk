# ADR 0017: Routines do the upkeep; a person keeps control

Status: Accepted

## Context

Keeping the portal right took a person for chores: resetting the change flags at each release, refreshing the organisation list after machinery of government changes, watching sources, chasing issues and reading many separate signals. Chores that rely on someone remembering get missed, as D-031 and D-032 showed. The same is true across the connected portals.

## Decision

Every workflow is declared in ops/automation.yaml with a tier: 0 observe, 1 maintain (changes derived or reference data on its own, only after every check passes, in one commit naming the routine), 2 propose (a pull request or issue for a person) and 3 person only (releases, settings, deletions, anything sent outside the repository, claims). tools/routine.py runs every tier 1 routine the same way. The change flags reset straight after each release; upkeep runs weekly; triage labels waiting issues; a weekly digest issue is the owner's one place to look. A repository variable, AUTOMATION=off, stops every tier 1 change. Across the estate, a weekly conductor reads each repository's digest and status, writes an estate digest and opens pull requests for a person; it never merges.

## Consequences

A person presses one button to release and reads one digest a week. tests/test_automation.py fails if a workflow is undeclared, a tier 1 routine ignores the kill switch, an action is not pinned to a commit or permissions are not declared. Routine commits are signed off with a Routine trailer, so the digest lists them and each is one revert to undo.

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
