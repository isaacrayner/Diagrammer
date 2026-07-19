# Azure Architecture Diagrammer

A local, free toolkit that turns a text description of an Azure design into a
professional architecture diagram — official Azure icons, subscription →
resource-group → VNet → subnet layering, orthogonal routing — and exports PNG/SVG
for embedding in documents. No subscription, no API key, no server, nothing
leaves the machine.

It is driven by an LLM (your Claude desktop ADS skill) that writes the diagram as
**D2 text**; deterministic tools handle layout, rendering, and quality control.

---

## How it works (the pipeline)

```
ADS notes ──▶ LLM writes design.d2 ──▶ optimize.py ──▶ design.png / design.svg ──▶ embedded in the Word doc
              (follows skill/ rules)     (D2+ELK render,
                                          lint-scored best layout)
```

The `.d2` text is the source of truth — versionable, diffable, stored next to the
ADS document. The LLM only ever writes that text; it never places anything by
pixel. Layout, icon placement, and connector routing are done by D2 + the ELK
engine; quality is checked by a geometry linter.

---

## Prerequisites

| Tool | Purpose | Notes |
|---|---|---|
| **d2** | render `.d2` → SVG | single binary |
| **resvg** (or `rsvg-convert`) | SVG → PNG for Word | single binary; only the PNG step needs it |
| **python3** | contract, lint, optimize, icon manifest | 3.9+, stdlib only |

### Windows install

```powershell
cd C:\Code\Diagrammer
.\setup.ps1
```

That installs d2 via winget (falling back to scoop), gets resvg via cargo or, if
you have no Rust toolchain, downloads the prebuilt binary into `.\tools\` (which
the render scripts add to `PATH` themselves), rebuilds the icon set, and renders
a smoke-test diagram.

If you would rather do it by hand, or `setup.ps1` reports a missing package
manager:

```powershell
# 1. d2 — pick one   (note the capitalisation: winget -e ids are case-sensitive)
winget install --id Terrastruct.D2 -e  # easiest
scoop install d2                       # if you use scoop
# or download d2-vX.X.X-windows-amd64.msi from
#    https://github.com/terrastruct/d2/releases  and run it

# 2. rasterizer — pick one
cargo install resvg                    # needs Rust; https://rustup.rs
# or download resvg-win64.zip from
#    https://github.com/linebender/resvg/releases
#    and put resvg.exe somewhere on PATH, e.g. C:\Tools

# 3. confirm both are visible to a NEW shell
d2 --version
resvg --version

# 4. build the icon set and check the repo
python bin\build_manifest.py
python bin\verify.py
```

Two Windows gotchas: `winget` and `cargo` only update `PATH` for **new**
terminals, so open a fresh PowerShell before running `d2 --version`; and if the
MSI is blocked by policy, the plain `.exe` from the release page dropped into a
folder on `PATH` works just as well.

### macOS / Linux

```bash
./setup.sh          # installs d2, points you at a rasterizer, builds icons
```

Everything is a single binary or stdlib Python, so it runs identically on any
machine after a `git clone`.

---

## Repository structure

```
Diagrammer/
├── README.md                 ← this file
├── LICENCE-NOTES.md          Azure icon set: source, permitted use, refresh steps
├── setup.ps1 / setup.sh      install d2 + rasterizer, build icons, smoke test
├── bin/
│   ├── contract.py           enforces the Microsoft diagramming guidelines on .d2 source
│   ├── render.py             design.d2 → design.svg + design.png (single ELK render)
│   ├── render.sh             POSIX wrapper around render.py
│   ├── optimize.py           renders layout variants, keeps the best-scoring
│   ├── lint.py               deterministic geometry checks + score (0–100)
│   ├── build_manifest.py     official Azure SVGs → icons/<slug>.svg + manifest.json
│   └── verify.py             repository self-check (structure, icons, contract)
├── styles/
│   └── azure.d2              THE colour/layer system — import with ...@<path>/styles/azure.d2
├── icons/
│   ├── <category>/           the official Microsoft set, as downloaded
│   ├── <slug>.svg            flat copies the .d2 files reference  [generated]
│   └── manifest.json         slug → file + aliases + provenance   [generated]
├── templates/
│   ├── target-state.d2       starter skeleton (metadata title block + legend)
│   └── phase.d2              starter skeleton for one migration phase
├── skill/                    LLM instructions the ADS skill reads
│   ├── PROMPT.md             ADS notes → .d2 generation rules
│   ├── style-contract.md     which class wraps which layer; line semantics
│   ├── icon-index.md         canonical service → slug vocabulary
│   └── critic.md             optional review-agent prompt
├── examples/
│   ├── azure-d2-*.d2/.png    rendered demos of the layer system
│   └── reference/            hand-made house-style diagrams (Mitie, RADical)
├── docs/
│   ├── azure-diagram-guidelines.md   the sourced Microsoft rules the contract enforces
│   ├── reference-review.md           your house style audited against those rules
│   └── azure-diagram*-plan.md        the build plans this repo implements
├── evals/
│   └── bad-diagram.d2        fixture that must fail every contract rule
└── designs/<customer>/       per-engagement .d2 + rendered output + phases/
    └── _example/example.d2   worked reference design
```

### Two D2 traps, both handled for you

**1. Path resolution.** D2 resolves `import` relative to the **working
directory** but `icon:` relative to the **file**. Those only agree in one place,
so the render scripts run `d2` from the design's own directory and materialise a
temporary sibling with icon paths rewritten (`bin/d2paths.py`). What that means
when authoring:

- icons are always `icon: ./icons/<slug>.svg`, wherever the design lives;
- the style import is depth-relative — `...@../../styles/azure.d2` from
  `designs/<customer>/`, `...@../../../styles/azure.d2` from `.../phases/`.

The `.d2` you author and commit keeps the clean form; nothing is rewritten in
version control.

**2. Markdown does not reach the PNG.** D2 renders `|md|` blocks as an HTML
`<foreignObject>`, and resvg cannot rasterise those. A markdown title therefore
survives in the SVG and silently vanishes from the PNG that goes into the Word
document. Use a quoted text label with `\n` and the `titleblock` class instead.
This is enforced (`R14-markdown-block`) and checked end-to-end by
`bin/verify.py`.

---

## Integrating with the Claude desktop ADS skill

The diagrammer is a toolkit the ADS skill **invokes** — the same way the skill
already shells out to `ads_convert.py`. There is no server and no API; the skill
writes a `.d2` file and runs a script.

### Where it lives (pick one)

- **Bundled (recommended).** Copy the diagrammer into the ADS skill's folder
  (e.g. `ads/diagrammer/`). The skill is then self-contained and paths always
  resolve wherever it runs. Develop the diagrammer as its own git repo, and sync
  `bin/`, `icons/`, `styles/`, `templates/`, `skill/` into the ADS skill when you
  cut a new version.
- **Referenced.** Keep it as a sibling repo and point the skill at it with an
  environment variable (`DIAGRAMMER_HOME`) or a known clone path. More separation,
  but the repo must exist on every machine the skill runs on.

### The contract (what the ADS skill does at the diagram step)

This replaces the old `generate_diagram.py` box-XML step:

1. **Read the rules** — `skill/PROMPT.md`, `skill/style-contract.md`,
   `skill/icon-index.md`.
2. **Write the design** — emit `designs/<customer>/<customer>.d2`:
   - first line `...@styles/azure.d2` to inherit the palette,
   - structure as `subscription → resource group → VNet → subnet`,
   - each service is `{ class: svc; icon: ./icons/<name>.svg }` from the icon index,
   - connections use `{ class: sync }` (HTTPS) or `{ class: pe }` (private endpoint),
   - include the metadata title block and legend from `templates/target-state.d2`.
3. **Render + quality-gate** — run
   `python bin/optimize.py designs/<customer>/<customer>.d2`
   (or `bin/render.sh <file>` for a plain ELK render). This produces
   `<customer>.svg` and `<customer>.png`.
4. **Embed** — insert the PNG into the Word document through the existing
   `<!-- IMAGE: <customer>.png 100 center -->` mechanism in `ads_convert.py`.
5. **Phases** — repeat steps 2–4 per phase file in `designs/<customer>/phases/`.

### Skill-side snippet to drop into the ADS `SKILL.md`

> **Step 3 — Generate the architecture diagram.**
> Read `diagrammer/skill/PROMPT.md`, `style-contract.md`, and `icon-index.md`.
> Write the design to `diagrammer/designs/[Customer]/[Customer].d2` following
> those rules, then run
> `python diagrammer/bin/optimize.py diagrammer/designs/[Customer]/[Customer].d2`.
> Embed the resulting `[Customer].png` with an `<!-- IMAGE: -->` directive.

Because the LLM only writes text and the tools are deterministic, the same notes
produce the same diagram on any machine, and the `.d2` is version-controlled
alongside the ADS document — satisfying Microsoft's WAF guidance to store diagram
sources with the workload's other assets.

---

## Usage (standalone, without the skill)

Run everything from the repository root.

```bash
# one-off: build icons/<slug>.svg + manifest.json from the vendored official set
python bin/build_manifest.py

# enforce the Microsoft diagramming guidelines on the source (do this first)
python bin/contract.py designs/_example/example.d2
python bin/contract.py --all

# render + auto-select the best layout, with quality report
python bin/optimize.py designs/_example/example.d2

# single plain render
python bin/render.py designs/_example/example.d2

# just check quality of an already-rendered SVG
python bin/lint.py designs/_example/example.svg
```

`lint.py` scores a diagram 0–100 and flags label-on-icon overlaps, edge-label
overlaps, connector crossings, partial node overlaps, and bad aspect ratio.
`optimize.py` renders ELK layout variants (orthogonal only — dagre's curved
connectors are deliberately excluded) and keeps the highest-scoring one.

---

## Customising the look

All colour and layer styling lives in **`styles/azure.d2`** — edit it once and
every diagram re-skins. Classes:

- containment: `sub`, `rg`, `vnet`, `subnet`
- leaf: `svc` (the node *is* the official icon)
- flows: `ingress`, `sync`, `devops`, `egress`, `pe`, `peering`, `replication`, `mgmt`
- state: `future` (deferred phase or DR standby)
- chrome: `legend`, `titleblock`

The flow colours were reverse-engineered from `examples/reference/` so generated
output reads the way the hand-made diagrams do. Adding a new meaning means adding
a class here and a legend entry — never an inline style.

### Two quality gates, deliberately separate

| Gate | Tool | Judges | Basis |
|---|---|---|---|
| **Contract** | `bin/contract.py` | the design: arrows, icons, metadata, legend, accuracy, density | Microsoft's WAF diagramming guidance + icon terms — see `docs/azure-diagram-guidelines.md` |
| **Geometry** | `bin/lint.py` | the render: overlaps, crossings, proportion | pure SVG geometry |

A diagram must pass the contract and score well on geometry. They fail for
different reasons and neither substitutes for the other: a tidy render of an
inaccurate design is still wrong.

`docs/reference-review.md` records how your existing hand-made diagrams (Mitie,
RADical) measure against the guidance, and which gap each rule now closes.

### Design rules baked in (from Microsoft's WAF diagramming guidance)

- **Official icons and names**, never recoloured or distorted.
- **Consistency** — standard colours, casing, icon sizes, line weights, line
  types, arrowheads, border styles for like elements.
- **Accuracy** — a PaaS service reached over a private endpoint is drawn *outside*
  the subnet with a dashed PE connection, not inside it.
- **Directional arrows**, client → dependency; `<->` only where the relationship
  genuinely is two-way (VNet peering, read/write to profile storage).
- **A house flow vocabulary** lifted from the reference diagrams — blue inflow,
  orange DevOps, red internet boundary, dash-dot peering, green replication,
  purple management, dashed blue private endpoint, grey deferred.
- **Accessibility** — every layer is distinguished by colour *and* pattern (e.g.
  resource groups are dashed), never colour alone.
- **A complete legend** — the legend must carry an entry for every flow class the
  diagram uses. A colour vocabulary nobody can decode is worse than none.
- **Layer, don't overload** — every diagram declares its type (`# diagram-type:
  component`) and is checked against what belongs at that layer.

---

## What still needs doing

- **Install the binaries.** `d2` and a rasterizer are not yet on this machine —
  run `.\setup.ps1` (see the Windows install section). Until then the contract
  and the icon manifest work, but nothing renders.
- **Tune the palette to the house style.** `examples/reference/` holds the
  hand-made Mitie and RADical diagrams; reverse-engineer the final hex values in
  `styles/azure.d2` from them.
- **Wire the ADS skill** (README section above) — replace `generate_diagram.py`
  with the shim that writes a `.d2` and calls `bin/optimize.py`.
- **Grow `examples/` and `evals/`.** Every approved diagram becomes a few-shot
  exemplar; every manual correction becomes a style-contract line or a new lint
  check, so a problem solved once stays solved.
- **Encode the next correction as a rule.** When you fix something by hand, add
  it to `bin/contract.py` (design) or `bin/lint.py` (geometry) so it cannot
  regress. `evals/bad-diagram.d2` should trip every rule you add.
