#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$ROOT_DIR/dist"

echo "=== wallpy macOS DMG builder ==="

cd "$ROOT_DIR"

# ── PyInstaller ────────────────────────────────────────────────────────────────
echo "Installing PyInstaller..."
pip3 install --quiet pyinstaller

# ── .app bundle ───────────────────────────────────────────────────────────────
echo "Building wallpy.app..."
pyinstaller --clean packaging/macos/wallpy.spec

# ── DMG ───────────────────────────────────────────────────────────────────────
echo "Creating wallpy.dmg..."

STAGING="$DIST_DIR/dmg"
rm -rf "$STAGING"
mkdir -p "$STAGING"

cp -r "$DIST_DIR/wallpy.app" "$STAGING/"
ln -sf /Applications "$STAGING/Applications"

hdiutil create \
    -volname "wallpy" \
    -srcfolder "$STAGING" \
    -ov \
    -format UDZO \
    "$DIST_DIR/wallpy.dmg"

rm -rf "$STAGING"

echo ""
echo "=== Done! ==="
echo "DMG: $DIST_DIR/wallpy.dmg"
