# ADR 0012: Integrations through a conformance kit and one reference implementation

Status: Accepted

## Context

Suppliers need to show conformance without reading the whole profile, and customers need to check claims.

## Decision

Publish test records with expected verdicts, level badges, a command line, a local HTTP API and a GitHub Action, all running validator.js.

## Consequences

A product conforms when it gives the expected verdict on every kit record. Product entries are background knowledge until each supplier confirms them (O-19).

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
