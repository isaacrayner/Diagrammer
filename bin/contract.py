#!/usr/bin/env python3
"""
contract.py - enforce the Azure diagramming guidelines on a .d2 SOURCE file.

lint.py judges the rendered geometry. This judges the design itself, against
Microsoft's Well-Architected Framework guidance for architecture design diagrams
(https://learn.microsoft.com/azure/well-architected/architect-role/design-diagrams)
and the Azure icon terms (https://learn.microsoft.com/azure/architecture/icons/).

Every rule below maps to a named guideline, so the report tells you which
guideline you broke, not just which line.

Usage:
    python bin/contract.py designs/acme/acme.d2          # human report
    python bin/contract.py designs/acme/acme.d2 --json   # machine-readable
    python bin/contract.py --all                         # every .d2 in the repo

Exit code 0 = clean or warnings only; 1 = at least one ERROR.
"""
import os, re, sys, json, glob

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(ROOT, "icons")

CONTAINER_CLASSES = {"sub", "rg", "vnet", "subnet", "group"}
# the house flow vocabulary, read off the Mitie / RADical reference diagrams
FLOW_CLASSES      = {"ingress", "sync", "devops", "egress", "pe",
                     "peering", "replication", "mgmt"}
STATE_CLASSES     = {"future"}
CHROME_CLASSES    = {"legend", "legendkey", "titleblock"}
KNOWN_CLASSES     = (CONTAINER_CLASSES | FLOW_CLASSES | STATE_CLASSES
                     | CHROME_CLASSES | {"svc"})

# ── diagram types (WAF: layer, don't overload / progressive disclosure) ───────
# Declared in the source as a header comment:  # diagram-type: component
DIAGRAM_TYPES = {
    "context":    "workload as a black box plus external actors",
    "container":  "macro structure and hosting models",
    "component":  "named services with official icons (the ADS default)",
    "network":    "connectivity: CIDRs, peering, egress paths",
    "resilience": "availability and recovery: RPO/RTO, DR pairs",
    "identity":   "identity and access flows",
}

# services that are reached over a private endpoint and must NOT be drawn
# inside a subnet (WAF: "be accurate"). Keyed by icon slug.
PAAS_OVER_PE = {
    "keyvault", "storage", "sqldb", "cosmos", "servicebus", "eventhubs",
    "eventgrid", "redis", "postgres", "mysql", "datalake", "synapse",
    "acr", "appinsights", "loganalytics", "monitor", "apim", "datafactory",
}
# ...unless the design says they are VNet-integrated / delegated-subnet
DELEGATION_HINT = re.compile(r"delegat|vnet[- ]integrat|injected", re.I)


class Finding:
    def __init__(self, level, rule, guideline, line, msg):
        self.level, self.rule, self.guideline, self.line, self.msg = \
            level, rule, guideline, line, msg
    def as_dict(self):
        return {"level": self.level, "rule": self.rule,
                "guideline": self.guideline, "line": self.line, "msg": self.msg}


def _strip_comments(lines):
    """Return (line_no, code) for lines that are not pure comments."""
    out = []
    for i, raw in enumerate(lines, 1):
        if raw.lstrip().startswith("#"):
            continue
        out.append((i, raw.split(" #")[0].rstrip()))
    return out


def _split_legend(code):
    """Return (legend_block_text, everything_else). Brace-matched, so a legend
    containing nested blocks is still separated correctly."""
    legend, rest, depth, inside = [], [], 0, False
    for _, c in code:
        if not inside and re.match(r"^\s*legend\b.*\{", c, re.I):
            inside, depth = True, c.count("{") - c.count("}")
            legend.append(c)
            if depth <= 0:
                inside = False
            continue
        if inside:
            legend.append(c)
            depth += c.count("{") - c.count("}")
            if depth <= 0:
                inside = False
            continue
        rest.append(c)
    return "\n".join(legend), "\n".join(rest)


def check(path):
    src   = open(path, encoding="utf-8").read()
    lines = src.splitlines()
    code  = _strip_comments(lines)
    body  = "\n".join(c for _, c in code)
    f     = []
    add   = lambda *a: f.append(Finding(*a))

    # ── R1  RETIRED ─────────────────────────────────────────────────────────
    # Bidirectional arrows were banned per WAF guidance, but the house style
    # uses them deliberately for genuinely two-way relationships (VNet peering,
    # profile-storage read/write). Retired by decision, 19 July 2026.

    # ── R2  directional arrows only ─────────────────────────────────────────
    # WAF: "Lines without arrows make relationships unclear."
    for n, c in code:
        if re.search(r"^\s*[\w.\"][\w.\" ]*\s--\s", c):
            add("ERROR", "R2-undirected", "Use directional arrows", n,
                "undirected line ('--') - use '->' from client to dependency")

    # ── R3  no inline styling ───────────────────────────────────────────────
    # WAF: "Maintain consistency" + icon terms: don't recolour or distort.
    for n, c in code:
        if re.search(r"\bstyle\s*:", c):
            add("ERROR", "R3-inline-style", "Maintain consistency", n,
                "inline style - use a class: " + ", ".join(sorted(KNOWN_CLASSES)))

    # ── R4  known classes only ──────────────────────────────────────────────
    for n, c in code:
        for cls in re.findall(r"class\s*:\s*([\w, ]+)", c):
            for one in [x.strip() for x in cls.split(",") if x.strip()]:
                if one not in KNOWN_CLASSES:
                    add("ERROR", "R4-unknown-class", "Use standard notations", n,
                        f"unknown class '{one}' - not defined in styles/azure.d2")

    # ── R5  icons: official set only, and they must exist ───────────────────
    # Icon terms: official icons, unmodified, referenced by slug.
    icon_refs = []
    for n, c in code:
        for m in re.finditer(r"icon\s*:\s*(\S+)", c):
            ref = m.group(1).strip().strip(';')
            icon_refs.append((n, ref))
            if not ref.startswith("./icons/"):
                add("ERROR", "R5-icon-path", "Use official icons", n,
                    f"icon '{ref}' - must be ./icons/<slug>.svg from the vendored set")
            elif not os.path.exists(os.path.join(ROOT, ref.replace("./", "").replace("/", os.sep))):
                add("ERROR", "R5-icon-missing", "Use official icons", n,
                    f"icon '{ref}' does not exist - run bin/build_manifest.py")

    # ── R6  every svc node carries an icon and a label ──────────────────────
    # Icon terms: "include the product name somewhere close to the icon."
    for n, c in code:
        if re.search(r"class\s*:\s*svc", c):
            if "icon:" not in c:
                add("ERROR", "R6-svc-no-icon", "Use official icons", n,
                    "svc node without an icon")
            if not re.search(r"^\s*[\w.]+\s*:\s*\S", c):
                add("WARN", "R6-svc-no-label", "Label everything clearly", n,
                    "svc node without a display label")

    # ── R7  RETIRED ─────────────────────────────────────────────────────────
    # The metadata block (title / revision / date / author) is still strongly
    # recommended and every template ships with one, but it is no longer
    # enforced. Retired by decision, 19 July 2026.

    # ── R8  legend must cover every semantic actually used ──────────────────
    # WAF: "If you introduce border or line semantics ... include a compact
    # legend." Upgraded: the legend must have an entry for EACH class in use,
    # not merely exist. This is the rule that makes the colour vocabulary
    # readable rather than decorative.
    legend_body, topology_body = _split_legend(code)
    used   = set(re.findall(r"class\s*:\s*(\w+)", topology_body)) & (FLOW_CLASSES | STATE_CLASSES)
    shown  = set(re.findall(r"class\s*:\s*(\w+)", legend_body))  & (FLOW_CLASSES | STATE_CLASSES)
    if used and not legend_body:
        add("ERROR", "R8-no-legend", "Provide a legend", 0,
            f"line semantics in use ({', '.join(sorted(used))}) but no legend block")
    elif used - shown:
        add("ERROR", "R8-legend-incomplete", "Provide a legend", 0,
            "legend is missing an entry for: " + ", ".join(sorted(used - shown)))

    # ── R9  RETIRED ─────────────────────────────────────────────────────────
    # Unlabelled-connection warnings retired by decision, 19 July 2026. The
    # colour vocabulary now carries the meaning that a label used to.

    # ── R10  accuracy: PaaS-over-private-endpoint must not sit in a subnet ──
    # WAF: "don't depict a PaaS service inside a subnet if it's actually
    # accessed over a private endpoint."
    depth_of_subnet = None
    stack = []
    for n, c in code:
        opens  = c.count("{")
        closes = c.count("}")
        is_subnet = bool(re.search(r"class\s*:\s*subnet", c))
        icon = re.search(r"icon\s*:\s*\./icons/([\w\-]+)\.svg", c)
        inside_subnet = any(stack)
        if icon and inside_subnet and icon.group(1) in PAAS_OVER_PE \
           and not DELEGATION_HINT.search(c):
            add("ERROR", "R10-paas-in-subnet", "Be accurate", n,
                f"'{icon.group(1)}' is reached over a private endpoint - draw it "
                "outside the VNet with a 'pe' connection, or note the delegation")
        for _ in range(opens):
            stack.append(is_subnet)
        for _ in range(closes):
            if stack:
                stack.pop()

    # ── R11  RETIRED ────────────────────────────────────────────────────────
    # Node-count and subnet-density warnings retired by decision, 19 July 2026.
    # Layering is now enforced properly by R13 (declared diagram type) rather
    # than guessed at from a node count.

    # ── R13  declared diagram type, and what belongs at that layer ──────────
    # WAF: "Layer diagrams ... progressive disclosure." A diagram that does not
    # say which layer it is cannot be checked against that layer.
    m = re.search(r"^#\s*diagram-type\s*:\s*([\w-]+)", src, re.M | re.I)
    if not m:
        add("ERROR", "R13-no-type", "Layer, don't overload", 0,
            "no '# diagram-type: <type>' header - one of: "
            + ", ".join(sorted(DIAGRAM_TYPES)))
    else:
        dtype = m.group(1).lower()
        if dtype not in DIAGRAM_TYPES:
            add("ERROR", "R13-bad-type", "Layer, don't overload", 0,
                f"unknown diagram-type '{dtype}' - one of: "
                + ", ".join(sorted(DIAGRAM_TYPES)))
        else:
            has_subnet = bool(re.search(r"class\s*:\s*subnet", body))
            has_vnet   = bool(re.search(r"class\s*:\s*vnet", body))
            has_svc    = bool(re.search(r"class\s*:\s*svc", body))
            if dtype == "context" and (has_subnet or has_vnet):
                add("ERROR", "R13-layer-mismatch", "Layer, don't overload", 0,
                    "a context diagram shows the workload as a black box - move "
                    "VNet/subnet detail to a container, component, or network diagram")
            if dtype == "container" and has_subnet:
                add("ERROR", "R13-layer-mismatch", "Layer, don't overload", 0,
                    "a container diagram shows hosting models, not subnets - "
                    "move subnet detail to a component or network diagram")
            # templates are skeletons: their topology is commented out, so the
            # "must contain X" completeness checks don't apply to them.
            skeleton = (os.sep + "templates" + os.sep) in os.path.abspath(path)
            if dtype == "component" and not has_svc and not skeleton:
                add("ERROR", "R13-layer-mismatch", "Layer, don't overload", 0,
                    "a component diagram must name the services (svc nodes with "
                    "official icons)")
            if dtype == "network" and not skeleton:
                if not re.search(r"/\d{1,2}\b", body):
                    add("ERROR", "R13-layer-mismatch", "Layer, don't overload", 0,
                        "a network diagram must carry CIDRs on its VNets and subnets")
                if not re.search(r"class\s*:\s*(peering|egress)", body):
                    add("WARN", "R13-layer-thin", "Layer, don't overload", 0,
                        "a network diagram usually shows peering and/or egress paths")
            if dtype == "resilience" and not skeleton \
               and not re.search(r"\bRPO\b|\bRTO\b", body, re.I):
                add("ERROR", "R13-layer-mismatch", "Layer, don't overload", 0,
                    "a resilience diagram must annotate RPO/RTO on the recovery path")
            if dtype == "identity" and not re.search(r"icons/entra", body):
                add("WARN", "R13-layer-thin", "Layer, don't overload", 0,
                    "an identity diagram usually includes the Entra ID tenant")

    # ── R14  no markdown blocks ─────────────────────────────────────────────
    # Learned the hard way, 19 July 2026: D2 renders |md| as an HTML
    # <foreignObject>. resvg cannot rasterise that, so a markdown title survives
    # in the SVG and silently vanishes from the PNG that goes into the Word
    # document. Plain text shapes render as real SVG text and survive both.
    for n, c in code:
        if re.search(r"\|\s*md\b", c):
            add("ERROR", "R14-markdown-block", "Include metadata", n,
                "markdown block will not rasterise to PNG (resvg cannot render "
                "foreignObject) - use a quoted text label with \\n instead")

    # ── R12  style import present ───────────────────────────────────────────
    if not re.search(r"\.\.\.@.*styles/azure\.d2", body):
        add("ERROR", "R12-no-style-import", "Maintain consistency", 0,
            "missing '...@<path>/styles/azure.d2' import - the shared visual language")

    return f


def report(path, findings, as_json=False):
    if as_json:
        print(json.dumps({"file": os.path.relpath(path, ROOT),
                          "findings": [x.as_dict() for x in findings]}, indent=2))
        return
    rel = os.path.relpath(path, ROOT)
    errs = [x for x in findings if x.level == "ERROR"]
    warns = [x for x in findings if x.level == "WARN"]
    status = "PASS" if not errs else "FAIL"
    print(f"{status}  {rel}  ({len(errs)} error, {len(warns)} warning)")
    for x in sorted(findings, key=lambda x: (x.level != "ERROR", x.line)):
        loc = f"L{x.line}" if x.line else "  -"
        print(f"   {x.level:5} {loc:>5}  [{x.rule}]  {x.msg}")
        print(f"                   guideline: {x.guideline}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    if "--all" in sys.argv:
        # examples/ holds pre-contract demos of the raw palette and styles/ is
        # the class library itself; neither is a deliverable. Lint them by name
        # if you want to.
        skip = (os.sep + "examples" + os.sep, os.sep + "styles" + os.sep,
                os.sep + "evals" + os.sep)   # evals hold deliberately-bad fixtures
        targets = [p for p in glob.glob(os.path.join(ROOT, "**", "*.d2"), recursive=True)
                   if ".opt_" not in p and not p.endswith(".optimized.d2")
                   and not any(s in p for s in skip)]
    elif args:
        targets = [os.path.abspath(a) for a in args]
    else:
        sys.exit("usage: python bin/contract.py <file.d2> [--json] | --all")

    failed = False
    for t in sorted(targets):
        fs = check(t)
        report(t, fs, as_json)
        if any(x.level == "ERROR" for x in fs):
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
