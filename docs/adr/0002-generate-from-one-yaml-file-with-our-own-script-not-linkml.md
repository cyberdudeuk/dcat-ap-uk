# ADR 0002: Generate from one YAML file with our own script, not LinkML

Status: Accepted

## Context

The xGov MEM used LinkML and MkDocs. Ten of its twelve open pull requests were dependency updates to that toolchain, and a LinkML limitation blocked issue 63.

## Decision

One profile file; a small Python generator for SHACL, JSON Schema, JSON-LD context, SKOS and the portal. A LinkML file is still generated for continuity.

## Consequences

Fewer dependencies to patch. CI checks the generated LinkML file with LinkML's own validator and linter, so it cannot drift from the other validators (D-029).

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
