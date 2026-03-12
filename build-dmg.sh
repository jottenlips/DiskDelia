#!/bin/bash
set -e

APP_NAME="DiskDelia"
VERSION="1.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
DIST_DIR="$SCRIPT_DIR/dist"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
DMG_NAME="$APP_NAME-$VERSION.dmg"

echo "═══════════════════════════════════════════"
echo "  Building $APP_NAME v$VERSION"
echo "  Hack the Planet."
echo "═══════════════════════════════════════════"
echo ""

# ── Step 1: Install PyInstaller in the venv ──────────────────────────────────
echo "[1/4] Setting up build environment..."
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "  Creating virtualenv..."
    ~/.pyenv/versions/3.11.8/bin/python3.11 -m venv "$SCRIPT_DIR/venv"
fi

source "$SCRIPT_DIR/venv/bin/activate"
pip install pyinstaller --quiet 2>/dev/null
echo "  ✓ PyInstaller ready"

# ── Step 2: Build the .app bundle ────────────────────────────────────────────
echo ""
echo "[2/4] Building .app bundle with PyInstaller..."

# Clean previous builds
rm -rf "$BUILD_DIR" "$DIST_DIR"

pyinstaller \
    --name "$APP_NAME" \
    --onefile \
    --windowed \
    --noconfirm \
    --clean \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR" \
    --specpath "$BUILD_DIR" \
    --add-data "$SCRIPT_DIR/venv/lib/python3.11/lib-dynload/_tkinter.cpython-311-darwin.so:." \
    "$SCRIPT_DIR/storage-app.py" 2>&1 | tail -5

# PyInstaller with --windowed creates .app on macOS
if [ ! -d "$APP_BUNDLE" ]; then
    echo "  PyInstaller didn't create .app, building manually..."

    # Create .app bundle structure manually
    mkdir -p "$APP_BUNDLE/Contents/MacOS"
    mkdir -p "$APP_BUNDLE/Contents/Resources"

    # Move the binary
    if [ -f "$DIST_DIR/$APP_NAME" ]; then
        mv "$DIST_DIR/$APP_NAME" "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
    fi

    # Create Info.plist
    cat > "$APP_BUNDLE/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>com.diskdelia.app</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
PLIST
fi

echo "  ✓ .app bundle created"

# ── Step 3: Create the DMG ───────────────────────────────────────────────────
echo ""
echo "[3/4] Creating DMG installer..."

DMG_TMP="$DIST_DIR/tmp.dmg"
DMG_FINAL="$DIST_DIR/$DMG_NAME"
DMG_STAGING="$DIST_DIR/dmg_staging"

# Clean
rm -rf "$DMG_STAGING" "$DMG_TMP" "$DMG_FINAL"

# Create staging area with app and Applications symlink
mkdir -p "$DMG_STAGING"
cp -R "$APP_BUNDLE" "$DMG_STAGING/"
ln -s /Applications "$DMG_STAGING/Applications"

# Create a read-only DMG
# First create a temporary read-write DMG
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$DMG_STAGING" \
    -ov \
    -format UDRW \
    "$DMG_TMP" \
    -quiet

# Convert to compressed read-only
hdiutil convert "$DMG_TMP" \
    -format UDZO \
    -o "$DMG_FINAL" \
    -quiet

# Cleanup
rm -rf "$DMG_TMP" "$DMG_STAGING"

echo "  ✓ DMG created"

# ── Step 4: Summary ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo "  BUILD COMPLETE"
echo "═══════════════════════════════════════════"
echo ""
echo "  .app → $APP_BUNDLE"
echo "  .dmg → $DMG_FINAL"
echo ""

DMG_SIZE=$(du -sh "$DMG_FINAL" | cut -f1)
echo "  DMG size: $DMG_SIZE"
echo ""
echo "  To test: open \"$DMG_FINAL\""
echo ""
