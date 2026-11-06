# ADR 0007: Sector extensions that only add or raise

Status: Accepted

## Context

Sectors need more than the base (health, geospatial, statistics, transport, AI, data spaces, energy). DCAT-AP solves this with separate extension profiles; the future pan-UK architecture plans domain profiles too.

## Decision

Extensions in one file, merged onto the base at build time. An extension may raise an obligation, narrow a cardinality, add a pattern, a property or a class; the build refuses one that weakens the base. Each gets its own shapes and schema.

## Consequences

A record that conforms to an extension conforms to the base. Sector terms from other namespaces are cited, not copied; terms this profile adds stay provisional (O-13).

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
