#!/usr/bin/env python3
"""
verify.py - repository self-check. Confirms the structure, the icon manifest,
every icon reference and style import in every .d2, that the linter runs, and
which external binaries are present.

Run after any restructure, icon refresh, or path change:
    python bin/verify.py
"""
import os, re, json, subprocess, sys
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok = True

def check(label, cond, detail=""):
    global ok
    print(("PASS " if cond else "FAIL ") + label + (("  " + detail) if detail else ""))
    if not cond: ok = False

# 1. structure
for p in ["README.md","LICENCE-NOTES.md",".gitignore","setup.sh","setup.ps1",
          "bin/lint.py","bin/optimize.py","bin/render.py","bin/render.sh","bin/build_manifest.py",
          "styles/azure.d2","templates/target-state.d2","templates/phase.d2",
          "bin/contract.py","bin/verify.py",
          "skill/PROMPT.md","skill/style-contract.md","skill/icon-index.md","skill/critic.md",
          "docs/azure-diagram-guidelines.md","docs/reference-review.md",
          "icons/manifest.json","icons/entra.svg",
          "designs/_example/example.d2","evals/bad-diagram.d2"]:
    check("exists " + p, os.path.exists(os.path.join(R,p)))

# 2. every slug in the manifest has a flat svg
man = json.load(open(os.path.join(R,"icons","manifest.json"), encoding="utf-8"))["icons"]
missing = [s for s in man if not os.path.exists(os.path.join(R,"icons",s+".svg"))]
check("all manifest slugs have icons/<slug>.svg", not missing, str(missing))

# 3. flat copies are byte-identical to the official source
import filecmp
bad = [s for s,v in man.items()
       if not filecmp.cmp(os.path.join(R,v["source"].replace("/",os.sep)),
                          os.path.join(R,"icons",s+".svg"), shallow=False)]
check("icons copied unmodified", not bad, str(bad))

# 4. every icon: reference in every .d2 resolves
refs, badrefs = 0, []
for dp,_,fs in os.walk(R):
    # evals/ holds deliberately-broken fixtures; icons/ holds the source set
    if os.sep+"icons" in dp or os.sep+"evals" in dp: continue
    for f in fs:
        if not f.endswith(".d2"): continue
        src = open(os.path.join(dp,f), encoding="utf-8").read()
        for m in re.findall(r"icon:\s*\./icons/([\w\-]+)\.svg", src):
            refs += 1
            if not os.path.exists(os.path.join(R,"icons",m+".svg")):
                badrefs.append((f,m))
check(f"all {refs} icon references resolve", not badrefs, str(badrefs))

# 5. style imports resolve
badimp = []
for dp,_,fs in os.walk(R):
    if os.sep+"evals" in dp: continue
    for f in fs:
        if not f.endswith(".d2"): continue
        p = os.path.join(dp,f)
        body = "\n".join(l for l in open(p, encoding="utf-8").read().splitlines()
                         if not l.lstrip().startswith("#"))
        for m in re.findall(r"\.\.\.@([^\s#]+)", body):
            t = m if m.endswith(".d2") else m + ".d2"
            if not os.path.exists(os.path.normpath(os.path.join(dp,t))):
                badimp.append((os.path.relpath(p,R), m))
check("all style imports resolve", not badimp, str(badimp))

# 6. lint.py still runs on the existing sample svg
svg = os.path.join(R,"examples","azure-d2-sample.svg")
r = subprocess.run([sys.executable, os.path.join(R,"bin","lint.py"), svg, "--json"],
                   capture_output=True, text=True)
try:
    score = json.loads(r.stdout)["score"]
except Exception:
    score = None
check("lint.py runs", score is not None, f"score={score}  {r.stderr.strip()[:150]}")

# 7. optimize.py imports cleanly from anywhere
r = subprocess.run([sys.executable, "-c",
                    "import sys; sys.argv=['optimize.py']; exec(open(r'%s').read())" %
                    os.path.join(R,"bin","optimize.py").replace("\\","\\\\")],
                   capture_output=True, text=True, cwd=os.path.expanduser("~"))
check("optimize.py imports lint from any cwd", "ModuleNotFoundError" not in r.stderr,
      r.stderr.strip()[:150])

# 8. the guideline contract: deliverables pass, the fixture fails
r = subprocess.run([sys.executable, os.path.join(R,"bin","contract.py"), "--all"],
                   capture_output=True, text=True)
check("contract.py: all deliverable .d2 pass", r.returncode == 0,
      r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[:150])
fixture = os.path.join(R,"evals","bad-diagram.d2")
r = subprocess.run([sys.executable, os.path.join(R,"bin","contract.py"), fixture],
                   capture_output=True, text=True)
rules = set(re.findall(r"\[(R\d+)-", r.stdout))
expected = {"R2","R3","R4","R5","R6","R8","R10","R12","R13","R14"}
check("contract.py: fixture trips every live rule", r.returncode == 1 and expected <= rules,
      "missing " + str(sorted(expected - rules)) if expected - rules else "")
retired = {"R1","R7","R9","R11"} & rules
check("contract.py: retired rules stay retired", not retired, str(sorted(retired)))
r = subprocess.run([sys.executable, os.path.join(R,"bin","contract.py"),
                    os.path.join(R,"evals","incomplete-legend.d2")],
                   capture_output=True, text=True)
check("contract.py: catches an incomplete legend",
      "R8-legend-incomplete" in r.stdout, r.stdout.strip()[:120])

# 9. toolchain
sys.path.insert(0, os.path.join(R,"bin"))
import d2paths
d2paths.ensure_path()
have = {}
for t in ("d2","resvg","rsvg-convert"):
    have[t] = any(os.path.exists(os.path.join(p,t+e))
                  for p in os.environ.get("PATH","").split(os.pathsep) for e in ("",".exe",".cmd"))
    print(("PASS " if have[t] else "TODO ") + f"toolchain: {t}"
          + ("" if have[t] else "  not installed"))

# 10. end-to-end: the example design actually renders, and the PNG carries the
#     title (guards the markdown/foreignObject trap from both directions)
if have["d2"]:
    ex = os.path.join(R,"designs","_example","example.d2")
    r = subprocess.run([sys.executable, os.path.join(R,"bin","render.py"), ex],
                       capture_output=True, text=True)
    svg = os.path.join(R,"designs","_example","example.svg")
    check("end-to-end render", r.returncode == 0 and os.path.exists(svg),
          (r.stdout + r.stderr).strip()[:200])
    if os.path.exists(svg):
        s = open(svg, encoding="utf-8").read()
        check("title survives as SVG text (not foreignObject)",
              "Target-State Architecture" in s and "foreignObject" not in s,
              "title is inside a foreignObject - it will vanish from the PNG")
        check("UTF-8 labels intact", "Â·" not in s, "mojibake in labels")
    if have["resvg"] or have["rsvg-convert"]:
        check("PNG produced", os.path.exists(
            os.path.join(R,"designs","_example","example.png")))

print("\nVERIFY:", "all repo checks passed" if ok else "FAILURES ABOVE")
sys.exit(0 if ok else 1)
