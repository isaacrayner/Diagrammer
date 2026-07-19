# Draw.io Phase 0 — how to run it on your machine

This folder now contains a **hand-built proof** that the draw.io direction works:
`radical-systems.drawio`. This README is the "what do I actually do" guide — read
it on mobile, run the steps on your laptop after you've pulled the branch.

It also records an **honest triple-check** (bottom section) of whether this
approach really meets the project's requirements — including one thing I got wrong
in the earlier plan and have corrected here.

---

## TL;DR — what you are testing

One question: **does draw.io give us Azure-icon diagrams in the house style, with
lines that route around objects — the thing the D2 grid could not do?**

You test it by opening `radical-systems.drawio`, then **dragging a node** and
watching the connectors bend around it. If that looks right, we build the real
converter (Phase 2). If it doesn't, we stop and rethink — for the cost of one
afternoon, not weeks.

---

## What's in this folder

| File | What it is | Committed? |
|---|---|---|
| `radical-systems.d2` | The design in D2 (the LLM's output; the semantic source) | yes |
| `radical-systems.drawio` | **The Phase-0 sample** — open this in draw.io | yes |
| `radical-systems-preview.svg` | A quick preview render so you can eyeball the look without draw.io | no (regenerable) |
| `../../bin/phase0_radical_to_drawio.py` | The generator that built the `.drawio` from the `.d2` + icons + styles | yes |

**The icons are embedded inside the `.drawio` as data** — so to *view* it you need
nothing except draw.io. No icon build, no Python, no internet.

---

## Step 1 — get the code onto your machine

After you've merged/submitted the PR (or just checked out the branch):

```bash
git clone <your-repo-url> Diagrammer        # if you don't have it yet
cd Diagrammer
git checkout claude/grid-diagram-gui-strategy-b82bct
git pull
```

The file you want is `designs/radical-systems/radical-systems.drawio`.

---

## Step 2 — open the diagram (pick ONE)

### Option A — draw.io Desktop (easiest, fully local, recommended for the test)

1. Download draw.io Desktop from **https://github.com/jgraph/drawio-desktop/releases**
   (pick the installer for your OS). It runs 100% offline — nothing leaves your machine.
2. Launch it → **Open Existing Diagram** → choose
   `designs/radical-systems/radical-systems.drawio`.

That's it. No Docker, no terminal.

### Option B — the self-hosted container (what the real pipeline will use)

This is the setup you said you're happy to host. You need **Docker Desktop**
installed and running first (https://www.docker.com/products/docker-desktop/).

```bash
# start the draw.io web app locally
docker run -d --name drawio -p 8080:8080 jgraph/drawio

# then open this URL in your browser (offline = cloud storage disabled):
#   http://localhost:8080/?offline=1&https=0
```

In that browser tab: **Open Existing Diagram → Device →** pick
`radical-systems.drawio` from disk. (The web container reads/writes files through
your browser, not a server folder — that's expected.)

To stop it later: `docker stop drawio && docker rm drawio`.

---

## Step 3 — the actual test

Once it's open:

1. **Look:** official Azure icons, subscription/RG/VNet/subnet nesting in the house
   colours, dashed resource groups, colour-coded connections, a legend, a title.
2. **Drag test (the important bit):** grab a node — e.g. a **Hub VM** — and drag it
   somewhere awkward, even outside its subnet. Watch the connectors **re-route
   around** the boxes instead of cutting through them. That is draw.io's orthogonal
   router (`edgeStyle=orthogonalEdgeStyle`) doing what the D2 grid refused to do.
3. **Add test (optional):** double-click empty space to add a shape — you'll want
   the Azure icons in the shapes panel; that library is a Phase-1 task (see below).

If both look good, the approach is validated.

---

## (Optional) Export a PNG for the Word doc — the pipeline step

This is how the finished diagram becomes an image for the ADS document, replacing
the old resvg step. It uses a **second** container built for headless export
(needs Docker running):

```bash
cd Diagrammer/designs/radical-systems
docker run --rm -w /data -v "$PWD:/data" rlespinasse/drawio-desktop-headless \
  --no-sandbox -x -f png --scale 2 -o radical-systems.png radical-systems.drawio
```

You'll get `radical-systems.png`. (`-f svg` gives you an SVG instead.)

---

## (Optional) Regenerate the sample

Only needed if you want to change the sample and rebuild it. The flat icon files
are generated from the vendored set, so build them first:

```bash
cd Diagrammer
python bin/build_manifest.py                    # makes icons/<slug>.svg + manifest.json
python bin/phase0_radical_to_drawio.py          # rewrites the .drawio + preview.svg
```

---

## Triple-check: does this actually meet the requirements?

I re-read the gate code (`bin/contract.py`, `bin/lint.py`) to verify, not assume.
Here is the honest scorecard.

| Requirement | Met? | Evidence / note |
|---|---|---|
| **Official Azure icons, unmodified** | ✅ | The 41 icons in the sample are the exact `icons/<slug>.svg` files your D2 pipeline uses, embedded into the `.drawio`. Same source, guaranteed parity. |
| **House visual style** (colours, dashes, line semantics) | ✅ | Every container/edge style was translated from `styles/azure.d2` using its exact hex values. The style-map lives in `bin/phase0_radical_to_drawio.py`. |
| **Semantic contract** (arrows directional, PaaS-over-PE outside subnet, legend covers every flow, declared diagram type, …) | ✅ | `contract.py` runs **unchanged** because the LLM still authors D2. Verified: `python bin/contract.py designs/radical-systems/radical-systems.d2` → **PASS, 0 errors, 0 warnings**. |
| **Lines route around objects** (the original pain) | ✅ | draw.io's `orthogonalEdgeStyle` router. This is what you're testing in Step 3. |
| **PNG for the Word pipeline** | ✅ | Headless-export container (command above). Renders real diagrams — unlike resvg, which couldn't. |
| **Local / confidential** (why the SaaS portal was dropped) | ✅ | Both the editor container (`?offline=1`) and the export container run fully offline. draw.io Desktop likewise. |
| **Geometry quality gate** (`lint.py`: overlaps, crossings, aspect) | ⚠️ **Not yet** | **This is the correction.** `lint.py` reads **D2-specific** SVG markup — it finds connectors by `class="...connection..."` (line 81) and edge-labels by `class="...italic..."` (line 90), neither of which draw.io emits. On a draw.io SVG it would silently see **zero connectors** and mis-classify labels, so its score would be meaningless. It does **not** run unchanged on the draw.io path, contrary to what the first plan said. |

### What the ⚠️ means, plainly

Five of the six requirements are met by this sample. The sixth — the automated
geometry linter — needs a **draw.io-SVG adapter**: a small rewrite of `lint.py`'s
`extract()` function so it understands how draw.io labels its edges and text,
instead of D2's convention. It's a contained, known piece of work (roughly a day),
not a hole in the plan — but it *is* real added scope that I under-stated earlier,
and you should budget for it. Until it's done, geometry quality on the draw.io path
is judged by eye, not by the 0–100 score.

Everything else — the icons, the styling, the semantic contract, the routing, the
PNG export, the offline story — carries over intact.

---

## Next steps (after you've done the drag test)

1. **If routing + look pass:** build **Phase 2** — generalise
   `bin/phase0_radical_to_drawio.py` into `bin/d2_to_drawio.py` that reads *any*
   design's `.d2`, so the Claude skill produces `.drawio` automatically.
2. **Phase 1 side-task:** generate the Azure icon **shape library** (`.mxlibrary`)
   from `icons/manifest.json` so humans can drag new official-icon nodes in the
   editor.
3. **The ⚠️ task:** add the draw.io-SVG adapter to `lint.py` so the geometry gate
   works on the new path.

Full detail for all of this is in `docs/drawio-pipeline-plan.md`.
