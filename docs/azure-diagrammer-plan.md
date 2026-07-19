# Azure Architecture Diagrammer — Build Plan (current)

*Supersedes the earlier SaaS/portal plan. The design settled on a **local, free,
open-source** pipeline after the volume (a few diagrams a year) and the
confidentiality of client architecture made a paid hosted portal the wrong fit.*

## 1. What it is

An LLM writes a diagram as **D2 text**; D2 + the **ELK** layout engine render it
with the **official Azure icons** and neat auto-routed connectors; a
**deterministic linter** and a **best-of-N optimizer** gate the quality; the
result exports to SVG/PNG and drops into the ADS Word document.

Principles: nothing leaves the machine, no subscription, no API key, no server.
The design artifact is the `.d2` text — versionable and diffable — stored per
customer alongside the ADS document. It runs identically on any machine after a
`git clone`.

## 2. Repository layout

```
azure-arch-diagrammer/
├── README.md
├── setup.sh                  # installs d2 + resvg, verifies icons present
├── bin/
│   ├── render.sh             # design.d2 -> design.svg + design.png
│   ├── lint.py               # deterministic geometry checks + score   [BUILT]
│   └── optimize.py           # best-of-N layout search, scored by lint  [BUILT]
├── styles/
│   └── azure.d2              # the colour/layer system (sub/rg/vnet/subnet/svc)
├── icons/                    # vendored official Azure SVGs (offline)
│   └── manifest.json         # service name + aliases -> icon file
├── templates/                # starter .d2 skeletons (target-state, phased)
├── skill/                    # LLM instructions (tuned from example PNGs)
│   ├── PROMPT.md             # ADS notes -> .d2 generation rules
│   ├── style-contract.md     # which class wraps which layer; dashed vs solid
│   ├── icon-index.md         # the service -> icon list the LLM selects from
│   └── critic.md             # the review-agent prompt (Layer 3)
├── examples/                 # approved reference diagrams = golden + few-shot set
├── evals/                    # notes -> expected-diagram regression pairs
└── designs/<customer>/       # per-engagement .d2 + rendered output + phases/
```

## 3. The colour / layer system  (`styles/azure.d2`)

One file defines the visual language for each containment level, and every
design imports it (`...@styles/azure.d2`), so the whole estate re-skins from a
single edit.

| Layer | Treatment |
|---|---|
| Subscription | heavy slate border, light blue-grey fill, bold title |
| Resource Group | dashed Azure-blue border (matches the standard RG convention) |
| VNet | solid blue-tinted box |
| Subnet | light grey box |
| Service (leaf) | the node **is** the official Azure icon, label beneath |

Connections: solid = HTTPS/synchronous, dashed = private endpoint / diagnostics.
Verified working across a two-subscription / multi-RG / multi-VNet example.

## 4. Icons  (`icons/` + `manifest.json`)

The official Microsoft Azure architecture icon SVGs are **vendored into the
repo** so rendering is offline and identical everywhere. `manifest.json` maps
canonical names and aliases ("SQL MI" = "Azure SQL Managed Instance") to files
so the generator can't pick the wrong icon. Download Microsoft's official set
once and drop it in — Microsoft permits these icons in architecture diagrams
(do not recolour or distort them).

## 5. Render + quality pipeline

**render.sh** — `d2 --layout elk` → SVG → rasterize to print-DPI PNG. Rasterizer:
`resvg` (single binary, best cross-machine portability) with `rsvg-convert` as a
fallback. Note: D2's own PNG export needs a bundled browser and is unreliable
offline — rasterize the SVG instead.

**lint.py  [BUILT]** — parses the rendered SVG (exact geometry, no vision model)
and scores it out of 100. Current checks:

- `label_on_icon` — a service label sitting on top of its icon
- `edge_label_on_icon` — a connection label sitting on top of a leaf icon
- `edge_crossings` — connectors crossing each other (from path geometry)
- `node_overlap` — node boxes partially overlapping (nesting is allowed)
- `aspect_ratio` — canvas too tall or too wide

Proven to separate a broken render (labels on icons → **4/100**) from a good one
(**82/100**) from a clean layered one (**100/100**).

**optimize.py  [BUILT]** — renders the same diagram across `{elk, dagre} x {down,
right}`, lints each, keeps the best score. Because rendering is fast and free,
this brute-forces a good layout with no agent. In testing it lifted a tall
82/100 layout to a well-proportioned 92/100 automatically.

**Tuning rule learned in testing:** the optimizer once picked `dagre` (curved
connectors) over `elk` (orthogonal) because dagre scored marginally higher on
proportion — but orthogonal routing looks more professional. **Action:** bias
selection toward ELK unless another engine wins by a clear margin (e.g. ≥5
points), or add a small lint penalty for curved connectors. This is the model
for all future tuning: encode the preference as a rule, don't rely on memory.

## 6. Generation config  (`skill/`) — *pending example PNGs*

Three plain-text files teach an LLM to turn ADS notes into a `.d2`: the
generation prompt, the style contract (class-per-layer, dashed-vs-solid, naming),
and the icon index. When the reference PNGs arrive, reverse-engineer the house
style from them and write these files so generated output matches hand-drawn
work. This is the "configure the prompts" step.

## 7. The critic agent (Layer 3, optional)

For judgments geometry can't make: is the grouping logical (right service in the
right subnet)? does it match the reference examples' look? is an important flow
missing or is it cluttered? The critic consumes the **lint report + image + D2
source**, proposes edits to the **D2 text**, then re-render → re-lint, looping
until clean or a budget is hit. Rule for the critic: **trust the linter for
geometry; spend judgment on semantics and style.**

## 8. Iterative learning — the honest version

Nothing retrains a model (and shouldn't, at this volume — fine-tuning is real but
wildly disproportionate). "Learning" here is **artifact accumulation in the
repo**, which is better because it's inspectable and portable:

- **Golden set as few-shot** — every approved diagram is saved and fed back as an
  exemplar for the next generation. More examples, better output.
- **Rule accretion** — every manual correction becomes either a line in the style
  contract or a **new lint check**, so the system provably never regresses on a
  problem solved once (the ELK-vs-dagre rule above is the first entry).
- **Eval harness** (`evals/`) — a handful of notes→expected pairs re-run on any
  prompt or palette change, so improving one diagram can't silently break another.

## 9. ADS skill integration

Replace `generate_diagram.py` with a thin shim that (a) writes a `.d2` into
`designs/<customer>/`, (b) calls `render.sh` (or `optimize.py`), (c) embeds the
PNG through the existing `<!-- IMAGE: ... -->` mechanism. The skill's interface
is unchanged; only the output quality changes.

## 10. Phase-awareness

Each phase is a `.d2` under `designs/<customer>/phases/`, all importing the one
style file. Enhancement for later: keep node IDs stable across phases and reuse a
shared base so a service that persists sits in the same place every phase (the
migration reads as one coherent story rather than reshuffling each stage).

## 11. Deployment across machines

`git clone` + `./setup.sh`. Because the icons are vendored and both tools are
single binaries (d2, resvg), it works offline and renders identically anywhere.
Version-control the `.d2` sources, the style file, the skill config, and the
icons; the PNGs are regenerable artifacts.

## 12. Status and build order

Done:
- Colour/layer style system (demonstrated)
- Official-icon rendering via D2 + ELK (demonstrated)
- `bin/lint.py` — deterministic geometry linter
- `bin/optimize.py` — best-of-N layout optimizer

Next, in order:
1. `setup.sh` + `render.sh` + vendored icon set + `manifest.json`
2. Finalise `styles/azure.d2` and templates (tune palette to your PNGs)
3. `skill/` prompt + style-contract + icon-index (from your PNGs)
4. Wire the ADS shim; batch-generate phase diagrams; auto-embed PNGs
5. Add the ELK bias rule to `optimize.py`; grow `examples/` and `evals/`
6. (Optional) `skill/critic.md` review loop

## 13. Open tuning notes

- ELK (orthogonal) preferred over dagre (curved) for the house style — encode as
  a selection bias / lint penalty.
- Long service names can overflow the icon width — shorten in the icon index or
  allow two-line labels.
- Icon licence: official set only, no recolour/distort, not for own-product use.
