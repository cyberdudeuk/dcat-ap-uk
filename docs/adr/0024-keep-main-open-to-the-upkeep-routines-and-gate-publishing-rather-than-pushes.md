# ADR 0024: Keep main open to the upkeep routines, and gate publishing rather than pushes

Status: Accepted

## Context

O-28 asked whether main should require the pages and CodeQL checks to pass before any change lands. Checked on 22 November 2026: the ruleset "Protect main" is active and blocks deletion and force pushes and requires linear history. Two tier 1 routines push to main directly (tools/routine.py commit_and_publish): the change-flag reset after a release, and the organisations refresh. The Pages workflow publishes only after every check passes, and CodeQL runs on every push to main. The repository has one maintainer, who works through pull requests. OpenSSF Scorecard reports the missing required checks as its Branch-Protection alert.

## Decision

Decided under the owner's delegation of 22 November 2026: keep the ruleset as it is and do not require status checks. A change that fails its checks on main is never published, because publishing is the gate; the weekly health run and the Status page show it.

## Consequences

Rejected: requiring the checks, which would turn both tier 1 routines into pull requests a person must merge each time, adding recurring work for a single maintainer to guard against something the publish gate already stops reaching readers. Accepted risk: main can be red for a short time after a direct push, though never on the live site. The Scorecard Branch-Protection alert stays open, with this ADR as its answer. Revisit if a second maintainer joins or a routine ever publishes without the checks: the change is one rule in Settings, then Rules.

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
