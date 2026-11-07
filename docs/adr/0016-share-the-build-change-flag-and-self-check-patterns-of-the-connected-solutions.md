# ADR 0016: Share the build, change-flag and self-check patterns of the connected solutions

Status: Accepted

## Context

DCAT-AP-UK links to and is linked from the Data Quality Commons, the DAM capability playbooks, the GitHub Repos Asset Catalogue and the Knowledge Web. They share one way of building a portal (generated pages, a retractable drawer, display options, a colophon, checks with deliberate breaks) but had drifted: only the Data Quality Commons flagged what changed, only the DAM playbooks published a status page and only the catalogue ran a repository self-assessment. A reader moving between them met different conventions.

## Decision

Adopt the three missing patterns. Change flags as the Data Quality Commons does them: a section baseline recorded at each release (tools/section_baseline.py), with New and Updated flags on drawer items and groups, on section headings, under page titles and in the global bar, and a list on What's new. A Status page as the DAM playbooks build it, fed by a health run on every build. The five self-* routines (verification, assessment, staleness, reporting, repair) as the catalogue reports them. Not adopted: GitHub Discussions voting and the ask-a-question assistant, which need the owning team to decide on moderation and hosting first.

## Consequences

C-24 fails the build if a flag disagrees with downloads/changes-since.json; status.json and changes-since.json are machine-readable. Someone runs section_baseline.py at each release so flags reset; until then they accumulate. Flags count words only, so restyling never flags a section.

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
