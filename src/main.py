"""Entry point for Mythica Pipeline."""

import sys
import os

# Make src/ the root so all imports work whether run directly or via PyInstaller
_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from ui.main_window import MythicaApp


def main():
    app = MythicaApp()
    app.run()


if __name__ == "__main__":
    main()
