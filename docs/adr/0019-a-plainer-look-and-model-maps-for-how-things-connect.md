# ADR 0019: A plainer look, and model maps for how things connect

Status: Accepted

## Context

The portal was rich but busy: a dark masthead with many controls, boxed and coloured headings, bordered cards, loud change flags and long tables on every class page. Readers who are not technical found it harder to use than the xGov MEM site, whose plain pages, left navigation and one diagram per class are easy to follow. The owner asked for that simplicity, every feature kept, and a friendlier way to see how parts of the model connect, after the MEM class diagrams and the Morgan Map pattern.

## Decision

Keep the architecture, every page, tool, check and pattern (drawer, tabs, change flags, glossary, display options), and change the look: a white masthead with search up front, quiet navigation, plain headings, light cards and tables, quieter flags that still say New and Updated. Show how classes connect as model maps after Morgan Maps: cards with a type chip, curved links named by the property that makes them, and a details panel with the card's facts and connections. Class pages follow the MEM order: the map first, then the properties as plain tables by obligation, then the detail. The links come from the profile data, plus the structural links DCAT expresses as IRIs, so the maps cannot drift from the model.

## Consequences

Every map works without JavaScript (each card is a link and a list repeats every link), carries no inline style (the CSP holds), and is checked: tests/test_integrations.py requires a card for every class a class links to and well-formed panel data, and tools/check_browser.py requires that selecting a card opens its details and Escape closes them, with a deliberate break (map). Busy maps show line labels for the card being looked at. Contrast is checked in light and dark on every page, as before. The old UML-style class diagram is replaced; the property tables carry the same facts as text.

<!-- Generated from content/portal.yaml by tools/build.py. Edit there. -->
