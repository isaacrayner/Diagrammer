#!/usr/bin/env python3
"""
optimize.py - render a diagram across layout variants, score each with lint.py,
keep the cleanest. Because D2 rendering is fast and free, this brute-forces its
way to a good layout with no agent and no cost.

Variants tried: {elk, dagre} x {down, right}. Each is scored by the geometry
linter; the highest-scoring variant is written to <base>.svg (+ .png if a
rasterizer is available) and <base>.optimized.d2 records the winning settings.

Usage:
    python optimize.py path/to/diagram.d2
"""
import sys, os, re, subprocess, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lint, d2paths

# d2 resolves BOTH imports and `icon:` paths relative to the .d2 file itself.
# Designs are authored with the uniform `icon: ./icons/<slug>.svg`, so each
# render variant is written as a temporary sibling with those paths rewritten
# (d2paths.materialise). Imports stay depth-relative in the source:
# a design in designs/<customer>/ imports `...@../../styles/azure.d2`.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d2paths.ensure_path()   # find d2/resvg even in a shell opened before install

ENGINES    = ["elk"]   # ELK only: orthogonal routing. dagre gives curved
                       # connectors that do not match the Azure house style.
# None = leave the source exactly as authored. Worth trying: ELK's own default
# often beats an imposed direction, and in testing it did.
DIRECTIONS = [None, "down", "right"]

def _set_direction(src, direction):
    if direction is None:
        return src
    if re.search(r"(?m)^\s*direction\s*:", src):
        return re.sub(r"(?m)^\s*direction\s*:.*$", f"direction: {direction}", src)
    return f"direction: {direction}\n" + src

def _render(proj, d2_name, svg_name, engine):
    d2_path  = os.path.join(proj, d2_name)
    svg_path = os.path.join(proj, svg_name)
    # cwd = the design's own directory; see the note in d2paths.py
    r = subprocess.run(["d2","--layout",engine,"--theme","0","--pad","50",d2_path,svg_path],
                       cwd=proj, capture_output=True, text=True)
    if r.returncode != 0 and r.stderr:
        print(r.stderr.strip()[:400])
    return r.returncode == 0 and os.path.exists(svg_path)

def _rasterize(proj, svg_name, png_name):
    svg_path = os.path.join(proj, svg_name)
    png_path = os.path.join(proj, png_name)
    for cmd in (["resvg","--zoom","2",svg_path,png_path],
                ["rsvg-convert","-z","2",svg_path,"-o",png_path]):
        try:
            if subprocess.run(cmd, cwd=ROOT, capture_output=True).returncode == 0:
                return True
        except FileNotFoundError:
            continue
    return False

def _cleanup(proj, base):
    for f in glob.glob(os.path.join(proj, f".opt_{base}_*")) + [os.path.join(proj, ".winner.d2")]:
        try: os.remove(f)
        except OSError: pass

def optimize(d2_path):
    proj = os.path.dirname(os.path.abspath(d2_path)) or "."
    base = os.path.splitext(os.path.basename(d2_path))[0]
    src  = open(d2_path, encoding="utf-8").read()   # '·' in labels is UTF-8
    results = []
    for eng in ENGINES:
        for dr in DIRECTIONS:
            name = f"{eng}/{dr or 'as-is'}"
            stem = f".opt_{base}_{eng}_{dr or 'asis'}"
            variant = d2paths.rewrite_icon_paths(_set_direction(src, dr), proj)
            open(os.path.join(proj, stem+".d2"), "w", encoding="utf-8").write(variant)
            if not _render(proj, stem+".d2", stem+".svg", eng):
                results.append((name, None, None)); continue
            rep = lint.lint(os.path.join(proj, stem+".svg"))
            results.append((name, rep["score"], rep))

    print("variant      score    issues")
    for name, score, rep in results:
        if score is None:
            print(f"  {name:9}    -      render failed"); continue
        iss = ", ".join(f"{i['check']}x{i['count']}" for i in rep["issues"]) or "clean"
        print(f"  {name:9}   {score:>3}/100  {iss}")

    scored = sorted([r for r in results if r[1] is not None], key=lambda r: r[1], reverse=True)
    if not scored:
        _cleanup(proj, base); print("no successful renders"); return
    win, score, _ = scored[0]
    eng, dr = win.split("/")
    if dr == "as-is":
        dr = None
    print(f"\nwinner: {win}  ({score}/100)")

    final = _set_direction(src, dr)
    # the recorded .optimized.d2 keeps the clean ./icons/ form; only the
    # throwaway .winner.d2 that d2 actually reads gets rewritten paths
    open(os.path.join(proj, base+".optimized.d2"), "w", encoding="utf-8").write(
        f"# auto-selected layout: engine={eng} direction={dr}  (lint score {score}/100)\n" + final)
    open(os.path.join(proj, ".winner.d2"), "w", encoding="utf-8").write(
        d2paths.rewrite_icon_paths(final, proj))
    _render(proj, ".winner.d2", base+".svg", eng)
    if _rasterize(proj, base+".svg", base+".png"):
        print(f"rendered: {base}.svg  {base}.png")
    else:
        print(f"rendered: {base}.svg  (install rsvg-convert or resvg for PNG)")
    _cleanup(proj, base)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python optimize.py path/to/diagram.d2"); sys.exit(2)
    optimize(sys.argv[1])
