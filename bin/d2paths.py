#!/usr/bin/env python3
"""
d2paths.py - reconcile the authoring convention with how d2 actually resolves
paths.

We author every icon as `icon: ./icons/<slug>.svg`, which is short, uniform, and
checkable no matter where the design lives. But d2 resolves `icon:` relative to
the .d2 FILE (not the working directory), so a design in designs/<customer>/
would look for designs/<customer>/icons/... and fail to bundle.

Rather than push depth-relative icon paths onto whoever writes the diagram, the
render scripts materialise a temporary sibling of the source with every
`./icons/...` rewritten to the correct file-relative path. The temp file lives in
the same directory as the original, so `...@../../styles/azure.d2` imports keep
resolving exactly as before.

Nothing else in the toolchain needs to know: the .d2 you author and the .d2 in
version control keep the clean form.
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_REF = re.compile(r"(icon\s*:\s*)\./icons/([\w\-]+\.svg)")

# Where d2 and the rasterizer end up on a fresh install. A shell opened before
# the install has a stale PATH, so look in the usual places rather than telling
# the user to restart their terminal.
CANDIDATE_DIRS = [
    os.path.join(ROOT, "tools"),                       # setup.ps1 drops resvg here
    r"C:\Program Files\D2",                            # winget / MSI
    r"C:\Program Files (x86)\D2",
    os.path.expanduser(r"~\scoop\shims"),
    os.path.expanduser("~/.cargo/bin"),                # cargo install resvg
    "/usr/local/bin", "/opt/homebrew/bin",
]


def ensure_path():
    """Prepend known install locations to PATH for this process."""
    extra = [d for d in CANDIDATE_DIRS if os.path.isdir(d)]
    if os.name == "nt":
        # pick up anything the installer added since this shell started
        try:
            import winreg
            for root, key in ((winreg.HKEY_LOCAL_MACHINE,
                               r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                              (winreg.HKEY_CURRENT_USER, "Environment")):
                with winreg.OpenKey(root, key) as k:
                    val, _ = winreg.QueryValueEx(k, "Path")
                    extra += [p for p in os.path.expandvars(val).split(os.pathsep) if p]
        except Exception:
            pass
    current = os.environ.get("PATH", "").split(os.pathsep)
    seen, merged = set(), []
    for p in extra + current:
        if p and p not in seen:
            seen.add(p)
            merged.append(p)
    os.environ["PATH"] = os.pathsep.join(merged)


def rewrite_icon_paths(src, d2_dir):
    """Rewrite ./icons/x.svg to a path relative to the .d2 file's directory."""
    rel = os.path.relpath(os.path.join(ROOT, "icons"), d2_dir).replace(os.sep, "/")
    if rel == ".":
        rel = "./icons"          # already at the repo root
    elif not rel.startswith("."):
        rel = "./" + rel
    return ICON_REF.sub(lambda m: f"{m.group(1)}{rel}/{m.group(2)}", src)


def materialise(d2_path, suffix=".__render.d2", extra=None):
    """Write a render-ready sibling of d2_path. Returns its path.

    extra: optional callable(src) -> src applied before the icon rewrite, used by
    the optimizer to inject a layout direction.
    """
    d2_path = os.path.abspath(d2_path)
    d2_dir  = os.path.dirname(d2_path)
    with open(d2_path, encoding="utf-8") as fh:
        src = fh.read()
    if extra:
        src = extra(src)
    src = rewrite_icon_paths(src, d2_dir)
    out = os.path.splitext(d2_path)[0] + suffix
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(src)
    return out


def cleanup(path):
    try:
        os.remove(path)
    except OSError:
        pass
