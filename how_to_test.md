How to run on Linux

  - Ensure Tk is available:
      - Ubuntu/Debian: sudo apt install python3-tk
      - Fedora: sudo dnf install python3-tkinter
      - Arch: sudo pacman -S tk
  - Activate your venv: source folder_declutter_env/bin/activate
  - Run from repo root:
      - Option A (current layout): PYTHONPATH=src python3 src/main.py
      - Option B (after Phase 2.1 adds packages): python3 -m src.main

  What to test (Linux dev)

  - Window shows “Desktop Sorter”, stays on top.
  - 2×3 grid of tiles; bottom shows “Recycle Bin” and an Undo button.
  - Click a “+” tile → pick a folder → enter a label → label renders.
  - Restart the app → defined tiles persist (Phase 4).
  - Hover a defined tile → tooltip shows full path; disappears on leave.
  - Right‑click a defined tile → Change Location…, Rename Label…, Remove Location all work and persist.
  - Drag-and-drop from a Linux file manager may not be supported; primary DnD target is Windows Explorer.

  Notes and troubleshooting

  - No Windows-only deps needed for this phase; pywin32 is not required on Linux.
  - If file dialogs don’t appear on WSL/headless, you need an X/Wayland display or run on a desktop session.
  - Minor polish items (e.g., duplicate tooltips, theme colors) are slated for Phase 2.1.

How to run on Windows

  - Use a native Windows Python (PowerShell/CMD), not WSL.
  - Create and activate a venv:
      - PowerShell: python -m venv .venv; .venv\Scripts\Activate.ps1
  - Install deps: pip install -r requirements.txt
  - Run from repo root: python -m src.main

  Windows smoke test
  - Window shows “Desktop Sorter”, stays on top.
  - 2×3 grid of tiles; bottom shows “Recycle Bin” and an Undo button (disabled until a move completes).
  - Pass-through is enabled by default: clicks fall through to the window underneath.
  - Debug toggle: set `$env:DS_DND_DEBUG="1"`, then press Ctrl+Alt+P to toggle pass-through on/off. Tiles remain visible in both states.
  - Dialogs (Add/Change/Rename/Overwrite) temporarily disable pass-through while open and re-enable afterward. Dialogs appear above the app.

  Phase 4 — Config persistence
  - Define a few tiles; close and relaunch → tiles restore.
  - Manually break a path in the config file → tile renders with invalid state; warning logs.

  Phase 5 — Drag-and-drop
  - Drop one or more files/folders from Explorer onto a tile → app logs the drop; tile highlights on drag-over.
  - Recycle Bin target currently logs a warning (Phase 7 adds behavior).

  Phase 6 — File operations + Undo
  - Drop files onto a defined tile pointing to a writable folder → files move; UI remains responsive; summary logged.
  - Desktop refresh: when moving items from the Desktop, icons disappear immediately after the move (Windows shell-backed moves).
  - Conflict: drop a file with same name → Replace/Skip/Cancel dialog appears above the main window; button labels are visible; choices apply per item; Cancel aborts remaining.
  - Undo: after a move completes, Undo enables; pressing Undo restores moved items (and prior contents if replaced). Repeated drops produce a LIFO undo stack.

  Phase 10B/10C — Overlay transparency, OS drag, double-click restore (Windows)
  - Minimize the app → a borderless, topmost overlay shows only the logo (no white rectangle) centered over the main window's last position.
  - Drag: click-and-hold anywhere on the overlay and move → the overlay follows smoothly; releasing the mouse does not restore.
  - Restore: double-click the overlay → main window restores (deiconify + raise + focus) and the overlay hides.
  - Minimize again → overlay appears centered over the main window (it does not remember the overlay's prior drag position when minimizing).
  - On high-DPI displays, verify the logo scales up: size ≈ min(screen_w, screen_h)/4.2 clamped to [192, 512] and never upscaled beyond source. With layered overlay enabled (Windows), edges should be crisp (no halos). Ensure the process is DPI-aware (no OS scaling blur).

  Overlay troubleshooting
  - Force layered overlay mode (native Windows with per-pixel alpha):
    PowerShell: $env:DS_OVERLAY_MODE = "layered"; python -m src.main
    Expected: logs "Using layered overlay" on startup; overlay has crisp edges without halos.
  - Force Tk fallback mode (chroma-key transparency):
    PowerShell: $env:DS_OVERLAY_MODE = "tk"; python -m src.main
    Expected: logs "Layered overlay disabled: forced Tk mode" on startup; overlay may have slight edge halos.
  - Enable debug logging for overlay events:
    PowerShell: $env:DS_OVERLAY_MODE = "tk"; $env:DS_OVERLAY_DEBUG = "1"; python -m src.main
    Expected: detailed logs for click/drag/release events, screen coordinates, geometry changes, and Tk scaling info.
  - Check what mode is active: look for "Overlay mode: auto (Windows detected)" and "Using layered overlay" or "Layered overlay disabled: <reason>" in startup logs.

  WSL/WSLg note
  - Always-on-top and Windows pass-through rely on native Win32 APIs and won't behave correctly under WSL/WSLg. Test these features using native Windows Python.

  Dependencies status

  - In your venv: tkinterdnd2 and PyInstaller are present; pywin32 is not (expected on Linux).
  - On Windows: ensure pywin32 is installed for pass-through and shell-backed file operations (Recycle Bin and moves).
