# Build Plan — LLM-Driven Azure Architecture Diagram Engine

**Goal:** Replace the manual Visio / hand-adjusted Draw.io workflow with a tool an LLM can drive to produce clean, professional, phase-aware Azure architecture diagrams — official service icons, neatly auto-routed arrows, one diagram per build phase — that drop straight into the ADS Word pipeline.

**How to use this document:** Work top to bottom. Each work item has a *Goal*, a *Done when* test, and an *LLM brief* (what to hand an LLM to execute it). Do them one at a time; don't start an item until the previous *Done when* passes.

---

## 1. The core idea (read this first — everything else follows from it)

The reason diagrams are hard to generate is that people conflate two jobs that should never be done by the same actor:

1. **What connects to what** — the *semantic* graph. Which services exist, which tier they sit in, what talks to what, over which protocol, encrypted or not, grouped into which subscription / VNet / subnet. **This is the LLM's job.** LLMs are good at this and terrible at pixel placement.

2. **Where the arrow physically goes** — *layout and edge routing*. Node positions, orthogonal arrow paths, avoiding crossings and overlaps. **This is a deterministic layout engine's job**, not the LLM's.

The current `generate_diagram.py` fails because it tries to do job 2 by hand (fixed grid rows, a single arrow between tier midpoints) and skips icons entirely. That is why it produces coloured boxes that need manual fixing in Draw.io.

**The whole tool is built around one artefact: an Intermediate Representation (IR).** The LLM emits a validated IR (JSON). A renderer turns the IR into a diagram using a real layout engine. Nothing else the LLM does touches geometry.

```
Discovery notes ──LLM──> IR (JSON graph) ──validator──> Renderer (layout engine) ──> SVG / PNG / .drawio
                          ▲                                    │
                          └──────────── correction loop ◄──────┘
```

Getting this separation right is 80% of the value. The rest is execution.

---

## 2. The engine decision

Three viable render paths. The recommendation is to run a short bake-off (Item 0.1) but the expected outcome is stated here so you know where you're heading.

| Path | Icons | Arrow routing | Editable after? | Fits Word embed | LLM-friendly |
|---|---|---|---|---|---|
| **D2 (ELK engine)** — *recommended primary* | `shape: image` + official Azure SVGs | ELK gives clean orthogonal routes, few crossings | No (regenerate from IR) | SVG/PNG export | Excellent (declarative text) |
| **mingrammer `diagrams` (Python + Graphviz)** | Built-in Azure icon set | Graphviz auto-route, decent, less control | No | PNG/SVG | Good (Python) |
| **Draw.io XML** — *recommended secondary* | Azure mxgraph stencils | Weak when generated; needs a layout engine feeding it | **Yes — opens in Draw.io** | Existing pipeline | Poor to hand-write |

**Recommendation:** D2 with the ELK layout engine as the primary render path (best routing + official icons + text is trivial for an LLM to emit and diff), and a `.drawio` emitter as a secondary path so you keep the "consultant tweaks it, then embeds in Word" workflow you already have. Both are fed by the *same IR*, so you are never locked in — if D2 disappoints on a specific diagram, the IR still renders via the other path.

Why not just improve the Draw.io generator? Because you'd be reimplementing a layout engine by hand. Let ELK do routing; emit Draw.io only as an *editable export*, with coordinates it computed.

---

## 3. Phase-awareness — the thing that makes this specifically yours

Your ADS work is a *migration story*: standalone IaaS three-tier → SQL PaaS + App Services + PaaS services, in stages, each building on the last. A generic diagram tool won't do this well. This is where your tool earns its keep.

**Model:** one **target-state IR** plus an ordered list of **phase deltas**. A delta is a set of operations against the previous phase:

- `add` node/edge/group
- `remove` node/edge
- `replace` node A with node B (e.g. *SQL Server on IaaS VM* → *Azure SQL Managed Instance*)
- `upgrade` node in place (e.g. *App Service Basic* → *Premium v3*, zone-redundant)

**Critical requirement — layout stability across phases.** Compute one master layout for the union of all phases, then render each phase as a *masked view* of that layout. That way the App Service in Phase 2 sits exactly where the VM it replaced sat in Phase 1. Diagrams that keep positions stable across phases read as a coherent journey; diagrams that reshuffle every phase look amateurish. This single decision is what separates your output from a whiteboard tool.

Bonus you get almost for free once deltas exist: a **phase-diff diagram** that highlights only what changed since the previous phase (added = green, removed = greyed, upgraded = badge). Consultants and customers love these.

---

## 4. The build — work items in order

### Phase 0 — De-risk and set foundations

**0.1 — Engine bake-off**
- *Goal:* Prove the routing/icon quality before committing. Build the *same* representative diagram (≈8 Azure services across 3 tiers + a VNet group + 6 labelled edges) three ways: D2/ELK, mingrammer, hand-rolled Draw.io.
- *Done when:* You have three rendered PNGs side by side and a one-paragraph verdict. Expected winner: D2/ELK.
- *LLM brief:* "Here are 8 Azure services in 3 tiers with these 6 connections. Produce (a) a D2 file using ELK layout and official Azure SVG icons, (b) a mingrammer Python script, (c) a Draw.io XML. Render all three to PNG."

**0.2 — Azure icon set + licence check**
- *Goal:* Acquire Microsoft's official Azure architecture icon set (SVG) and confirm the licence terms cover your use (Microsoft permits these icons in architecture diagrams; do not distort or recolour them; don't use them to represent your own product).
- *Done when:* Icons are on disk in a versioned folder, and a `LICENCE-NOTES.md` records the permitted-use terms and the download date/version.

**0.3 — Output contract**
- *Goal:* Decide the three outputs and their consumers: **SVG** (web/preview), **PNG at print DPI** (Word embed — match what `ads_convert.py` expects), **.drawio** (editable handoff).
- *Done when:* A one-page spec states dimensions, DPI, colour space, and file-naming (`<Customer>-Phase<N>-Architecture.<ext>`).

### Phase 1 — The Intermediate Representation

**1.1 — IR schema**
- *Goal:* A JSON Schema for the architecture graph. Minimum fields:
  - `nodes`: `id`, `service` (canonical Azure name), `label`, `tier` (frontend/middleware/backend/networking/security), `group` (subscription/RG/VNet/subnet id), `phase_introduced`.
  - `edges`: `id`, `source`, `target`, `label`, `protocol`, `direction`, `encrypted` (bool).
  - `groups`: `id`, `type` (subscription/rg/vnet/subnet/tier), `label`, `parent`.
  - `phases`: ordered list, each with a `deltas` array.
  - `meta`: customer, engagement, date, CAF/WAF anchors.
- *Done when:* Schema validates a hand-written example and rejects a deliberately broken one.

**1.2 — Validator**
- *Goal:* Catch the errors an LLM will make. Rules: no dangling edges (source/target must exist), every node in a known tier, unknown service names flagged, SPOF detector (reuse the CTP-2 "name every single point of failure" logic), and phase-continuity check (a `replace` must reference a node that exists in the prior phase).
- *Done when:* Running the validator on your 0.1 diagram passes; a mutated copy with a dangling edge and a fake service fails with clear messages.

**1.3 — Golden examples from real ADS work**
- *Goal:* Hand-encode 2–3 past ADS designs (including at least one phased IaaS→PaaS migration) as IR. This is the reality check the schema must survive.
- *Done when:* All golden IRs validate, and anything the schema *couldn't* express is written down as a schema gap to fix.

### Phase 2 — Icon resolver

**2.1 — Service→icon registry**
- *Goal:* Map canonical service names **and their aliases** to icon files. "Azure SQL Managed Instance", "SQL MI", "Managed Instance" → one icon. This is where the current tool's "just print the string" approach dies; aliasing is essential because notes are inconsistent.
- *Done when:* A lookup function resolves every service in your golden IRs to a real icon, with fuzzy/alias matching.

**2.2 — Unknown-service fallback**
- *Goal:* Never crash on an unrecognised service. Fall back to a tier-coloured labelled box **and** emit a warning so it gets fixed.
- *Done when:* Feeding a made-up service produces a labelled fallback box + a logged warning, not an error.

### Phase 3 — Single-phase renderer

**3.1 — IR → D2 emitter**
- *Goal:* Translate one phase of IR into D2: groups become containers `{}`, nodes become `shape: image` with the resolved icon, edges become `src -> dst: label`, layout set to ELK with a sensible `direction`.
- *Done when:* Your 0.1 diagram renders from IR with icons and auto-routed arrows — no manual placement.

**3.2 — Professional styling pass**
- *Goal:* Make it look like a deliverable, not a default render. Tier bands/backgrounds, consistent spacing, readable edge labels, encrypted edges styled distinctly (e.g. lock badge / line style), a title block matching your ADS branding, and a theme that survives PNG export at print DPI.
- *Done when:* A neutral reviewer, shown your output next to a Microsoft Learn reference diagram, can't immediately tell which was hand-made.

**3.3 — Render CLI**
- *Goal:* `render.py --ir design.json --phase 2 --format png` producing all three output formats per the 0.3 contract.
- *Done when:* One command turns an IR + phase number into SVG + PNG + .drawio.

### Phase 4 — Phase-aware generation

**4.1 — Delta model + phase materialiser**
- *Goal:* Apply an ordered delta list to the target state to reconstruct the concrete IR for any phase N.
- *Done when:* From one phased golden IR, you can materialise Phase 1, 2, 3 IRs and each validates independently.

**4.2 — Shared master layout (the important one)**
- *Goal:* Compute layout once over the union of all phases; render each phase as a masked subset so node positions stay fixed across phases (see §3).
- *Done when:* Rendering Phases 1→3 of a migration, a service that persists sits at the identical coordinates in every phase, and a replaced service occupies its predecessor's slot.

**4.3 — Phase-diff view**
- *Goal:* A per-phase diagram highlighting only changes vs the previous phase (added/removed/upgraded).
- *Done when:* The Phase 2 diff clearly shows the IaaS→PaaS swaps and nothing else is emphasised.

### Phase 5 — Editable Draw.io handoff

**5.1 — IR → .drawio emitter with real coordinates**
- *Goal:* Emit Draw.io using Azure mxgraph stencils, positioned with the coordinates the layout engine computed (not the old fixed grid). Preserves your "tweak in Draw.io, then embed in Word" step.
- *Done when:* The .drawio opens in Draw.io/diagrams.net with icons in sensibly routed positions and is fully editable.

### Phase 6 — The LLM interaction layer (the "tool")

**6.1 — Tool contract**
- *Goal:* Define the small, sharp set of operations the LLM calls — e.g. `emit_ir`, `validate_ir`, `apply_delta`, `render(phase)`, `diff_phases`. The LLM only ever manipulates the graph; it never positions anything.
- *Done when:* The contract is written as function specs + schemas an LLM can target.

**6.2 — Notes → IR → diagrams, with correction loop**
- *Goal:* Wire it end to end: discovery notes in, LLM drafts IR, validator runs, LLM fixes flagged issues, renderer emits the full phase set.
- *Done when:* Feeding a real Day-1 notes file yields a validated multi-phase diagram set with no manual geometry work.

**6.3 — (Optional) The web front-end**
- *Goal:* The "site" — upload notes, watch diagrams generate per phase, nudge the IR in a form, export SVG/PNG/.drawio. Only build this once 6.2 is solid; the value is in the pipeline, not the UI.
- *Done when:* You can go from uploaded notes to downloaded diagram set in a browser.

### Phase 7 — Fold back into the ADS skill

**7.1 — Replace Step 3 of the ADS skill**
- *Goal:* Swap `generate_diagram.py` for the new renderer. The skill now emits an IR and calls `render` for every phase.
- *Done when:* An ADS run produces per-phase diagrams automatically.

**7.2 — Auto-embed into the docx pipeline**
- *Goal:* Batch-generate phase PNGs and feed them to `ads_convert.py` via the existing `<!-- IMAGE: ... -->` mechanism, so the architecture diagrams land in the Word document without the manual "export from Draw.io and paste" step noted in the current skill.
- *Done when:* The Word output contains the phase diagrams with no manual export step.

**7.3 — Golden regression set**
- *Goal:* Keep the golden IRs as a regression suite; re-render on every change and eyeball for layout regressions.
- *Done when:* A `make regen` (or equivalent) reproduces all golden diagrams for comparison.

---

## 5. Build-vs-buy (be honest with yourself before Phase 1)

Off-the-shelf AI Azure-diagram generators already exist (text/whiteboard → official-icon Draw.io, cost overlays, etc.). Spend an hour trying one or two before you build. But they almost certainly **won't** give you: the phased delta model with stable cross-phase layout, an IR you control, or native integration into your ADS skill and Word pipeline. Those three are the actual product here. If a tool gets you 70% and exposes an API/IR you can drive, wrap it instead of rebuilding the renderer — but keep your own IR as the source of truth either way, so you're never locked in.

---

## 6. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Icon licence misuse | Legal / rebrand | 0.2 licence note; never recolour/distort; not for your own-product branding |
| ELK routing disappoints on dense diagrams | Ugly output | Bake-off (0.1); .drawio fallback for manual fix; try TALA only if you'll pay for it |
| LLM invents non-existent Azure services | Wrong diagram | Validator (1.2) + icon resolver warnings (2.2) |
| Cross-phase layout drift | Looks amateur | Shared master layout (4.2) — treat as non-negotiable |
| Scope creep into the web UI too early | Stall | UI is Phase 6.3, after the pipeline works headless |

---

## 7. Start here (first three moves)

1. **Item 0.1** — run the three-way bake-off. One afternoon; it decides your engine.
2. **Item 0.2** — pull the Azure icon set and write the licence note.
3. **Item 1.1 + 1.3** — draft the IR schema and immediately stress it against 2–3 real past designs. If the schema survives your real work, the rest is execution.

Everything after that is turning the crank one work item at a time.
