# setup.ps1 - install the two binaries the pipeline needs and verify the icon set.
# Windows. macOS / Linux: use setup.sh.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

function Have($name) { $null -ne (Get-Command $name -ErrorAction SilentlyContinue) }

$tools = Join-Path $root "tools"

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path","User") + ";" + $tools
}
Refresh-Path

Write-Host "== d2 =="
if (Have "d2") {
    Write-Host "  present: $(d2 --version)"
} elseif (Have "winget") {
    # NOTE: the winget package id is case-sensitive with -e: Terrastruct.D2
    Write-Host "  installing via winget (Terrastruct.D2)..."
    winget install --id Terrastruct.D2 -e --accept-source-agreements --accept-package-agreements
    Refresh-Path
    if (Have "d2") { Write-Host "  installed: $(d2 --version)" }
    else { Write-Warning "  installed, but not on PATH yet - open a NEW terminal and re-run." }
} elseif (Have "scoop") {
    scoop install d2
    Refresh-Path
} else {
    Write-Warning "  d2 not installed and no winget/scoop found."
    Write-Host   "  Download the Windows MSI: https://github.com/terrastruct/d2/releases"
}

Write-Host "== rasterizer (SVG -> PNG) =="
if ((Have "resvg") -or (Have "rsvg-convert")) {
    Write-Host "  present"
} elseif (Have "cargo") {
    Write-Host "  installing resvg via cargo..."
    cargo install resvg
    Refresh-Path
} else {
    # No Rust toolchain: fetch the prebuilt binary into .\tools\ and use it from there.
    Write-Host "  no rasterizer and no cargo - fetching the prebuilt resvg binary..."
    try {
        New-Item -ItemType Directory -Force -Path $tools | Out-Null
        $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/linebender/resvg/releases/latest" `
                                 -Headers @{ "User-Agent" = "diagrammer-setup" }
        $asset = $rel.assets | Where-Object { $_.name -match "win.*(64|amd64).*\.zip$" } | Select-Object -First 1
        if (-not $asset) { throw "no Windows asset in the latest release" }
        $zip = Join-Path $tools $asset.name
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing
        Expand-Archive -Path $zip -DestinationPath $tools -Force
        Remove-Item $zip
        Refresh-Path
        if (Have "resvg") {
            Write-Host "  installed to $tools (this repo adds it to PATH at render time)"
        } else {
            Write-Warning "  downloaded but resvg.exe not found in $tools - unzip it manually."
        }
    } catch {
        Write-Warning "  automatic download failed: $($_.Exception.Message)"
        Write-Host   "  Grab it by hand from https://github.com/linebender/resvg/releases"
        Write-Host   "  and drop resvg.exe into $tools"
        Write-Host   "  SVG still renders without it; only the PNG step is skipped."
    }
}

Write-Host "== python =="
python --version

Write-Host "== icons =="
python "$root\bin\build_manifest.py"

Write-Host "== smoke test =="
python "$root\bin\render.py" "$root\examples\azure-d2-sample.d2"

Write-Host "setup complete."
