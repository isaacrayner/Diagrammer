# Plan — Draw.io as the Human-Edit Surface, Driven by the Existing Pipeline

**Status:** implementation plan. Companion to `diagram-gui-editor-plan.md`, which
weighed build-vs-buy; this one commits to the **buy/host** path and details how a
self-hosted draw.io container becomes the manipulation GUI **without discarding a
single existing prerequisite** — the icons, the style contract, the semantic
contract, the geometry linter, or the Claude skill's authoring rules.

**The ask this answers:** host a draw.io container, and give the local Claude skill
a way to *generate* draw.io diagrams that already obey every rule that dictates how
a diagram should look — icons, colours, line semantics, layering, legend, Microsoft
WAF guidance.

---

## 1. The one principle that does not change

`azure-diagram-tool-build-plan.md` §1 is still the law:

> **The LLM decides *what connects to what* (semantics). A deterministic engine
> decides *where the arrow goes* (geometry). They are never the same actor.**

Draw.io is a **coordinate** format. So the Claude skill must **not** hand-write
`.drawio` XML with x/y positions — that would put the LLM back in the pixel
business it is bad at, and would throw away `contract.py`, `icon-index.md`, and
`style-contract.md` in one move.

Therefore: **the skill keeps writing D2** (its semantic strength, all existing
rules intact), and a **deterministic converter** turns that D2 into a styled,
icon-bearing, auto-laid-out `.drawio` file. The human then opens *that* in the
hosted container and adjusts — and draw.io's orthogonal router keeps the lines
bending around objects on every drag. **That routing is the whole reason we came
here** (D2 grids cannot route; see `diagram-gui-editor-plan.md` §1a).

---

## 2. Target pipeline

```
 Claude skill  ──►  design.d2  ──►  contract.py  ──►  d2→drawio      ──►  design.drawio
 (PROMPT.md,        (semantic     (SEMANTIC GATE,     converter          (icons embedded,
  style-contract,    IR, as         unchanged)         (NEW)              house styles,
  icon-index —       today)                                              titleblock+legend,
  UNCHANGED)                                                             seed auto-layout)
                                                                              │
                                                        human opens in HOSTED draw.io container
                                                        (offline, local) — drags, re-routes;
                                                        draw.io's orthogonal router avoids objects
                                                        + can drag NEW nodes from the icon library
                                                                              │
                                        ┌─────────────────────────────────────┼──────────────┐
                                        ▼                                     ▼               ▼
                             headless export container            lint.py on the SVG    save design.drawio
                             drawio -x -f png/svg  ──►  design.png/.svg   (GEOMETRY GATE,   next to design.d2
                             (rlespinasse/drawio-desktop-headless)         unchanged)       (versioned)
                                        │
                                        ▼
                             embed PNG in the Word doc via the existing
                             <!-- IMAGE: design.png 100 center --> mechanism
```

Everything in **CAPS/unchanged** already exists and is reused as-is. Only three new
pieces are built (§4).

---

## 3. How every existing prerequisite is leveraged

This is the core of the plan — nothing is thrown away.

| Existing asset | Role in the draw.io pipeline | Change needed |
|---|---|---|
| **`skill/PROMPT.md`, `style-contract.md`, `icon-index.md`** | The skill still authors **D2** by these exact rules. The authoring contract is untouched. | **None.** |
| **`bin/contract.py`** (semantic gate) | Still runs on `design.d2` before conversion — directional arrows, PE-outside-subnet, legend completeness, layer discipline, no-markdown-block, etc. | **None.** (Optional thin post-convert assertion that the `.drawio` still carries the legend + titleblock.) |
| **`icons/<slug>.svg` + `icons/manifest.json`** | Two uses: (a) the converter **embeds** each service's official SVG into the `.drawio` (`shape=image`); (b) a generated **draw.io shape library** loads the same set into the container so a human can drag *new* official-icon nodes. Icon parity with the D2 path is guaranteed — both read from `icons/`. | Build a library file from them (§4c). |
| **`styles/azure.d2`** (the visual truth) | Its classes (`sub/rg/vnet/subnet/svc` and flows `ingress/sync/pe/…`) are translated **once** into draw.io style strings. This **style-map** becomes the single visual truth for the draw.io path, mirroring `azure.d2`. | Build the style-map (§4a). |
| **`templates/target-state.d2`** (titleblock + legend) | The converter reproduces the same title block and full legend in the `.drawio`, so every rule about "a legend for every flow class used" still holds visually. | Converter emits them (§4b). |
| **`bin/lint.py`** (geometry gate) | Runs on the **SVG the headless exporter produces** — overlap, crossings, aspect ratio. | **Adapter needed** (see caveat below). |
| **`bin/render.py` / `optimize.py` / `resvg`** | The D2→SVG/PNG render path still exists for a fast, no-human "first look". For the *edited* diagram, headless draw.io export replaces resvg (it rasterises natively, and — unlike resvg — it *can* render a proper diagram). | Kept; new export path added alongside. |
| **`designs/<customer>/`** | Now holds `x.d2` (semantic seed) **and** `x.drawio` (human-edited truth) **and** `x.png/.svg` (export), all versioned together — the WAF "store sources with the workload" guidance still satisfied. | Convention update only. |
| **Local / confidential constraint** (killed the SaaS portal) | The hosted container runs with `?offline=1` — cloud storage disabled, stateless, nothing leaves the machine. Headless export is a local container too. | Honoured by design. |

**Net:** the skill, the semantic gate, and the icon set are reused verbatim. The
geometry gate is reused in *purpose* but needs a small adapter (below). The
genuinely new surface is a **style translation + a converter + an icon library** —
three deterministic, testable artifacts — plus that lint adapter.

> **Correction (verified against the code, not assumed).** `bin/lint.py` reads
> **D2-specific** SVG markup: it finds connectors by `class="…connection…"`
> (`lint.py:81`) and edge-labels by `class="…italic…"` (`lint.py:90`), neither of
> which draw.io emits. On a draw.io-exported SVG it would silently see **zero
> connectors** and mis-classify labels, so its 0–100 score would be meaningless.
> The geometry gate therefore does **not** run unchanged on the draw.io path — it
> needs a **draw.io-SVG adapter**: a rewrite of `lint.py`'s `extract()` to
> understand draw.io's edge/label markup. Contained (~a day), but real added scope.
> This became a Phase-3 work item (§8). `contract.py`, by contrast, *does* run
> unchanged, because the skill still authors D2 — verified: it PASSes on
> `radical-systems.d2` with 0 errors.

---

## 4. The three new pieces

### 4a. `styles/azure.drawio-style.json` — the style-map (the crux)
A one-time translation of every class in `styles/azure.d2` into a draw.io mxGraph
style string. This is where "how it should look" is enforced for the draw.io path.
Illustrative shape (values come from `azure.d2`):

```jsonc
{
  "containers": {
    "sub":    "rounded=1;strokeColor=#37475A;strokeWidth=3;fillColor=#F2F5F8;fontStyle=1;verticalAlign=top",
    "rg":     "rounded=1;dashed=1;strokeColor=#0078D4;fillColor=#F8FBFE;fontStyle=1;verticalAlign=top",
    "vnet":   "rounded=1;strokeColor=#0E70C0;fillColor=#E4F0FB;fontStyle=1;verticalAlign=top",
    "subnet": "rounded=1;strokeColor=#90A2BC;fillColor=#FAFBFD;fontStyle=1;verticalAlign=top"
  },
  "leaf": { "svc": "shape=image;verticalLabelPosition=bottom;verticalAlign=top;imageAspect=1;image={ICON}" },
  "edges": {
    "ingress":     "edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#1F6FEB;endArrow=block",
    "sync":        "edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#37475A;endArrow=block",
    "pe":          "edgeStyle=orthogonalEdgeStyle;rounded=0;dashed=1;strokeColor=#1F6FEB;endArrow=open",
    "peering":     "edgeStyle=orthogonalEdgeStyle;rounded=0;dashPattern=8 4 1 4;strokeColor=#37475A;startArrow=block;endArrow=block"
    /* egress, devops, replication, mgmt … one line each, from azure.d2 */
  }
}
```

Two things to note: `edgeStyle=orthogonalEdgeStyle` **is** draw.io's obstacle-aware
orthogonal router — that single token is the fix for the original pain. And every
class stays defined in exactly one place, exactly as `azure.d2` is today.

*Done when:* a rendered `.drawio` built from this map is visually
indistinguishable from the D2 render of the same design.

### 4b. `bin/d2_to_drawio.py` — the converter
Deterministic, stdlib-only (house style). Steps:
1. Parse the D2 semantic graph (nodes, classes, containment, edges + edge classes).
   The skill already writes a constrained D2 subset, so this is a small parser, not
   a general D2 implementation.
2. Compute a **seed layout** — reuse ELK (via the existing render) or `elkjs`/a
   layered pass — to get starting coordinates and container bounds. It only has to
   be a *reasonable* starting point; the human refines and draw.io re-routes on
   drag, so pixel-perfection here is not required.
3. Emit mxGraph XML: each container → a group cell with its style-map style; each
   service → `shape=image` embedding `icons/<slug>.svg`; each edge → its class's
   orthogonal style; plus the titleblock and legend from the template.
4. Write `designs/<customer>/<customer>.drawio`.

*Done when:* `contract.py` passes on the `.d2`, the converter emits a `.drawio`
that opens cleanly in the container showing correct icons, colours, dashed RGs,
legend, and orthogonally-routed edges.

### 4c. `bin/build_drawio_library.py` — the icon library for humans
Reads `icons/manifest.json` and emits an `.mxlibrary` (`File → Open Library`) so
every official icon is a named, searchable, drag-to-canvas shape in the container.
This covers nodes a human adds that the LLM didn't — keeping them on the same
official set.

*Done when:* the library loads in the hosted container and every manifest slug is
draggable with its official SVG and correct default `svc` style.

---

## 5. The hosting: two containers, different jobs

Be clear these are **two separate images** — do not expect the web UI to be an API.

**A. The edit surface (human) — `jgraph/drawio`, offline.**
```bash
docker run -d --name drawio -p 8080:8080 jgraph/drawio
# open:  http://localhost:8080/?offline=1&https=0
```
`?offline=1` disables cloud storage (confidentiality); the container is stateless.
The human uses **Open Existing Diagram → Device** to open
`designs/<customer>/<customer>.drawio` from disk, edits, and saves back to disk.
(Mount the `designs/` folder into the container, or run the container against a
local path, so open/save land in the repo. The draw.io **desktop app** is an even
simpler local alternative for this one step if the container's browser-file flow
feels clumsy — same file, same result.)

**B. The exporter (pipeline) — `rlespinasse/drawio-desktop-headless`.**
```bash
docker run --rm -w /data -v "$PWD/designs:/data" rlespinasse/drawio-desktop-headless \
  -x -f png  --scale 2 -o customer/customer.png  customer/customer.drawio
docker run --rm -w /data -v "$PWD/designs:/data" rlespinasse/drawio-desktop-headless \
  -x -f svg               -o customer/customer.svg  customer/customer.drawio
```
This is the deterministic `.drawio → PNG/SVG` step the Word pipeline and `lint.py`
consume. It replaces the resvg step for edited diagrams (and renders real diagrams
resvg couldn't). Wrap both in `bin/drawio_export.py` so the skill calls one script.

---

## 6. Source-of-truth rule (state it, live by it)

- **`design.d2`** — the LLM's semantic output and the **seed**. Diffable, gated by
  `contract.py`. Regenerating it re-seeds a fresh `.drawio`.
- **`design.drawio`** — the **truth for any diagram a human has edited.** Once
  someone drags a node, positions live here, not in the D2.
- D2 → drawio is a **one-way seed**; there is no lossless drawio → D2. Do not try to
  round-trip positions back into D2 — that mistake is what makes these systems
  miserable. If the semantics change, re-seed and re-apply edits, or edit the
  `.drawio` directly.

Both files, plus the exported PNG/SVG, live in `designs/<customer>/` and version
together.

---

## 7. What changes in the Claude skill

Small, additive. The diagram step becomes:

> **Step 3 — Generate the architecture diagram.**
> 1. Write `designs/[Customer]/[Customer].d2` per `skill/PROMPT.md`,
>    `style-contract.md`, `icon-index.md` *(unchanged)*.
> 2. `python bin/contract.py designs/[Customer]/[Customer].d2` *(unchanged gate)*.
> 3. `python bin/d2_to_drawio.py designs/[Customer]/[Customer].d2` → `.drawio`.
> 4. *(Optional human step)* open the `.drawio` in the draw.io container, adjust.
> 5. `python bin/drawio_export.py designs/[Customer]/[Customer].drawio` → PNG/SVG.
> 6. `python bin/lint.py designs/[Customer]/[Customer].svg` *(unchanged gate)*.
> 7. Embed the PNG with `<!-- IMAGE: -->` *(unchanged)*.

The skill never writes `.drawio` by hand. Human editing is an **optional** step
between 3 and 5 — the pipeline produces a correct diagram with or without it.

---

## 8. Phased plan (each phase has a *Done-when*)

**Phase 0 — Prove the look (½–1 day).** Hand-build one `.drawio` for
`radical-systems` using draft style-map values + embedded icons. Open in the hosted
container.
*Done when:* it visually matches the house style **and** dragging a node makes edges
re-route around it. If the look or routing disappoints, stop before building the
converter.

**Phase 1 — Style-map + icon library (§4a, §4c).** Translate `azure.d2`; generate
the `.mxlibrary`.
*Done when:* library loads in the container; a hand-styled node matches the D2 render.

**Phase 2 — Converter (§4b).** `d2_to_drawio.py` for the constrained D2 subset the
skill emits, with seed layout.
*Done when:* `radical-systems.d2` → `.drawio` opens with correct icons, containers,
legend, titleblock, orthogonal edges; `contract.py` passed on the `.d2`.

**Phase 3 — Export + gate (§5B).** `drawio_export.py` around the headless container;
**add a draw.io-SVG adapter to `lint.py`** (rewrite `extract()` for draw.io's
edge/label markup — see the correction in §3), then wire it in.
*Done when:* `.drawio` → PNG/SVG headlessly, PNG embeds in the Word doc, and
`lint.py` returns a *correct* connector count + score on the draw.io SVG (not the
zero-connector misread it gives today).

**Phase 4 — Fold into the skill (§7).** Update `skill/SKILL.md` + README.
*Done when:* the full LLM→D2→drawio→(optional edit)→PNG loop is documented and runs
end to end on one customer.

---

## 9. Honest caveats

- **The converter is the real work.** Parsing even a constrained D2 subset and
  emitting valid mxGraph XML with a decent seed layout is a few days, not an hour.
  The style-map and library are easy; the converter is the load-bearing build.
- **Seed layout quality.** The converter's auto-layout only needs to be a good
  starting point, but a *bad* one makes the human do more dragging. Reusing ELK for
  coordinates keeps it consistent with today's output.
- **Container file I/O is browser-based**, not a server drop-folder. Mount `designs/`
  or use the desktop app; don't expect to POST a diagram to the web container.
- **Divergence is real** (§6). The one-way-seed rule is load-bearing; teams that
  ignore it will hit "why did my layout reset" confusion.
- **Two images to operate** (edit + export). Slightly more moving parts than a pure
  local binary, but both run offline and the export one is CI-friendly.

---

## 10. Immediate next step

**Phase 0**: hand-build one `radical-systems.drawio` with embedded official icons and
draft house styles, open it in a locally-run `jgraph/drawio` container, and confirm
two things at once — it *looks* right, and edges *route around* dragged nodes. That
single afternoon validates the entire approach before the converter is written. I
can produce that hand-built `.drawio` from the existing `icons/` and
`radical-systems.d2` on request.

---

*Sources for the hosting/export claims:*

- [jgraph/docker-drawio — self-hosted container](https://github.com/jgraph/docker-drawio)
- [Run your own draw.io server with Docker (offline mode `?offline=1`, stateless)](https://www.drawio.com/blog/diagrams-docker-app)
- [rlespinasse/docker-drawio-desktop-headless — headless export](https://github.com/rlespinasse/docker-drawio-desktop-headless)
- [draw.io command-line export (`-x -f png/svg -o`)](https://tomd.xyz/how-i-use-drawio/)
- [Importing custom Azure icon libraries into draw.io](https://github.com/pacodelacruz/diagrams-net-azure-libraries)
- [Microsoft official Azure architecture icons](https://learn.microsoft.com/en-us/azure/architecture/icons/)
