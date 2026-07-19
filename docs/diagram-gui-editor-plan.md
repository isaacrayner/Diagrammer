# Plan — A GUI for Manipulating Diagrams (and Getting Lines to Route Around Objects)

**Status:** strategy / decision doc. No code yet. Written to answer two questions:
1. Why do connectors refuse to bend around objects on the grid, and can it be fixed?
2. Can a manipulation GUI be built on top of the *current* design, or is a different
   approach warranted — and if so, which one?

**How to read this:** Sections 1–2 diagnose the real problem (with the facts
checked, not asserted). Section 3 states the one reframe everything else follows
from. Sections 4–6 give the architecture, an honest library bake-off, and the
buy-vs-build question. Section 7 is a phased plan with *Done-when* tests, matching
the style of `azure-diagram-tool-build-plan.md`. Section 8 records where this could
still be wrong.

---

## 1. The problem, diagnosed

Two separate frustrations are tangled together. They have different causes and
different fixes, and conflating them is why this has felt intractable.

### 1a. "Lines won't curve around objects on the grid" — this is a D2 limitation, not your code

D2 has **two layout paths and you can only pick one per container**:

- **ELK layout** does proper obstacle-avoiding orthogonal routing — lines *do*
  bend around nodes — but it auto-arranges everything and will not hold the
  `actors | landing zone | production | PaaS & operations` column structure.
  Your own grid file documents this: *"ELK alone stacks it into a column."*
- **`grid-rows` / `grid-columns`** gives the aligned house-style columns, but the
  grid engine does **no path-finding at all**.

This is confirmed by D2's own documentation on grid diagrams:

> *"Because a grid structure imposes positioning outside what the layout engine
> controls, the layout engine is unable to make routes. Connections between shapes
> inside a grid are center-to-center straight segments with no path-finding."*

So this is **not tunable**. There is no D2 knob that gives you aligned columns
*and* routed edges simultaneously. `bin/optimize.py` already excludes dagre
(curved) on purpose and searches only ELK variants — meaning the moment you reach
for a grid to get the house-style columns, you leave the only routing engine the
pipeline has. You are being forced to choose alignment **or** routing. That choice
is the whole problem.

### 1b. "No way to edit except in text afterward" — this is intrinsic to D2

D2 is an **auto-layout language**: you describe structure and semantics
(`class: svc`, `-> { class: pe }`), never positions. By design there is nothing to
grab and drag — the only lever is editing text and re-rendering. A GUI wants the
opposite: **positions are the model.** This is why bolting a GUI directly onto D2
fights the grain — you would be building a position editor on top of a language
that deliberately hides positions and has almost nowhere to write a dragged
position *back* (`near`, grid membership — that is essentially the entire
vocabulary).

---

## 2. What must NOT be thrown away

The instinct to "go entirely different" is half right and half a trap. The parts
of the current design that are genuinely valuable and carry straight over:

| Asset | Why it survives any GUI |
|---|---|
| **Icon set + `icons/manifest.json`** | slug → file + aliases is already the perfect catalog to drive an icon palette/picker. Nodes render the same SVGs. |
| **`styles/azure.d2` class system** | the semantic vocabulary (`sub/rg/vnet/subnet`, `ingress/sync/pe/...`) maps 1:1 to node/edge styles in a GUI. One theme file mirrors it. |
| **`bin/lint.py` geometry gate** | overlap / crossing / aspect checks run against the GUI's *exported* SVG unchanged. |
| **`bin/contract.py` semantic gate** | still validates the semantic design. |
| **D2 as the LLM's target** | the ADS skill keeps emitting `.d2` for the first pass. |
| **The IR idea** (`azure-diagram-tool-build-plan.md` §1) | the plan already separates *"what connects to what"* (LLM) from *"where the arrow goes"* (engine). The GUI is just a **human editor for job 2**, sitting exactly where that plan always intended a layout engine to sit. |
| **Local / confidential constraint** | the SaaS portal was already rejected for volume + client confidentiality. Any GUI here must run **fully local**, nothing leaving the machine. All options below satisfy this — they are client-side/desktop, no server. |

So this is a **new front-end layer + a new position-aware model**, wrapped around
the engine and assets you already have. Not a rewrite.

---

## 3. The one reframe everything follows from

> **Obstacle-avoiding orthogonal routing is a separable, swappable component — and
> it is the actual risk. De-risk *that* before choosing any GUI framework.**

The research makes this concrete: every serious canvas library either ships an
obstacle-avoiding router or has one available:

- **JointJS** — a built-in `manhattan` router: *"the smart version of the
  orthogonal router… inserting route points when necessary while avoiding obstacles
  in its way."* First-class, mature, production-grade.
- **ELK (elkjs)** — the layered algorithm routes orthogonally **when ELK also
  places the nodes**. For **fixed** node positions (a human drag, or pinned
  columns) with obstacle avoidance you need **`libavoid`**
  (`org.eclipse.elk.alg.libavoid`, exposed as `elkjs-libavoid`), or a dedicated
  router. *(This corrects a naive "just run elkjs with `edgeRouting: ORTHOGONAL`
  and pin the columns" plan — plain layered routing is coupled to ELK's own node
  placement; the moment you hold positions you are in libavoid/manhattan
  territory.)*
- **React Flow (xyflow)** — obstacle avoidance is **not core**; it comes via an
  add-on: the WASM "avoid-nodes" edge, or `elkjs-libavoid`.
- **maxGraph / draw.io** — inherit the mature draw.io orthogonal connector router.

The strategic consequence: **do not spend a week building a GUI and only then
discover the routing still doesn't satisfy you.** Build a headless routing spike
first (Section 7, Phase 0). The router is a module you can swap; the GUI framework
is the expensive commitment.

---

## 4. Recommended architecture

A **local canvas editor** with a **position-aware scene model**, D2 as an I/O
format rather than the source of truth, and a **swappable routing module**.

```
LLM writes design.d2  ──►  import + one auto-layout pass  ──►  positioned scene (JSON)
 (ADS skill, job 1)          (ELK layered places nodes            nodes: {x,y,w,h,class,icon}
                              AND routes once)                      edges: {class, waypoints?}
                                                                         │
                                                          human edits in the GUI
                                                          (drag, re-route, add/remove,
                                                           edge-class picker, icon palette)
                                                                         │
                                        ┌────────────────────────────────┼───────────────┐
                                        ▼                                ▼                ▼
                               export SVG/PNG                   export .d2 (semantic,     run bin/lint.py
                               (into the Word pipeline)          positions as comments)   on the SVG
```

**Model.** A small position-aware JSON scene: nodes carry `x/y/w/h` + semantic
`class` + `icon` slug; edges carry `class` + optional `waypoints`. Containers
(subscription/RG/VNet/subnet) are parent nodes. This **is the IR from the existing
build plan, plus a layout layer** — not a new concept, an extension of the one you
already committed to.

**Source-of-truth rule (state this and live by it).** D2 is the **seed and
interchange format**; the JSON scene is the **truth for any diagram a human has
touched.** They *will* diverge once someone hand-places a node, because D2 has
nowhere to store pixels. Do not try to keep them losslessly in sync — that is the
single thing that would make this miserable. D2 → scene is a one-way *seed*; scene
→ D2 is a lossy *export* (semantics preserved, positions dropped to comments).

**Routing.** A single `route(nodes, edges) → waypoints` function behind an
interface, so the engine (manhattan / libavoid / avoid-nodes) can be swapped
without touching the GUI. Re-route on drag-end.

**Columns AND routing — the thing D2 can't do.** Because the GUI owns positions,
you pin containers into the four house-style columns *and* run the obstacle-avoiding
router over the fixed layout. That combination — aligned columns with edges that
bend around objects — is precisely what D2 forces you to choose between. This is
the core payoff and Phase 0 exists to prove it.

---

## 5. Library bake-off (honest, not a foregone conclusion)

| Option | Obstacle-avoiding routing | DX / fit | Cost | Verdict |
|---|---|---|---|---|
| **JointJS** | **Built-in `manhattan` router**, mature, obstacle-avoiding by default | Framework-agnostic SVG core; React wrapper is a thin layer; purpose-built for *diagram editors* | Core is MPL; the polished tooling (JointJS+) is **commercial** | **Strongest fit for the pain point** — the exact missing capability is first-class. |
| **React Flow + libavoid/avoid-nodes** | Add-on (WASM avoid-nodes / `elkjs-libavoid`) | Best React-native DX, huge ecosystem, official elkjs + `partitioning` + group-node examples | Open-source; routing add-on maturity is the risk | Best if you want a React-native codebase and are willing to own the routing integration. |
| **Embed draw.io / maxGraph** | Inherited draw.io orthogonal router (proven) | Fastest to "it works"; Azure stencils exist; runs locally (desktop or embedded) | Its file format tends to become the truth; a black box to extend | Best **buy-not-build** shortcut. See Section 6. |
| **tldraw** | Not architecture-grade arrow routing | Excellent freeform canvas SDK | OSS | Wrong tool — great whiteboard, weak structured routing. |

**Recommendation:** treat this as a real bake-off decided by Phase 0, not a
foregone React Flow choice. Going in, the two front-runners are:

1. **JointJS** if the priority is "lines route around objects, correctly, with the
   least integration work" — its manhattan router *is* the feature you are missing.
2. **React Flow + a routing add-on** if the priority is a clean, ownable,
   React-native codebase and ecosystem, accepting that you integrate the router.

Phase 0 builds the same routing spike against **both** front-runners' routers on a
**fixed-node** layout and picks the winner on output quality, not vibes.

---

## 6. The question you actually asked: is building a GUI even right?

Be honest about the alternative to building anything: **adopt draw.io as the
human-edit surface.**

- Keep D2 + the ADS skill for the LLM first pass.
- Import that into **draw.io desktop** (fully local, nothing leaves the machine —
  satisfies the confidentiality constraint that killed the SaaS portal) with an
  Azure stencil.
- Humans adjust there; draw.io's routing already bends lines around objects.
- Accept two formats and a one-way D2 → draw.io seed.

**Trade-off, stated plainly:**

- *Build (JointJS / React Flow):* weeks of work; a bespoke editor that speaks your
  icon manifest, your style classes, and your lint gate natively; the diagram is a
  first-class versioned artifact in this repo. Right **if the editor itself becomes
  a durable internal accelerator** you will keep investing in.
- *Buy (embed/desktop draw.io):* days, not weeks, to real value; you inherit a
  proven router and Azure shapes for free; but you own an import shim, live with
  format divergence, and give up native integration with the contract/lint gates.
  Right **if the goal is good diagrams, not a diagramming product.**

For a consultancy producing a handful of diagrams a year, **draw.io-embed is the
higher-ROI default** and Phase 0 should include a quick draw.io import test as a
baseline to beat. Only commit to a bespoke build if Phase 0 shows the integration
with icons/styles/lint (and the LLM round-trip) is worth the weeks.

---

## 7. Phased plan (each phase has a *Done-when*)

### Phase 0 — De-risk routing FIRST (headless, ~1–2 days)
**Goal.** Prove you can get *aligned house-style columns AND obstacle-avoiding
orthogonal edges* over a **fixed** node layout — the combination D2 refuses to give.
**Do.** Hand-build the node/container/edge set for `radical-systems-grid.d2` as
plain JSON. Feed it to (a) JointJS `manhattan` router and (b) elkjs-libavoid /
avoid-nodes, with columns pinned. Render SVG. Also import the same design into
draw.io desktop as a baseline.
**Done when.** At least one router produces columns + edges that bend around nodes,
cleanly enough to beat the current grid render on `bin/lint.py` score. Pick the
router. If none satisfies, **stop and reconsider** before building any GUI.

### Phase 1 — Read-only canvas shell
**Goal.** See a real design in the chosen framework.
**Do.** Custom Azure-icon node driven by `icons/manifest.json`; container nodes
styled from `styles/azure.d2`; load the Phase 0 positioned scene. No editing yet.
**Done when.** `radical-systems` renders in-app, visually matching the house style,
edges routed by the Phase 0 router.

### Phase 2 — Manipulation
**Goal.** Direct editing.
**Do.** Drag nodes (re-route on drag-end), edge-class picker (`ingress/sync/pe/…`),
icon palette from the manifest, add/delete nodes and edges, container membership.
**Done when.** A user repositions a node by hand and the connectors re-route around
its new position, and the manual position sticks across a re-render.

### Phase 3 — I/O + quality gate
**Goal.** Close the loop with the existing pipeline.
**Do.** D2 import (seed); SVG/PNG export; run `bin/lint.py` on the export and
surface the score; scene JSON persisted next to the `.d2` in `designs/<customer>/`.
**Done when.** LLM-generated `.d2` → import → hand-tune → export PNG lands in the
Word pipeline via the existing `<!-- IMAGE: -->` mechanism, with a lint score shown.

### Phase 4 — Fold into the ADS skill
**Goal.** The GUI becomes the human review/adjust step after the LLM's first pass.
**Done when.** The ADS flow is: skill emits `.d2` → open in editor → adjust →
export → embed, documented in the skill and README.

---

## 8. Where this could still be wrong (kept honest)

- **The router might disappoint even in Phase 0.** Manhattan/libavoid avoidance is
  good but not magic; dense Azure diagrams with many crossing private-endpoint
  edges can still look busy. Phase 0 exists precisely to find this out for ~2 days
  of cost, not weeks. If it fails, draw.io-embed (Section 6) is the fallback.
- **Scene ↔ D2 divergence is a real cost, not a footnote.** Once humans hand-place,
  the `.d2` is no longer the truth. Teams that don't internalize the one-way-seed
  rule will fight phantom "why did my layout reset" bugs. The rule in Section 4 is
  load-bearing.
- **Build effort is weeks.** For a few diagrams a year, that only pays off if the
  editor becomes a durable accelerator. If it won't, Section 6's buy path is the
  correct answer and this build plan should be shelved in its favor.
- **JointJS's best tooling is commercial**, and React Flow's routing is an add-on
  you own — neither front-runner is free-and-complete. Phase 0 must weigh licensing
  alongside output quality.

---

## 9. Immediate next step

Run **Phase 0**. It is the cheapest possible test of the entire premise: if a
fixed-node layout can get columns + obstacle-avoiding routing, the whole GUI
direction is validated; if it can't, we learn that in two days and pivot to
draw.io-embed instead of after building an editor. Everything else waits on that
result.

---

*Sources for the verified claims in this document:*

- [D2 — Grid Diagrams (grid connections do not route)](https://d2lang.com/tour/grid-diagrams/)
- [ELK — Edge Routing with Libavoid (fixed-node obstacle avoidance)](https://eclipse.dev/elk/blog/posts/2022/22-11-17-libavoid.html)
- [ELK Layered — algorithm reference](https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html)
- [elkjs-libavoid](https://github.com/MrMint/elkjs-libavoid)
- [Avoid Nodes Edge — orthogonal routing for React Flow](https://avoid-nodes-pro-example.vercel.app/)
- [React Flow — elkjs layout example](https://reactflow.dev/examples/layout/elkjs)
- [React Flow — elkjs `partitioning` for column grouping](https://github.com/xyflow/xyflow/discussions/3355)
- [JointJS — routers (manhattan avoids obstacles)](https://docs.jointjs.com/api/routers/)
- [JointJS — React Flow alternative comparison](https://www.jointjs.com/react-flow-alternative)
- [maxGraph (maintained successor to mxGraph / draw.io engine)](https://github.com/maxGraph/maxGraph)
