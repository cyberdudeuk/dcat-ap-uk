# ADR 0023: Record the sharing agreement with DCAT's own qualified relation, and add a sharing method only where nothing exists

Status: Proposed

## Context

Change request #34 asks for two things on datasets and data services: a link to the agreement the data is shared under, and every method by which it moves. Checked on 22 November 2026. (1) The Digital Economy Act register of information sharing agreements lists 667 agreements; an agreement's page has one field for its information sharing method, holding one value (three pages checked). Agreements 205, 284 and 663 (Warm Home Discount helpline) record trusted partner transfer, encrypted hardware and secure file transfer, yet each says electronic access to DWP's Citizen Application Programming Interface (CAPI) will also be enabled, so methods counted from that field undercount API use. The issue's further counts (194 active, 11 using API, 6 of them active) were not re-counted. (2) DCAT 3 already has a way to link a resource to another with a stated role: dcat:qualifiedRelation to a dcat:Relationship holding dct:relation and dcat:hadRole. The profile has it on Dataset only, and binds hadRole to the agent-role codelist, whose values are people's responsibilities, not kinds of relation. (3) Nothing in DCAT, DCAT-AP or the profile records how data moves between organisations. The profile's transferMechanism is a different thing: the legal mechanism for sending personal data outside the UK.

## Decision

Proposed: (a) the agreement link uses dcat:qualifiedRelation, extended to DataService, with a new relation-role codelist bound to hadRole on Relationship (agent-role stays bound on Attribution); its first value is sharing-agreement, and the target is the IRI of the agreement's register entry. No new property for it. (b) A new optional property, dcat-ap-uk:sharingMethod (0..n) on Dataset and DataService, takes concepts from a new sharing-method codelist whose first nine values are the register's own labels. Where a method is API, the record also links the API through accessService. (c) Both are optional, so this is a minor change: every record that conforms today still conforms.

## Consequences

Rejected: two new UK properties as first drafted in #34 (a new property for the agreement duplicates what DCAT 3 already carries, so other DCAT readers would not see the link); dct:relation alone (any reader sees a related resource but not that it is the agreement); reusing transferMechanism (it carries a legal basis, not a technical method). Costs: hadRole needs its codelist chosen by class, so the builder, validators and SHACL must look the codelist up per class, with a test; the sharing-method codelist must stay in step with the register's values, compared at each review (minutes, not hours). Until the owner decides, nothing in the profile changes; O-30 tracks the decision. Goes to the Metadata Implementation Working Group as a minor change if accepted.

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
