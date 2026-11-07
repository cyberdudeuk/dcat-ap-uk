# ADR 0021: Vendor connectors from published models only, with each vendor's AI offer beside them

Status: Accepted

## Context

The owner asked for connectors, add-ons and crosswalks for the products in the Gartner Magic Quadrants and Forrester Waves on data catalogues, metadata management and data governance, linked to each vendor's own repositories, with each vendor's AI agent skills and Model Context Protocol (MCP) offer. The reports are paywalled; live connectors need a tenant and credentials, which a static site must not hold.

## Decision

content/vendors.yaml registers each report (positions taken only from vendor announcements and abstracts, labelled S, or secondary sources, labelled K), each product, its public repositories at a named commit, its MCP server, tools and skills, and a crosswalk only where a public file defines its metadata model (labelled V). A product with no published model gets no mapping, with the reason, rather than a guessed one. Each mapped product gets an add-on kit in its own extension format and a weaver model; every property without a native field goes in that extension place, so a record survives the round trip. The portal reads vendor repositories and never posts to them.

## Consequences

The connectors page and downloads/connectors/ carry twelve products, seven kits and the register. The weaver gains Collibra, OpenMetadata, DataHub, Unity Catalog, Dataplex and data.world, and writes Apache Atlas (Purview, Atlan). tests/test_vendors.py checks the register (with deliberate breaks), lossless round trips of every worked example, that people fields are never carried, and that kits and weaver agree; check_site C-25 checks the page and kits. Nine ranked vendors with no public model are listed for the weekly run. Kits are not tested against live tenants.

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
