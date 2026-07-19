# Azure diagram guidelines — the source of the contract

Everything `bin/contract.py` enforces traces back to two Microsoft pages.
Checked 19 July 2026.

- **Architecture design diagrams** (Well-Architected Framework, architect role) —
  https://learn.microsoft.com/en-us/azure/well-architected/architect-role/design-diagrams
- **Azure architecture icons** (download + terms) —
  https://learn.microsoft.com/en-us/azure/architecture/icons/

## The diagramming practices, verbatim in substance

| # | Guideline | What it means for us |
|---|---|---|
| 1 | **Use standard notations** | Only the classes in `styles/azure.d2`; no bespoke shapes |
| 2 | **Avoid ambiguous lines** | Two line meanings only: `sync` (solid) and `pe` (dashed) |
| 3 | **Use directional arrows** | Every relationship is `->`; never a bare line |
| 4 | **Avoid bidirectional arrows** | Two single-ended arrows, client → dependency; never `<->` |
| 5 | **Label everything clearly** | Every icon, container, and non-obvious line gets a label |
| 6 | **Maintain consistency** | One taxonomy across the whole set: same colours, casing, icon sizes, line weights, arrowheads, borders |
| 7 | **Be accurate** | Do not draw a PaaS service inside a subnet if it is reached over a private endpoint. Retire diagrams that no longer answer a live question |
| 8 | **Include metadata** | Title, description, last-updated date, author, version, references |
| 9 | **Use official icons and service names** | Latest official set; no stretching or recolouring; no vendor logos for generic blocks |
| 10 | **Provide a legend** | Required as soon as line or border semantics are introduced |
| 11 | **Design for accessibility** | Sufficient contrast; pair colour with pattern, never colour alone |
| 12 | **Layer, don't overload** | Progressive disclosure: context → container → component/sequence |
| 13 | **Version control** | Diagram sources live with the workload's other versioned assets |

## Icon terms (the download page)

**Do:** use icons to show how products work together; put the product name near
the icon; use icons as they appear in Azure.

**Don't:** crop, flip, rotate, distort, or change icon shape; use Microsoft
product icons to represent your own product or service.

Permitted use is architectural diagrams, training materials, and documentation.
Microsoft reserves all other rights. See `LICENCE-NOTES.md`.

## Icon set version

The vendored set is **Azure_Public_Service_Icons_V24** (July 2026 update: Azure
DocumentDB, Azure Resiliency, AI Gateway, DDoS custom policies, and new Microsoft
Foundry icons), plus the **Microsoft Entra architecture icons** (October 2023)
which carry the Entra ID tenant icon the Azure set does not include.

Microsoft ships icon updates every few months; re-run the refresh in
`LICENCE-NOTES.md` a couple of times a year.

## Diagram types worth knowing

The WAF page lists the types an architect layers across an engagement. The three
that matter most for an ADS deliverable:

- **Context diagram** — the workload as a black box plus external actors. Use
  generic shapes for external systems, not product logos, and draw an explicit
  boundary.
- **High-level system / container diagram** — the macro structure and hosting
  models. This is what an ADS target-state diagram usually is.
- **Component diagram** — generic blocks replaced with named technologies; the
  visual bill of materials.

Also high value for our work: **network connectivity** (referenced later in
security audits and incident response), **availability and resilience map**
(RPO/RTO annotations for DR phases), and **identity and access flow**.
