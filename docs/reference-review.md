# Reference diagram review — house style vs Microsoft's guidance

Reviewed 19 July 2026 against `azure-diagram-guidelines.md`.
Subjects: all seven diagrams in `examples/reference/` — the Mitie set (Phase 1,
Phase 2 v1 and v2, Phase 3) and the RADical set (Phase 1, DR, and the text-block
HLD).

> **Decisions taken after this review** (19 July 2026). Rules `R1` bidirectional,
> `R7` metadata, `R9` unlabelled edges and `R11` density were **retired** — the
> house style uses bidirectional arrows deliberately and comprehensive diagrams
> are wanted. In their place the flow vocabulary below became a first-class part
> of the style system, the legend rule was **strengthened** to require an entry
> per class used, and layering is now enforced by a declared diagram type (`R13`)
> rather than a node count. See `../skill/style-contract.md`.

Verdict: **the Visio-family diagrams are close to compliant and are the right
model for the generator.** Most of the gaps are things a deterministic linter can
prevent, which is why they are now rules in `bin/contract.py` rather than advice.

## Where your work already matches the guidance

| Guideline | Evidence |
|---|---|
| Official icons and service names | The Mitie and RADical Phase-1 diagrams use the official Azure set throughout, unmodified, with the product name beside each icon |
| Be accurate | Private endpoints get their own PE subnet; the ACA environment is marked as a delegated `/23`; SQL DBs are shown behind a Private Endpoint rather than dropped inside the app subnet |
| Standard notation for containment | Subscription → resource group (with the RG badge) → VNet → subnet, dashed RG borders, CIDRs on every subnet. This is exactly the layering `styles/azure.d2` reproduces |
| Label lines where it matters | Ports and protocols are called out: `443`, `ODBC TCP 2638`, `SMB 445 (FSLogix)`, `AVD PaaS Routing`, `VNet Peering` |
| Layer by phase | One diagram per phase, and positions are broadly stable between Phase 1 and Phase 3 — the hub stays left, production VNet right. This is the cross-phase stability the build plan calls non-negotiable, and you were already doing it by hand |
| Resilience annotation | RPO/RTO, zone redundancy, and ASR warm-standby notes on the DR diagram match the WAF "availability and resilience map" type |

## Continuity across the set — the flow vocabulary you were already using

Reading all seven together, the colour semantics are more consistent than any one
diagram suggests. This is the vocabulary that has been lifted into
`styles/azure.d2` so generated output matches the hand-made set:

| Treatment | Meaning in your diagrams | Now |
|---|---|---|
| Blue solid | user and app inflow — Operators → Front Door → AVD control plane → host pool; internal app tiers | `ingress` |
| Orange solid | DevOps and CI/CD — Engineers ↔ Boards, Pipelines → Container Registry, Devs → pipelines | `devops` |
| Red solid | crossing the internet boundary — NAT Gateway → External Services, IFS PSO FTP, and the inbound 443 path to the AVD hosts | `egress` |
| Black dash-dot | VNet peering, consistently across all Mitie phases and RADical | `peering` |
| Green dashed | SQL geo-replication (Phase 3) | `replication` |
| Thin black solid | ASR and storage replication (DR diagram) | `replication` |
| Greyed icons | deferred phase work and DR standby hosts | `future` |

Two continuity notes worth keeping in mind:

- **Positions are stable across phases**, which is the single hardest thing to do
  by hand and you were already doing it: the hub sits left, production right, and
  Phase 1 → Phase 3 keeps AVD, App, Database, and Private Endpoint subnets in the
  same vertical order. The `phase.d2` template's stable-ID rule preserves this.
- **Red is used in both directions.** In RADical it is outbound egress; in Mitie
  it also carries the inbound 443 path. The `egress` class is therefore defined
  as "crosses the internet boundary", either direction, which matches how you
  actually use it.

## Gaps, and what now enforces each

| # | Gap | Seen in | Enforced by |
|---|---|---|---|
| 1 | **Bidirectional arrows** — double-headed connectors for host-pool ↔ profile storage, VNet peering, Front Door ↔ WAF, FTP ↔ external services | Mitie all phases, RADical Phase 1 | **Not enforced.** Retired: these are genuinely two-way. The style contract asks only that `<->` means a real two-way relationship |
| 2 | **No legend** despite four distinct line treatments (blue solid, black dash-dot, red solid, green dashed) carrying different meanings | Mitie set | `R8-no-legend` **and** `R8-legend-incomplete` (errors) — the legend must name every class in use. This is the single biggest improvement over the reference set |
| 3 | **No metadata block** — no title, revision, date, or author on the Visio diagrams | Mitie set, RADical Phase 1 | **Not enforced.** Retired; the title block ships in both templates and remains recommended |
| 4 | **Colour-only encoding** — the RADical HLD separates tiers by fill colour alone (yellow / teal / green / orange / purple / pink) with no pattern pairing | RADical HLD | Structural: `styles/azure.d2` pairs every layer with a border pattern (RG dashed), and `R3-inline-style` blocks ad-hoc fills |
| 5 | **No icons at all** — the RADical HLD is entirely text blocks, so it fails "use official icons and service names" as a component-level deliverable. It is a fine *block/functional* diagram; it should not be the only architecture view | RADical HLD | `R6-svc-no-icon` (error) |
| 6 | **Overloading** — the RADical HLD carries topology, cost notes, phase deferrals, and licensing in one canvas; the Mitie Phase 3 diagram carries prod, DR, identity, DevOps, and management together | Both | `R13` declared diagram type. No node-count limit: a comprehensive component diagram is allowed, but a context diagram cannot grow subnets, and DR detail belongs in a `resilience` view |
| 7 | **Greyed-out future elements** mixed into a current-state view (deferred firewall subnet, Maximo hosts) with no key explaining what grey means | Mitie, RADical | The `future` class plus `R8-legend-incomplete` — grey is now a declared class and the legend must explain it |
| 8 | **Unlabelled connectors** — several plain dash-dot lines carry no label | Mitie set | **Not enforced.** Retired; the flow colour now carries the meaning a label used to |
| 9 | **Icon/thing mismatch** — "Entra DC01 / DC02" domain controllers drawn with the Entra ID icon | Mitie set | `entradomain` is now a distinct slug and `icon-index.md` calls this case out; the rest is a judgement call for `skill/critic.md` |

## What this means in practice

The generator should aim at the **Mitie Visio style**, plus the two things that
set is missing: a title block and a complete legend for the colour vocabulary you
were already using implicitly. That is precisely what
`templates/target-state.d2` and `templates/phase.d2` now produce by default, so a
compliant diagram is the path of least resistance.

The RADical text-block HLD stays useful as a **block/functional diagram** early in
an engagement, but it should be paired with an icon-based component diagram
rather than shipped alone.

Two items remain human judgement and belong to the critic agent, not the linter:
whether a service is in the right subnet, and whether the chosen icon actually
represents the thing it is labelled as.
