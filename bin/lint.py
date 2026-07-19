#!/usr/bin/env python3
"""
lint.py — deterministic quality checks on a D2-rendered SVG.

Reads the exact geometry D2 emits (icon boxes, node/container rects, connector
paths, label anchors) and reports defects that layout engines don't guarantee
away: labels colliding with icons, edge labels sitting on shapes, connector
crossings, partial node overlaps, and bad canvas proportion.

No AI, no vision, no network. Pure geometry. Higher score = cleaner diagram.

Usage:
    python lint.py diagram.svg            # human-readable report
    python lint.py diagram.svg --json     # machine-readable (for the optimizer)
"""
import sys, json, re
import xml.etree.ElementTree as ET

EPS = 1e-6

# ── geometry helpers ─────────────────────────────────────────────────────────
def _box_contains(o, i, m=0.0):
    return o[0]-m <= i[0] and o[1]-m <= i[1] and o[0]+o[2]+m >= i[0]+i[2] and o[1]+o[3]+m >= i[1]+i[3]

def _boxes_overlap(a, b):
    return not (a[0]+a[2] <= b[0] or b[0]+b[2] <= a[0] or a[1]+a[3] <= b[1] or b[1]+b[3] <= a[1])

def _pt_in_box(x, y, b, m=4.0):
    return b[0]-m <= x <= b[0]+b[2]+m and b[1]-m <= y <= b[1]+b[3]+m

def _seg_cross(p1, p2, p3, p4):
    """True proper crossing (interiors intersect), ignoring shared endpoints."""
    def o(a, b, c):
        v = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        return 0 if abs(v) < EPS else (1 if v > 0 else -1)
    for q in (p1, p2):
        for r in (p3, p4):
            if abs(q[0]-r[0]) < EPS and abs(q[1]-r[1]) < EPS:
                return False  # shared endpoint = legitimate (edges meet at a node)
    d1, d2, d3, d4 = o(p3,p4,p1), o(p3,p4,p2), o(p1,p2,p3), o(p1,p2,p4)
    return d1 != d2 and d3 != d4

def _path_points(d):
    """Approximate a path 'd' as a polyline (endpoints of M/L, endpoint of C)."""
    toks = re.findall(r"[MLC]|-?\d+\.?\d*", d)
    pts, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t == 'M' or t == 'L':
            pts.append((float(toks[i+1]), float(toks[i+2]))); i += 3
        elif t == 'C':
            pts.append((float(toks[i+5]), float(toks[i+6]))); i += 7  # cubic endpoint
        else:
            i += 1
    return pts

def _tag(el): return el.tag.split('}')[-1]

# ── extraction ───────────────────────────────────────────────────────────────
def extract(svg_path):
    root = ET.parse(svg_path).getroot()
    vb = (root.get('viewBox') or '0 0 0 0').split()
    W, H = float(vb[2]), float(vb[3])

    icons, node_rects, conns, labels, edge_labels = [], [], [], [], []
    for el in root.iter():
        t, cls = _tag(el), (el.get('class') or '')
        if t == 'image':
            icons.append((float(el.get('x')), float(el.get('y')),
                          float(el.get('width')), float(el.get('height'))))
        elif t == 'rect':
            try:
                b = (float(el.get('x')), float(el.get('y')),
                     float(el.get('width')), float(el.get('height')))
            except (TypeError, ValueError):
                continue
            # skip the full-canvas background rect
            if b[2] >= W*0.98 and b[3] >= H*0.98:
                continue
            node_rects.append(b)
        elif t == 'path' and 'connection' in cls:
            p = _path_points(el.get('d', ''))
            if len(p) >= 2:
                conns.append(p)
        elif t == 'text':
            x, y = el.get('x'), el.get('y')
            if x is None or y is None:
                continue
            rec = (float(x), float(y), ''.join(el.itertext()))
            (edge_labels if 'italic' in cls else labels).append(rec)
    return dict(W=W, H=H, icons=icons, node_rects=node_rects,
                conns=conns, labels=labels, edge_labels=edge_labels)

# ── checks ───────────────────────────────────────────────────────────────────
def _near(g, box):
    """Best-guess name for a box: the label whose anchor sits inside or just
    above it. Makes lint findings actionable instead of anonymous."""
    bx, by, bw, bh = box
    best, bestd = None, 1e9
    for (x, y, txt) in g['labels'] + g['edge_labels']:
        if not txt.strip():
            continue
        if bx - 6 <= x <= bx + bw + 6 and by - 20 <= y <= by + bh + 6:
            d = abs(y - by) + abs(x - (bx + bw / 2)) * 0.1
            if d < bestd:
                best, bestd = txt.strip(), d
    return (best[:34] if best else f"box@{int(bx)},{int(by)}")


def lint(svg_path):
    g = extract(svg_path)
    issues = []
    _detail = {}

    # 1. label sitting on top of an icon
    n = sum(1 for (x, y, _) in g['labels'] for b in g['icons'] if _pt_in_box(x, y, b))
    if n: issues.append(("label_on_icon", n, "service label overlaps its icon"))

    # 2. edge label sitting on top of a leaf icon (inside a container is normal)
    n = sum(1 for (x, y, _) in g['edge_labels'] for b in g['icons'] if _pt_in_box(x, y, b, m=2.0))
    if n: issues.append(("edge_label_on_icon", n, "connection label overlaps an icon"))

    # 3. connector crossings (fewer is better)
    cross = 0
    C = g['conns']
    for a in range(len(C)):
        for b in range(a+1, len(C)):
            for i in range(len(C[a])-1):
                for j in range(len(C[b])-1):
                    if _seg_cross(C[a][i], C[a][i+1], C[b][j], C[b][j+1]):
                        cross += 1
    if cross: issues.append(("edge_crossings", cross, "connectors cross each other"))

    # 4. partial node overlaps (nesting is fine; partial overlap is not)
    #
    # D2 emits a small masking rect behind every edge label so the connector
    # doesn't run through the text. Those are NOT nodes. Counting them as nodes
    # scored an edge label resting on a container border as an 8-point "node
    # overlap", which badly distorted the score on any busy diagram. They are
    # identified by being label-sized and centred on a label anchor, and are
    # reported separately below at a much lower weight.
    def _is_label_mask(b):
        if b[3] > 26 or b[2] > 260:
            return False
        cx, cy = b[0] + b[2]/2, b[1] + b[3]/2
        return any(abs(x - cx) < b[2]/2 + 4 and abs(y - cy) < b[3]/2 + 8
                   for (x, y, t) in g['edge_labels'] + g['labels'] if t.strip())

    all_rects  = [b for b in g['node_rects'] if b[2] > 6 and b[3] > 6]
    label_msks = [b for b in all_rects if _is_label_mask(b)]
    R          = [b for b in all_rects if b not in label_msks]
    overlap = 0
    overlap_where = []
    for a in range(len(R)):
        for b in range(a+1, len(R)):
            if _boxes_overlap(R[a], R[b]) and not (_box_contains(R[a], R[b]) or _box_contains(R[b], R[a])):
                ox = min(R[a][0]+R[a][2], R[b][0]+R[b][2]) - max(R[a][0], R[b][0])
                oy = min(R[a][1]+R[a][3], R[b][1]+R[b][3]) - max(R[a][1], R[b][1])
                if ox > 4 and oy > 4:   # ignore slivers from touching edges / rounding
                    overlap += 1
                    overlap_where.append(
                        f"{_near(g, R[a])} [{int(R[a][2])}x{int(R[a][3])}] x "
                        f"{_near(g, R[b])} [{int(R[b][2])}x{int(R[b][3])}]  "
                        f"(overlap {int(ox)}x{int(oy)}px)")
    if overlap: issues.append(("node_overlap", overlap, "node boxes partially overlap"))
    _detail["node_overlap"] = overlap_where

    # 4b. an edge label resting on a container border. Cosmetic, not structural
    #     - worth nudging the author, not worth an 8-point penalty.
    onborder, onborder_where = 0, []
    for m in label_msks:
        for b in R:
            if _boxes_overlap(m, b) and not _box_contains(b, m):
                onborder += 1
                onborder_where.append(f"{_near(g, m)} sits on the edge of {_near(g, b)}")
                break
    if onborder:
        issues.append(("edge_label_on_border", onborder,
                       "connection label sits on a container border"))
    _detail["edge_label_on_border"] = onborder_where

    # 5. container label wider than its own box (the label spills over the
    #    border and collides with whatever sits beside it). Learned from the
    #    RADical render: "Web/App Subnet /23 — delegated to ACA" overflowed.
    #    ~5.4px per character at the 12-13px container font size.
    spill = 0
    for (x, y, txt) in g['labels']:
        if not txt.strip():
            continue
        w = len(txt) * 5.4
        # the box this label titles: the smallest rect whose top edge is at y
        owners = [b for b in g['node_rects']
                  if abs(b[1] - y) < 22 and b[0] - 4 <= x <= b[0] + b[2] + 4 and b[2] > 40]
        if owners and w > min(b[2] for b in owners) * 0.95:
            spill += 1
    if spill:
        issues.append(("label_overflow", spill,
                       "container label is wider than its box - shorten it"))

    # 6. canvas proportion
    ar = (g['W']/g['H']) if g['H'] else 0
    if ar and (ar > 3.5 or ar < 0.28):
        issues.append(("aspect_ratio", round(ar, 2), "canvas is very elongated"))

    penalty = 0
    weights = dict(label_on_icon=6, edge_label_on_icon=4, edge_crossings=3,
                   node_overlap=8, aspect_ratio=6, label_overflow=3,
                   edge_label_on_border=1)
    for key, count, _ in issues:
        penalty += weights.get(key, 3) * (1 if key == "aspect_ratio" else count)
    score = max(0, 100 - penalty)

    return dict(score=score, canvas=[g['W'], g['H']],
                counts=dict(icons=len(g['icons']), nodes=len(g['node_rects']),
                            connectors=len(g['conns']),
                            labels=len(g['labels'])+len(g['edge_labels'])),
                issues=[dict(check=k, count=c, detail=d,
                             where=_detail.get(k, [])) for k, c, d in issues])

import signal
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except Exception:
    pass
def main():
    # Windows consoles default to cp1252 and choke on the tick/cross glyphs
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if not args:
        print("usage: python lint.py diagram.svg [--json]"); sys.exit(2)
    rep = lint(args[0])
    if '--json' in sys.argv:
        print(json.dumps(rep)); return
    print(f"score: {rep['score']}/100   canvas {int(rep['canvas'][0])}x{int(rep['canvas'][1])}   {rep['counts']}")
    if not rep['issues']:
        print("  ✓ no geometry defects detected"); return
    for it in rep['issues']:
        print(f"  ✗ {it['check']:20} x{it['count']:<4} {it['detail']}")
        if '--explain' in sys.argv:
            for w in it.get('where', []):
                print(f"      → {w}")

if __name__ == '__main__':
    main()
