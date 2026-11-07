# ADR 0018: Run the estate as flight operations: test flights with an envelope, near misses reported without blame

Status: Accepted

## Context

ADR 0017 made routines do the upkeep, but said nothing about trying new things safely or learning from what nearly went wrong. A conductor metaphor describes coordination, not safety or experiment. The owner asked for a model that trims waste, prevents incidents and pre-empts threats while still allowing frontier work inside guardrails with kill switches.

## Decision

The estate is run as flight operations, after aviation safety practice: routines are flights inside an envelope (the tiers), the digest and Status page are the instruments, a weekly AI agent is operations control (dispatch and watch, never fly), and a person is pilot in command. Threats are named before they bite, after the Threat and Error Management framework (threats, errors, undesired states). New ideas fly as trials in ops/automation.yaml: each states a hypothesis, an envelope, a measure, an abort rule and an end date at most 90 days away, may only observe or propose, and has its own kill switch (TRIAL_ plus its name) as well as AUTOMATION. Near misses are reported without blame as occurrence issues, after the just culture principle, and each closes with a check or a recorded reason for none.

## Consequences

The build fails if a trial is malformed, touches anything kept for a person, runs over 90 days or passes its end date, so no experiment is left running unowned (tests/test_automation.py Trials, with negative tests for each guardrail). The digest lists occurrences and trials. Nothing new can be merged, released or switched on without a person. The metaphor is a naming aid only: every term maps to a mechanism, and a term without one is dropped.

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
