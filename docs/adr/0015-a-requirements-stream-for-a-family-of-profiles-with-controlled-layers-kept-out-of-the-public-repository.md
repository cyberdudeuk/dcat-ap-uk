# ADR 0015: A requirements stream for a family of profiles, with controlled layers kept out of the public repository

Status: Proposed

## Context

The same needs keep coming up in engagement with catalogue owners, data asset management, discovery services, defence and security users, policing and geospatial teams: a common core, specialist layers, separate handling for records and data, explicit missing values, strict machine validation and honest mappings. Some of those needs can only be specified with material that is not public, and publishing who asked what would aggregate information about protected communities.

## Decision

Keep one public requirements catalogue that names kinds of community only, labels each requirement with its evidence (engagement, verified public source or operating rule) and traces it to properties, rules and tests. Build the open core and its extension points here; list requirements needing controlled material with status Controlled and specify them elsewhere. Add record-level classification and explicit missing values to the core now.

## Consequences

The requirements page counts how many are met, partly met, planned or controlled. C-22 fails the build on any protective marking or caveat, and a test limits the catalogue to kinds of community. No conformance claim is made for any allied or controlled specification.

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
