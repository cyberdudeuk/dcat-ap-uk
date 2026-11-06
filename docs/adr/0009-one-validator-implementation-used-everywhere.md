# ADR 0009: One validator implementation, used everywhere

Status: Accepted

## Context

The quality score, levels, converters and exports could be written twice, in Python for the build and JavaScript for the browser, and drift.

## Decision

They live once, in site_src/validator.js. The build, the MCP server and the browser all run it; Python checks only what SHACL and JSON Schema check.

## Consequences

Building needs Node. Tests compare the browser Turtle with the build RDF so the two paths cannot drift.

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
