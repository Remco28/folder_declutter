How to run on Linux

  - Ensure Tk is available:
      - Ubuntu/Debian: sudo apt install python3-tk
      - Fedora: sudo dnf install python3-tkinter
      - Arch: sudo pacman -S tk
  - Activate your venv: source folder_declutter_env/bin/activate
  - Run from repo root:
      - Option A (current layout): PYTHONPATH=src python3 src/main.py
      - Option B (after Phase 2.1 adds packages): python3 -m src.main

  What to test

  - Window shows “Desktop Sorter”, stays on top.
  - 2×3 grid of tiles; bottom shows “Recycle Bin” and a disabled “Undo”.
  - Click a “+” tile → pick a folder → enter a label → label renders.
  - Hover a defined tile → tooltip shows full path; disappears on leave.
  - Right‑click a defined tile → Change Location…, Rename Label…, Remove Location all work.
  - Press Ctrl+Z → should log “Undo requested (not implemented in Phase 2)”; button remains disabled.

  Notes and troubleshooting

  - No Windows-only deps needed for this phase; pywin32 is not required on Linux.
  - If file dialogs don’t appear on WSL/headless, you need an X/Wayland display or run on a desktop session.
  - Minor polish items (e.g., duplicate tooltips, theme colors) are slated for Phase 2.1.

  Dependencies status

  - In your venv: tkinterdnd2 and PyInstaller are present; pywin32 is not (expected on Linux).
  - For Linux testing now, you’re covered. For Phase 3, install pywin32 only on Windows.
