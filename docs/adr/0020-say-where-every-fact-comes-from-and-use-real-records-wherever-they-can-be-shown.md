# ADR 0020: Say where every fact comes from, and use real records wherever they can be shown

Status: Accepted

## Context

The portal used invented records and samples to show its features, and some facts were labelled background knowledge (K) with no check behind them. Some invented examples named real organisations. The owner asked for genuine, authoritative content wherever it exists, synthetic content only where it must be, and routines that keep it checked.

## Decision

tools/provenance.py builds a register of every labelled fact, worked example, extension example and tool sample on every build, shown on the Status page and in downloads/provenance.json. A fact needs action when it is K or U, or when its V check is undated or more than 180 days old (sources watched by the weekly health run count as re-checked). Worked examples and tool samples use real public records, each with its source and the date checked; a sample written in another metadata model says so. Synthetic content stays only where nothing genuine can be shown in public (an unpublished critical data asset, personal data shared across a border, a conformance claim no real catalogue has made, candidate extensions no publisher uses yet), states why, and never names a real organisation. The upkeep routine keeps one provenance issue listing what needs a person; the weekly operations-control agent verifies up to ten K or U facts a week through a pull request, never relabelling without a source.

## Consequences

tests/test_provenance.py fails on unexplained synthetic content, on synthetic content under a real publisher and on an undeclared example address in the tools, with negative tests for each. The census examples and five of the seven tool samples are now real (the FSA hygiene ratings API and CKAN package, the Environment Agency river levels, The National Archives CAB 360, the ONS Living Costs and Food Survey). The DCAT-US sample is still invented and listed for replacement; the Purview sample stays invented because data map entities are not published.

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
