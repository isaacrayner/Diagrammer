#!/usr/bin/env python3
"""
render.py - single plain render of a design: design.d2 -> design.svg + design.png

Uses ELK (orthogonal routing, the house style) with no layout search. For the
quality-gated best-of-N render use optimize.py instead.

Designs are authored with `icon: ./icons/<slug>.svg`. d2 resolves icon paths
relative to the .d2 file, so before rendering we materialise a temporary sibling
with those paths rewritten (see d2paths.py). The file you author and commit keeps
the clean form.

Usage:
    python bin/render.py designs/contoso/contoso.d2 [--direction down] [--zoom 2]
"""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import d2paths

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d2paths.ensure_path()   # find d2/resvg even in a shell opened before install

def render(d2_path, direction=None, zoom="2"):
    d2_path = os.path.abspath(d2_path)
    if not os.path.exists(d2_path):
        sys.exit(f"not found: {d2_path}")
    base = os.path.splitext(d2_path)[0]
    svg, png = base + ".svg", base + ".png"

    # d2 resolves icon: relative to the .d2 file, so render a rewritten sibling
    prefix = (lambda s: f"direction: {direction}\n" + s) if direction else None
    tmp = d2paths.materialise(d2_path, extra=prefix)
    src_arg = tmp

    try:
        # cwd = the design's own directory: d2 resolves imports relative to the
        # working directory and icons relative to the file, so this is the one
        # place where both agree (see d2paths.py).
        r = subprocess.run(["d2", "--layout", "elk", "--theme", "0", "--pad", "50",
                            src_arg, svg], cwd=os.path.dirname(d2_path),
                           capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("d2 not found on PATH - run setup.ps1 (Windows) or setup.sh")
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)

    if r.returncode != 0:
        sys.exit(r.stderr.strip() or "d2 render failed")
    print("rendered:", os.path.relpath(svg, ROOT))

    for cmd in (["resvg", "--zoom", zoom, svg, png],
                ["rsvg-convert", "-z", zoom, svg, "-o", png]):
        try:
            if subprocess.run(cmd, cwd=ROOT, capture_output=True).returncode == 0:
                print("rendered:", os.path.relpath(png, ROOT))
                return
        except FileNotFoundError:
            continue
    print("PNG skipped - install resvg or rsvg-convert (see setup script)")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: python bin/render.py path/to/diagram.d2 [--direction down] [--zoom 2]")
    path = args[0]
    opts = dict(zip(args[1::2], args[2::2]))
    render(path, opts.get("--direction"), opts.get("--zoom", "2"))
