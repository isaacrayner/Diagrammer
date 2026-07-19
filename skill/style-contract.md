# style-contract.md — the rules every diagram must follow

Authoritative rules for turning a design into D2. Grounded in Microsoft's
Well-Architected Framework diagramming guidance (see
`../docs/azure-diagram-guidelines.md` for the sourced list). The LLM must not
deviate.

**These rules are machine-checked.** Run `python bin/contract.py <file>.d2`
before you consider a diagram finished; it reports the rule ID and the Microsoft
guideline behind every failure. Errors must be fixed, warnings justified.

| Rule | Checks | Level |
|---|---|---|
| `R2-undirected` | no bare `--` lines | error |
| `R3-inline-style` | no inline `style:` — classes only | error |
| `R4-unknown-class` | only classes defined in `styles/azure.d2` | error |
| `R5-icon-path` / `R5-icon-missing` | icons are `./icons/<slug>.svg` and exist | error |
| `R6-svc-no-icon` / `R6-svc-no-label` | every service has an official icon and a name | error / warn |
| `R8-no-legend` / `R8-legend-incomplete` | the legend has an entry for **every** flow class used | error |
| `R10-paas-in-subnet` | PaaS-over-private-endpoint is not inside a subnet | error |
| `R12-no-style-import` | the shared style file is imported | error |
| `R13-no-type` / `-bad-type` / `-layer-mismatch` | declared diagram type, and content appropriate to that layer | error |
| `R13-layer-thin` | the diagram is thin for its declared type | warn |
| `R14-markdown-block` | no `\|md\|` blocks — they do not rasterise to PNG | error |

**Retired 19 July 2026** (deliberately not enforced): `R1` bidirectional arrows,
`R7` metadata block, `R9` unlabelled connections, `R11` node/subnet density.
Bidirectional arrows are used on purpose for genuinely two-way relationships such
as VNet peering; the metadata block is still in every template and still
recommended, just not enforced. `bin/verify.py` asserts these stay retired so
they cannot creep back in.

## 1. Containment — which class wraps which layer

Nest strictly, outer → inner. Never skip a level that exists in the design.

| Element | Class | Rendered as |
|---|---|---|
| Subscription | `sub` | slate border, light grey-blue fill |
| Resource group | `rg` | **dashed** Azure-blue border (colour + pattern) |
| Virtual network | `vnet` | solid blue border, light-blue fill |
| Subnet | `subnet` | light grey border, near-white fill |
| Service (leaf) | `svc` | the node **is** the official Azure icon |

Label format: `SUBSCRIPTION · <name>`, `RG · <name>`, `<vnet-name> <CIDR>`,
`<subnet-name> <CIDR>`. Use a middle dot `·` as the separator, Title Case for
proper names.

## 2. What goes inside a subnet — and what does not

Inside a `subnet`: only things that genuinely occupy IP space — VMs, VM scale
sets, Application Gateway, Azure Bastion, Azure Firewall, VNet-integrated or
delegated-subnet services (e.g. SQL Managed Instance), and private endpoints.

**Outside the VNet** (as standalone `svc` nodes): PaaS services accessed over a
private endpoint — Storage, Key Vault, Azure SQL Database, Cosmos DB, Service
Bus, Event Hubs, etc. Connect them with a `pe` connection. Drawing them inside a
subnet is inaccurate and is not allowed (WAF: *be accurate*).

## 3. Connection semantics — the house flow vocabulary

Reverse-engineered from the Mitie and RADical reference diagrams so generated
output reads the way the hand-made set does.

| Class | Meaning | Style | Typical use |
|---|---|---|---|
| `ingress` | user / app inflow | blue solid | users → Front Door → App Gateway → app |
| `sync` | internal service-to-service call | slate solid | app → SQL MI, app → cache |
| `devops` | DevOps and CI/CD | orange solid | Pipelines → ACR, Engineers → Boards |
| `egress` | crosses the internet boundary | red solid | NAT Gateway / Firewall → external services |
| `pe` | private endpoint | blue dashed | app → Key Vault, app → Storage |
| `peering` | VNet peering | slate dash-dot | hub ↔ spoke |
| `replication` | data replication | green dashed | SQL geo-replication, ASR |
| `mgmt` | management, backup, diagnostics | purple dashed | app → Monitor, VM → Backup |

Plus one state class:

| Class | Meaning | Style |
|---|---|---|
| `future` | deferred to a later phase, or DR standby | grey, dashed, muted text |

Rules:

- **Direction.** Arrows point from the caller to the dependency. Bidirectional
  `<->` is allowed only where the relationship genuinely is two-way — VNet
  peering, read/write to profile storage — not as a shortcut for "they talk".
- **One meaning per class.** Do not reuse `egress` red for an internal flow
  because it needs to stand out. If you need a new meaning, add a class to
  `styles/azure.d2` and to the legend, not an inline style.
- **The legend must list every class the diagram uses.** This is checked
  (`R8-legend-incomplete`), because a colour vocabulary nobody can decode is
  worse than no vocabulary. Delete unused entries from the template legend.
- **Grey is never bare.** If anything uses `future`, the legend says what grey
  means. This is the one thing to fix from the reference diagrams, which greyed
  out deferred items with no key.

## 4. Metadata (expected on every diagram)

The title block carries: customer, diagram scope (Target-State or Phase N),
revision, date, author. This is the WAF *include metadata* rule. It is no longer
machine-enforced, but every template ships with one — keep it. Keep the `.d2` in
version control alongside the ADS document.

## 5. Consistency

Like elements look alike: same icon size (via `svc`), same border styles per
layer (via the classes), same casing, same arrowheads. Never restyle one node to
stand out — if emphasis is needed, that's a separate concern, not an ad-hoc
colour change.

## 6. Accessibility

Every layer is distinguished by **colour and pattern**, never colour alone
(resource groups are dashed for this reason). Keep labels high-contrast. Do not
introduce new fills that reduce contrast against black text.

## 7. Layer, don't overload — declare the diagram type

Every `.d2` starts with a type declaration on line 2:

```d2
...@../../styles/azure.d2
# diagram-type: component
```

| Type | Answers | Must not contain | Must contain |
|---|---|---|---|
| `context` | who uses the workload and what it touches | VNets, subnets | external actors |
| `container` | hosting models and macro structure | subnets | — |
| `component` | which named Azure services, where | — | `svc` nodes with official icons |
| `network` | connectivity | — | CIDRs; usually peering and/or egress |
| `resilience` | what survives what | — | RPO/RTO on the recovery path |
| `identity` | who authenticates how | — | usually the Entra tenant |

`component` is the usual ADS deliverable. The type is checked (`R13`), so a
context diagram cannot quietly grow subnets. There is no node-count limit: if a
comprehensive component diagram is the right answer for the engagement, draw it.
Split by **phase** and by **type**, not by size.

## 7b. Layout — use the grid, not the layout engine's instincts

The house style is a **four-column grid**, reverse-engineered from the Mitie and
RADical Visio diagrams:

```
actors | landing zone | production | PaaS & operations
```

Set `grid-columns: 4` at the root, then a grid inside each container:

- subnets are **full-width horizontal bands** inside the VNet (`grid-rows: N`),
  each band holding a row of instances (`grid-columns: N`);
- resource groups holding a VNet plus loose resources go `grid-columns: 2` so the
  column does not become a tall thin strip;
- draw the actual instances (`AVD SH 01–04`, `Hub 01–03`, `DB 01–03`) rather than
  one icon captioned "VMs". It matches the reference and it fills the bands
  horizontally, which is what keeps the diagram landscape.

**Why this matters:** left to itself ELK stacks everything into one tall column.
The RADical target-state diagram went from 1483×3679 (portrait, 0.4 aspect) to
3941×2310 (landscape, 1.7) purely by imposing the grid — the same aspect as the
hand-drawn original.

**The trade-off, and it is binary.** Tested exhaustively on the RADical design,
19 July 2026:

| Mode | Alignment | Connectors | Aspect |
|---|---|---|---|
| `grid-*` anywhere in the file | columns and bands, as drawn by hand | **straight diagonals across everything** | landscape 1.7 |
| no grid directives at all | ELK's own arrangement | **orthogonal, routed around containers** | portrait 0.57 |

**A single grid directive anywhere switches D2 to straight-line connectors for
the whole diagram.** It is not per-container. Confirmed by stripping the root
grid but keeping grids inside subnets only: connectors stayed diagonal. Removing
every `grid-` line restored right-angle routing immediately.

Things that were tried and did **not** get both: `direction: right` at root
(ELK ignores it and still stacks, 1974×4942); grids on leaf containers only;
re-ordering bands so endpoints sit adjacent; fanning private-endpoint traffic
through the PE subnet. That last one is worth keeping anyway on accuracy grounds
— see below — but it did not fix routing.

So pick per diagram, and say which you picked:

- **Orthogonal** (`designs/radical-systems/radical-systems.d2`) when the diagram
  will be read closely and line paths matter. This matches the house style's
  routing.
- **Grid** (`…-grid.d2`) when the diagram is a one-page overview and alignment
  matters more than routing.

Getting both requires a human routing the lines — which is what Visio was doing.

Because diagonals cross more often, `lint.py` scores grid layouts lower than the
same content under ELK. **The scores are not comparable across layout modes.**

**Worth keeping regardless of mode:** draw the private endpoints as nodes in the
PE subnet (a private endpoint genuinely is a NIC in that subnet) and run one
Private Link edge out to the PaaS group, rather than five long edges from three
different subnets straight to the services. More accurate and fewer crossings.

## 8. Naming and IDs

- Node IDs: short, lowercase, stable (`app`, `sql`, `kv`, `agw`, `func`).
- Across phases, **reuse IDs** for services that persist so positions stay put.
- Display labels: the official service name in Title Case (`App Service`,
  `SQL Managed Instance`, `Key Vault`).

## 10. Diagram chrome

The title block and legend are not decoration; they are guideline requirements
(*include metadata*, *provide a legend*). Use the `titleblock` and `legend`
classes — do not style them inline. Both are already in
`templates/target-state.d2` and `templates/phase.d2`, so start from a template.

## 11. Never

- inline `style:` on nodes or containers — classes only
- PaaS-over-private-endpoint inside a subnet
- a flow class that isn't in the legend
- grey (`future`) with no legend entry explaining it
- recoloured, stretched, or substituted icons
- an icon that doesn't represent the thing it labels (the reference set used the
  Entra ID icon for domain controllers — use `entradomain` for those)
- mixing diagram types in one file
