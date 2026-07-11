#!/bin/bash
# ============================================================
#  Mythica Pipeline — First-Time Setup
#  Double-click this file ONCE to install everything.
#  After it finishes, double-click "Mythica Pipeline.app".
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/.mythica_venv"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     Mythica Pipeline Setup           ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ---- 1. Find Python 3.9+ (prefer 3.14 for Tk 9.0) ----
PYTHON=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$candidate" &>/dev/null; then
        VER=$("$candidate" -c "import sys; print(sys.version_info.major * 100 + sys.version_info.minor)")
        if [ "$VER" -ge 309 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.9 or later is required."
    echo ""
    echo "Please install it from https://www.python.org/downloads/"
    echo "or via Homebrew:  brew install python"
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

echo "✓ Using $($PYTHON --version)"
echo ""

# ---- 2. Create virtual environment ----
echo "Creating Python environment at $VENV …"
"$PYTHON" -m venv "$VENV"
source "$VENV/bin/activate"

echo "✓ Environment ready"
echo ""

# ---- 3. Install dependencies ----
echo "Installing packages (this may take a minute)…"
pip install --quiet --upgrade pip
pip install --quiet \
    "Pillow>=10.0.0" \
    "openai>=1.0.0" \
    "requests>=2.31.0" \
    "keyring>=24.0.0" \
    "tkinterdnd2>=0.3.0" \
    "pyinstaller>=6.0.0"

echo "✓ Packages installed"
echo ""

# ---- 4. Build the .app ----
echo "Building Mythica Pipeline.app …"
cd "$SCRIPT_DIR"
pyinstaller --clean --noconfirm Mythica.spec 2>&1 | tail -5

APP_PATH="$SCRIPT_DIR/dist/Mythica Pipeline.app"

if [ -d "$APP_PATH" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  Setup complete!                                     ║"
    echo "║                                                      ║"
    echo "║  Your app is ready at:                              ║"
    echo "║  dist/Mythica Pipeline.app                          ║"
    echo "║                                                      ║"
    echo "║  Double-click it to launch. You can also drag it    ║"
    echo "║  to your /Applications folder for easy access.       ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    # Open the dist folder in Finder
    open "$SCRIPT_DIR/dist/"
else
    echo ""
    echo "Something went wrong — the .app was not created."
    echo "Check the output above for errors."
    echo ""
fi

read -p "Press Enter to close this window…"
