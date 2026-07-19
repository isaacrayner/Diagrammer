#!/usr/bin/env python3
"""
Phase-0 proof: hand-build designs/radical-systems/radical-systems.drawio from the
real design structure + the official icons + styles translated from azure.d2.

This is NOT the general converter (that is Phase 2, and reads D2). It hardcodes
the radical-systems structure so we can eyeball the LOOK and the ROUTING in a
draw.io container before committing to the converter build.
"""
import base64, os, html

ROOT = "/home/user/Diagrammer"
ICONS = os.path.join(ROOT, "icons")
OUT = os.path.join(ROOT, "designs/radical-systems/radical-systems.drawio")

# ── style-map: azure.d2 classes → draw.io mxGraph styles (exact hex from azure.d2)
CONTAINER_STYLE = {
    "sub":    "rounded=1;arcSize=4;strokeColor=#37475A;strokeWidth=3;fillColor=#F2F5F8;fontSize=15;fontStyle=1;fontColor=#37475A;verticalAlign=top;align=left;spacingLeft=12;spacingTop=6;html=1;whiteSpace=wrap;",
    "rg":     "rounded=1;arcSize=6;dashed=1;dashPattern=6 4;strokeColor=#0078D4;strokeWidth=2;fillColor=#F8FBFE;fontSize=13;fontStyle=1;fontColor=#0078D4;verticalAlign=top;align=left;spacingLeft=12;spacingTop=6;html=1;whiteSpace=wrap;",
    "vnet":   "rounded=1;arcSize=8;strokeColor=#0E70C0;strokeWidth=2;fillColor=#E4F0FB;fontSize=13;fontStyle=1;fontColor=#0E70C0;verticalAlign=top;align=left;spacingLeft=12;spacingTop=6;html=1;whiteSpace=wrap;",
    "subnet": "rounded=1;arcSize=8;strokeColor=#90A2BC;strokeWidth=1;fillColor=#FAFBFD;fontSize=12;fontStyle=1;fontColor=#5B6B82;verticalAlign=top;align=left;spacingLeft=10;spacingTop=5;html=1;whiteSpace=wrap;",
    "group":  "rounded=1;arcSize=4;dashed=1;dashPattern=1 3;strokeColor=#8A8886;strokeWidth=1;fillColor=#FCFCFC;fontSize=12;fontColor=#605E5C;verticalAlign=top;align=left;spacingLeft=10;spacingTop=5;html=1;whiteSpace=wrap;",
}
LEAF_STYLE = ("shape=image;imageAspect=1;aspect=fixed;verticalLabelPosition=bottom;"
              "verticalAlign=top;labelPosition=center;align=center;fontSize=11;"
              "fontColor=#323130;spacing=2;html=1;whiteSpace=wrap;image=")

# edge classes → draw.io styles (orthogonalEdgeStyle = draw.io's obstacle-aware router)
EDGE_STYLE = {
    "ingress": "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#0078D4;strokeWidth=2;fontSize=10;fontColor=#0078D4;",
    "sync":    "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#37475A;strokeWidth=2;fontSize=10;fontColor=#37475A;",
    "devops":  "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#D83B01;strokeWidth=2;fontSize=10;fontColor=#D83B01;",
    "egress":  "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#C42B1C;strokeWidth=2;fontSize=10;fontColor=#C42B1C;",
    "pe":      "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=open;dashed=1;dashPattern=3 3;strokeColor=#0078D4;strokeWidth=2;fontSize=10;fontColor=#0078D4;",
    "peering": "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;startArrow=block;endArrow=block;dashed=1;dashPattern=8 4 1 4;strokeColor=#37475A;strokeWidth=2;fontSize=10;fontColor=#37475A;",
    "mgmt":    "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;dashed=1;dashPattern=3 3;strokeColor=#8661C5;strokeWidth=2;fontSize=10;fontColor=#8661C5;",
}

_icon_cache = {}
def icon_uri(slug):
    if slug not in _icon_cache:
        with open(os.path.join(ICONS, slug + ".svg"), "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        _icon_cache[slug] = "data:image/svg+xml," + b64
    return _icon_cache[slug]

def L(label):  # newline for html labels
    return html.escape(label).replace("\n", "&#10;")

# ── the design tree (mirrors radical-systems.d2). leaf = has 'icon'. -----------
def N(id, label, cls, icon=None, cols=1, children=None):
    return dict(id=id, label=label, cls=cls, icon=icon, cols=cols, children=children or [])

TREE = [
    N("actors", "Users & Identity", "group", cols=1, children=[
        N("users", "Tenant Users\nB2B guests", "svc", "users"),
        N("devs", "RADical Developers", "svc", "users"),
        N("entra", "Microsoft Entra ID\nGoogle OIDC", "svc", "entra"),
    ]),
    N("sub_lz", "SUBSCRIPTION · Landing Zone", "sub", cols=1, children=[
        N("edge", "Global edge services", "group", cols=3, children=[
            N("fd", "Front Door Std\n+ WAF", "svc", "frontdoor"),
            N("avd", "AVD control plane", "svc", "avd"),
            N("devops", "Azure DevOps\nPipelines", "svc", "devops"),
        ]),
        N("rg_hub", "RG · rg-hub", "rg", cols=1, children=[
            N("vnet_hub", "Hub VNet", "vnet", cols=3, children=[
                N("snet_bastion", "AzureBastionSubnet", "subnet", cols=1, children=[
                    N("bastion", "Azure Bastion", "svc", "bastion")]),
                N("snet_gw", "GatewaySubnet", "subnet", cols=1, children=[
                    N("vgw", "VNet Gateway", "svc", "vnetgw")]),
                N("snet_fw", "AzureFirewallSubnet\n(Phase 3)", "subnet", cols=1, children=[
                    N("fw", "Azure Firewall", "svc", "firewall")]),
            ]),
        ]),
        N("govern", "Governance & security", "group", cols=2, children=[
            N("defender", "Defender for Cloud", "svc", "defender"),
            N("policy", "Azure Policy", "svc", "policy"),
        ]),
    ]),
    N("sub_prod", "SUBSCRIPTION · Production", "sub", cols=1, children=[
        N("rg_prod", "RG · rg-prod", "rg", cols=1, children=[
            N("vnet_spoke", "Production Spoke VNet", "vnet", cols=1, children=[
                N("snet_pres", "Presentation Subnet /26 · AVD host pool", "subnet", cols=4, children=[
                    N("sh", "AVD SH 01\nWin 11 24H2", "svc", "avd"),
                    N("sh2", "AVD SH 02\nzoned", "svc", "avd"),
                    N("sh3", "AVD SH 03\nzoned", "svc", "avd"),
                    N("sh4", "AVD SH 04\nzoned", "svc", "avd"),
                ]),
                N("snet_web", "Web/App Subnet /23 · ACA", "subnet", cols=5, children=[
                    N("aca", "Container Apps\nEnvironment", "svc", "containerapps"),
                    N("smweb", "Spaceman Web", "svc", "containerapps"),
                    N("smshop", "Spaceman Shop", "svc", "containerapps"),
                    N("smops", "Spaceman Ops", "svc", "containerapps"),
                    N("smlink", "Spaceman Link", "svc", "containerapps"),
                ]),
                N("snet_mw", "Middleware Subnet /24 · Spaceman Hub", "subnet", cols=3, children=[
                    N("hubvm", "Hub 01\nWindows IaaS", "svc", "vm"),
                    N("hubvm2", "Hub 02\nzoned", "svc", "vm"),
                    N("hubvm3", "Hub 03\nzoned", "svc", "vm"),
                ]),
                N("snet_db", "Database Subnet /24 · SQL Anywhere 17", "subnet", cols=3, children=[
                    N("sqlvm", "DB 01\nUbuntu IaaS", "svc", "vm"),
                    N("sqlvm2", "DB 02\nzoned", "svc", "vm"),
                    N("sqlvm3", "DB 03\nzoned", "svc", "vm"),
                ]),
                N("snet_pe", "Private Endpoint Subnet /27", "subnet", cols=6, children=[
                    N("pe_acr", "PE · Registry", "svc", "privateendpoint"),
                    N("pe_kv", "PE · Key Vault", "svc", "privateendpoint"),
                    N("pe_blob", "PE · Blob", "svc", "privateendpoint"),
                    N("pe_files", "PE · Files", "svc", "privateendpoint"),
                    N("pe_cos", "PE · Cosmos", "svc", "privateendpoint"),
                    N("pdns", "Private DNS Zones", "svc", "privatedns"),
                ]),
            ]),
            N("natgw", "NAT Gateway\nfixed outbound IP", "svc", "natgw"),
        ]),
    ]),
    N("right", "PaaS & Operations", "group", cols=1, children=[
        N("paas", "PaaS · via Private Endpoints", "group", cols=1, children=[
            N("acr", "Container Registry", "svc", "acr"),
            N("kv", "Key Vault", "svc", "keyvault"),
            N("blob", "Blob Storage\n(was AWS S3)", "svc", "storage"),
            N("files", "Azure Files\nFSLogix", "svc", "files"),
            N("cosmos", "Cosmos DB\nsessions", "svc", "cosmos"),
        ]),
        N("law", "Log Analytics\n+ Azure Monitor", "svc", "loganalytics"),
        N("rsv", "Recovery Vault\nGRS · ASR to UK West", "svc", "recovery"),
        N("external", "External Services\nStripe · GoCardless · Graph", "svc", "internet"),
    ]),
]

EDGES = [  # (src_path, dst_path, class, label)
    ("actors.users", "actors.entra", "ingress", "authenticate"),
    ("actors.users", "sub_lz.edge.fd", "ingress", "HTTPS 443"),
    ("actors.users", "sub_lz.edge.avd", "ingress", "Windows App · SSO"),
    ("sub_lz.edge.fd", "sub_prod.rg_prod.vnet_spoke.snet_web.aca", "ingress", "HTTPS 443"),
    ("sub_lz.edge.avd", "sub_prod.rg_prod.vnet_spoke.snet_pres.sh", "ingress", "session broker"),
    ("sub_prod.rg_prod.vnet_spoke.snet_web.aca", "sub_prod.rg_prod.vnet_spoke.snet_mw.hubvm", "sync", "TCP 2638"),
    ("sub_prod.rg_prod.vnet_spoke.snet_pres.sh", "sub_prod.rg_prod.vnet_spoke.snet_mw.hubvm", "sync", "TCP 2638"),
    ("sub_prod.rg_prod.vnet_spoke.snet_mw.hubvm", "sub_prod.rg_prod.vnet_spoke.snet_db.sqlvm", "sync", "SQL Anywhere"),
    ("sub_prod.rg_prod.vnet_spoke.snet_web.aca", "sub_prod.rg_prod.vnet_spoke.snet_pe.pe_blob", "pe", "customer files"),
    ("sub_prod.rg_prod.vnet_spoke.snet_web.aca", "sub_prod.rg_prod.vnet_spoke.snet_pe.pe_cos", "pe", "TCP 10255"),
    ("sub_prod.rg_prod.vnet_spoke.snet_web.aca", "sub_prod.rg_prod.vnet_spoke.snet_pe.pe_acr", "pe", "image pull"),
    ("sub_prod.rg_prod.vnet_spoke.snet_pres.sh", "sub_prod.rg_prod.vnet_spoke.snet_pe.pe_files", "pe", "SMB 445"),
    ("sub_prod.rg_prod.vnet_spoke.snet_mw.hubvm", "sub_prod.rg_prod.vnet_spoke.snet_pe.pe_kv", "pe", "secrets"),
    ("sub_prod.rg_prod.vnet_spoke.snet_pe", "right.paas", "pe", "Azure Private Link"),
    ("sub_lz.rg_hub.vnet_hub", "sub_prod.rg_prod.vnet_spoke", "peering", "VNet peering"),
    ("sub_prod.rg_prod.vnet_spoke.snet_mw.hubvm", "sub_prod.rg_prod.natgw", "egress", "outbound"),
    ("sub_prod.rg_prod.natgw", "right.external", "egress", "fixed IP · allowlisted"),
    ("actors.devs", "sub_lz.edge.devops", "devops", "commit · PR"),
    ("sub_lz.edge.devops", "right.paas.acr", "devops", "build · push"),
    ("sub_lz.edge.devops", "sub_prod.rg_prod.vnet_spoke.snet_web.aca", "devops", "Terraform deploy"),
    ("sub_prod.rg_prod.vnet_spoke.snet_mw.hubvm", "right.rsv", "mgmt", "daily full + 15-min log"),
    ("sub_prod.rg_prod.vnet_spoke.snet_db.sqlvm", "right.rsv", "mgmt", "ASR replication"),
    ("sub_prod.rg_prod.vnet_spoke.snet_web.aca", "right.law", "mgmt", "diagnostics"),
    ("sub_lz.govern.defender", "sub_prod", "mgmt", "posture + threat detection"),
    ("sub_lz.rg_hub.vnet_hub.snet_bastion.bastion", "sub_prod.rg_prod.vnet_spoke.snet_mw.hubvm", "mgmt", "RDP/SSH admin"),
]

# ── layout: uniform-cell grid per container ------------------------------------
LEAF_W = LEAF_H = 74
COL_GAP, ROW_GAP = 46, 60
HEADER, PAD, LABEL_ROOM = 34, 18, 30

def layout(node):
    if not node["children"]:
        node["w"], node["h"] = LEAF_W, LEAF_H
        return
    for c in node["children"]:
        layout(c)
    cols = node["cols"]
    rows = (len(node["children"]) + cols - 1) // cols
    cell_w = max(c["w"] for c in node["children"])
    cell_h = max(c["h"] for c in node["children"])
    for i, c in enumerate(node["children"]):
        r, k = divmod(i, cols)
        c["rx"] = PAD + k * (cell_w + COL_GAP) + (cell_w - c["w"]) / 2
        c["ry"] = HEADER + PAD + r * (cell_h + ROW_GAP)
    node["w"] = PAD * 2 + cols * cell_w + (cols - 1) * COL_GAP
    node["h"] = HEADER + PAD + rows * cell_h + (rows - 1) * ROW_GAP + LABEL_ROOM

for col in TREE:
    layout(col)

# place the four top-level columns side by side, aligned to the top
TOP, COLUMN_GAP, LEFT = 130, 70, 40
x = LEFT
for col in TREE:
    col["rx"], col["ry"] = x, TOP
    x += col["w"] + COLUMN_GAP
total_w = x
total_h = TOP + max(col["h"] for col in TREE) + 60

# ── emit mxGraph XML -----------------------------------------------------------
cells, id_of = [], {}
def emit(node, parent_id, path):
    fid = ".".join(path + [node["id"]])
    id_of[fid] = fid
    if node["icon"]:
        style = LEAF_STYLE + icon_uri(node["icon"])
    else:
        style = CONTAINER_STYLE[node["cls"]] + "container=1;collapsible=0;"
    cells.append(
        f'        <mxCell id="{html.escape(fid)}" value="{L(node["label"])}" style="{style}" vertex="1" parent="{html.escape(parent_id)}">\n'
        f'          <mxGeometry x="{node["rx"]:.0f}" y="{node["ry"]:.0f}" width="{node["w"]:.0f}" height="{node["h"]:.0f}" as="geometry" />\n'
        f'        </mxCell>')
    for c in node["children"]:
        emit(c, fid, path + [node["id"]])

for col in TREE:
    emit(col, "1", [])

# titleblock (plain text shape — survives PNG export, per azure.d2 note)
cells.append(
    f'        <mxCell id="title" value="{L("RADical Systems Ltd — Azure Target-State Architecture (UK South)&#10;Rev 2 · 2026-07-19 · Climb Global Services")}" '
    f'style="text;html=1;align=center;verticalAlign=middle;fontSize=20;fontStyle=1;fontColor=#37475A;whiteSpace=wrap;" vertex="1" parent="1">\n'
    f'          <mxGeometry x="{LEFT}" y="30" width="{total_w-LEFT-40:.0f}" height="60" as="geometry" />\n'
    f'        </mxCell>')

# legend (bottom-left): a titled box with one colour-coded line + label per class
legend_keys = [
    ("ingress", "user / app inflow"), ("sync", "internal service call"),
    ("devops", "DevOps / CI-CD"), ("egress", "internet egress"),
    ("pe", "private endpoint"), ("peering", "VNet peering"),
    ("mgmt", "management / backup"),
]
lx, lw = LEFT, 300
lh = 26 + len(legend_keys) * 22 + 10
ly = total_h - lh - 30
cells.append(
    f'        <mxCell id="legend" value="{L("Legend")}" style="rounded=1;arcSize=4;strokeColor=#90A2BC;fillColor=#FFFFFF;fontSize=12;fontStyle=1;verticalAlign=top;align=left;spacingLeft=10;spacingTop=6;html=1;" vertex="1" parent="1">\n'
    f'          <mxGeometry x="{lx}" y="{ly:.0f}" width="{lw}" height="{lh}" as="geometry" />\n'
    f'        </mxCell>')
for i, (cls, text) in enumerate(legend_keys):
    row_y = 28 + i * 22
    st = EDGE_STYLE[cls]
    stroke = [p for p in st.split(";") if p.startswith("strokeColor")][0].split("=")[1]
    dashed = "dashed=1;" + [p for p in st.split(";") if p.startswith("dashPattern")][0] + ";" if "dashed=1" in st else ""
    line_style = f"shape=line;strokeColor={stroke};strokeWidth=2;{dashed}html=1;"
    cells.append(
        f'        <mxCell id="lk_{cls}_line" value="" style="{line_style}" vertex="1" parent="legend">\n'
        f'          <mxGeometry x="12" y="{row_y}" width="46" height="10" as="geometry" />\n'
        f'        </mxCell>')
    cells.append(
        f'        <mxCell id="lk_{cls}_txt" value="{L(text)}" style="text;html=1;align=left;verticalAlign=middle;fontSize=11;fontColor=#323130;" vertex="1" parent="legend">\n'
        f'          <mxGeometry x="66" y="{row_y-6}" width="{lw-80}" height="20" as="geometry" />\n'
        f'        </mxCell>')

# edges
for i, (s, d, cls, label) in enumerate(EDGES):
    if s not in id_of or d not in id_of:
        raise SystemExit(f"edge endpoint missing: {s} -> {d}")
    cells.append(
        f'        <mxCell id="e{i}" value="{L(label)}" style="{EDGE_STYLE[cls]}" edge="1" parent="1" source="{html.escape(s)}" target="{html.escape(d)}">\n'
        f'          <mxGeometry relative="1" as="geometry" />\n'
        f'        </mxCell>')

xml = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<mxfile host="Diagrammer" type="device">\n'
    '  <diagram id="radical-systems" name="Target State">\n'
    f'    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{total_w+80:.0f}" pageHeight="{total_h+80:.0f}" math="0" shadow="0">\n'
    '      <root>\n'
    '        <mxCell id="0" />\n'
    '        <mxCell id="1" parent="0" />\n'
    + "\n".join(cells) + "\n"
    '      </root>\n'
    '    </mxGraphModel>\n'
    '  </diagram>\n'
    '</mxfile>\n'
)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(xml)
print(f"wrote {OUT}  ({len(xml)//1024} KB, {len(cells)} cells, {len(EDGES)} edges)")

# ── SVG preview (my own render, NOT draw.io's router) --------------------------
# Lets you eyeball the LOOK (icons, house styles, legend) without draw.io.
# Edges are drawn as simple orthogonal elbows; draw.io's obstacle-avoiding router
# is what tidies them once opened in the container.
SVG_FILL = {"sub": "#F2F5F8", "rg": "#F8FBFE", "vnet": "#E4F0FB", "subnet": "#FAFBFD", "group": "#FCFCFC"}
SVG_STROKE = {"sub": "#37475A", "rg": "#0078D4", "vnet": "#0E70C0", "subnet": "#90A2BC", "group": "#8A8886"}
SVG_SW = {"sub": 3, "rg": 2, "vnet": 2, "subnet": 1, "group": 1}
SVG_DASH = {"rg": "6 4", "group": "1 3"}
SVG_EDGE = {"ingress": ("#0078D4", None), "sync": ("#37475A", None), "devops": ("#D83B01", None),
            "egress": ("#C42B1C", None), "pe": ("#0078D4", "3 3"), "peering": ("#37475A", "8 4 1 4"),
            "mgmt": ("#8661C5", "3 3")}

abs_pos, svg = {}, []
def absolve(node, ox, oy):
    ax, ay = ox + node["rx"], oy + node["ry"]
    fid = node.get("_fid")
    abs_pos[fid] = (ax, ay, node["w"], node["h"])
    for c in node["children"]:
        absolve(c, ax, ay)

def tag(node, path):
    node["_fid"] = ".".join(path + [node["id"]])
    for c in node["children"]:
        tag(c, path + [node["id"]])
for col in TREE:
    tag(col, [])
    absolve(col, 0, 0)

def svg_esc(s):
    return html.escape(s)

def draw(node):
    ax, ay, w, h = abs_pos[node["_fid"]]
    if node["icon"]:
        with open(os.path.join(ICONS, node["icon"] + ".svg"), "rb") as f:
            uri = "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode("ascii")
        svg.append(f'<image x="{ax:.0f}" y="{ay:.0f}" width="74" height="74" href="{uri}"/>')
        lines = node["label"].split("\n")
        for j, ln in enumerate(lines):
            svg.append(f'<text x="{ax+37:.0f}" y="{ay+86+j*12:.0f}" font-size="10" text-anchor="middle" fill="#323130">{svg_esc(ln)}</text>')
    else:
        dash = SVG_DASH.get(node["cls"])
        da = f' stroke-dasharray="{dash}"' if dash else ""
        svg.append(f'<rect x="{ax:.0f}" y="{ay:.0f}" width="{w:.0f}" height="{h:.0f}" rx="8" '
                   f'fill="{SVG_FILL[node["cls"]]}" stroke="{SVG_STROKE[node["cls"]]}" stroke-width="{SVG_SW[node["cls"]]}"{da}/>')
        svg.append(f'<text x="{ax+12:.0f}" y="{ay+20:.0f}" font-size="{13 if node["cls"] in ("sub","rg","vnet") else 12}" '
                   f'font-weight="bold" fill="{SVG_STROKE[node["cls"]]}">{svg_esc(node["label"])}</text>')
        for c in node["children"]:
            draw(c)
for col in TREE:
    draw(col)

# edges as orthogonal elbows (H→V→H through the horizontal midpoint)
edge_svg = []
for s, d, cls, label in EDGES:
    sx, sy, sw, sh = abs_pos[s]; tx, ty, tw, th = abs_pos[d]
    p1 = (sx + sw / 2, sy + sh / 2); p2 = (tx + tw / 2, ty + th / 2)
    mx = (p1[0] + p2[0]) / 2
    col, dash = SVG_EDGE[cls]
    da = f' stroke-dasharray="{dash}"' if dash else ""
    pts = f"{p1[0]:.0f},{p1[1]:.0f} {mx:.0f},{p1[1]:.0f} {mx:.0f},{p2[1]:.0f} {p2[0]:.0f},{p2[1]:.0f}"
    edge_svg.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.6" opacity="0.55"{da}/>')

# legend + title
leg = []
leg.append(f'<text x="{LEFT}" y="60" font-size="22" font-weight="bold" fill="#37475A">RADical Systems Ltd — Azure Target-State Architecture (UK South)</text>')
leg.append(f'<text x="{LEFT}" y="82" font-size="13" fill="#605E5C">Rev 2 · 2026-07-19 · Climb Global Services</text>')
lyy = total_h - lh - 30
leg.append(f'<rect x="{LEFT}" y="{lyy:.0f}" width="300" height="{lh}" rx="4" fill="#FFFFFF" stroke="#90A2BC"/>')
leg.append(f'<text x="{LEFT+10}" y="{lyy+20:.0f}" font-size="12" font-weight="bold" fill="#323130">Legend</text>')
for i, (cls, text) in enumerate(legend_keys):
    ry = lyy + 34 + i * 22
    col, dash = SVG_EDGE[cls]
    da = f' stroke-dasharray="{dash}"' if dash else ""
    leg.append(f'<line x1="{LEFT+12}" y1="{ry:.0f}" x2="{LEFT+58}" y2="{ry:.0f}" stroke="{col}" stroke-width="2"{da}/>')
    leg.append(f'<text x="{LEFT+66}" y="{ry+4:.0f}" font-size="11" fill="#323130">{svg_esc(text)}</text>')

svg_doc = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w+80:.0f}" height="{total_h+80:.0f}" '
    f'viewBox="0 0 {total_w+80:.0f} {total_h+80:.0f}" font-family="Segoe UI, Arial, sans-serif">\n'
    f'<rect width="100%" height="100%" fill="#FFFFFF"/>\n'
    + "\n".join(edge_svg) + "\n" + "\n".join(svg) + "\n" + "\n".join(leg) + "\n</svg>\n"
)
SVG_OUT = os.path.join(ROOT, "designs/radical-systems/radical-systems-preview.svg")
with open(SVG_OUT, "w", encoding="utf-8") as f:
    f.write(svg_doc)
print(f"wrote {SVG_OUT}  ({len(svg_doc)//1024} KB)")
