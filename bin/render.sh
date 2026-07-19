#!/usr/bin/env bash
# render.sh - design.d2 -> design.svg + design.png (single ELK render).
# Thin wrapper around bin/render.py so the pipeline is identical on every OS.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/bin/render.py" "$@"
