#!/bin/bash
# Build Mythica Pipeline.app using PyInstaller
# Run this from the project root after setup.command has been run.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/.mythica_venv"

echo ""
echo "=== Building Mythica Pipeline.app ==="
echo ""

source "$VENV/bin/activate"

cd "$SCRIPT_DIR"
pyinstaller --clean --noconfirm Mythica.spec

echo ""
echo "Done! Your app is at:"
echo "  $SCRIPT_DIR/dist/Mythica Pipeline.app"
echo ""
echo "You can drag it to your Applications folder."
