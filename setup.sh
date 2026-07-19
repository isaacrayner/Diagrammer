#!/usr/bin/env bash
# setup.sh - install the two binaries the pipeline needs and verify the icon set.
# macOS / Linux. Windows: use setup.ps1.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== d2 =="
if command -v d2 >/dev/null 2>&1; then
  echo "  present: $(d2 --version)"
else
  echo "  installing..."
  curl -fsSL https://d2lang.com/install.sh | sh -s --
fi

echo "== rasterizer (SVG -> PNG) =="
if command -v resvg >/dev/null 2>&1 || command -v rsvg-convert >/dev/null 2>&1; then
  echo "  present"
else
  echo "  none found. Install one of:"
  echo "    cargo install resvg          # any platform"
  echo "    brew install librsvg         # macOS"
  echo "    sudo apt install librsvg2-bin  # Debian/Ubuntu"
fi

echo "== python =="
python3 --version

echo "== icons =="
python3 "$ROOT/bin/build_manifest.py"

echo "== smoke test =="
python3 "$ROOT/bin/render.py" "$ROOT/examples/azure-d2-sample.d2" || true
echo "setup complete."
