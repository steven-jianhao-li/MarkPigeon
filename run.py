#!/usr/bin/env python3
"""
MarkPigeon Entry Point for PyInstaller

This file uses absolute imports to work correctly in frozen executables.
"""

import sys
import os

# Add src to path for frozen executable
if getattr(sys, 'frozen', False):
    # Running as compiled
    app_path = os.path.dirname(sys.executable)
    sys.path.insert(0, app_path)
else:
    # Running as script
    app_path = os.path.dirname(os.path.abspath(__file__))
    parent_path = os.path.dirname(app_path)
    if parent_path not in sys.path:
        sys.path.insert(0, parent_path)


def main():
    """
    Main entry point for MarkPigeon.

    - No arguments: Launch GUI
    - With arguments: Run CLI
    """
    if len(sys.argv) > 1:
        # CLI mode
        from src.interfaces.cli.main import main as cli_main
        sys.exit(cli_main())
    else:
        # GUI mode
        try:
            from src.interfaces.gui.main_window import run_gui
            run_gui()
        except ImportError as e:
            print(f"Error: GUI dependencies not available: {e}")
            print("Please install PySide6: pip install PySide6")
            print("\nAlternatively, use CLI mode:")
            print("  markpigeon document.md --help")
            sys.exit(1)


if __name__ == "__main__":
    main()
