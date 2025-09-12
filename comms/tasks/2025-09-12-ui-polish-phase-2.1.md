# Phase 2.1 Spec — UI Polish and Robustness

Status: SPEC READY
Owner: Architect
Date: 2025-09-12

## Objective
Tighten the Phase 2 UI scaffold for reliability and ergonomics without changing scope. Focus on package structure, minor UX polish, and small safeguards.

## Changes In Scope
1) Package structure
- Add `__init__.py` to `src/` and `src/ui/` to make them packages.
- Preferred run command: `python -m src.main` from repo root.

2) Imports and lint
- Remove unused imports/variables (e.g., `ttk` in `window.py`).
- Ensure module-level loggers follow `logger = logging.getLogger(__name__)` pattern.

3) Tooltip robustness
- Prevent duplicate tooltip windows on rapid `<Enter>` events. Keep a single `Toplevel` per tile; ignore if already visible.
- Destroy tooltip on `<Leave>` and on `<FocusOut>` of the main window to avoid orphan windows.

4) Keyboard binding reliability
- Bind Undo shortcut on the toplevel: `root.bind_all('<Control-z>', ...)` to ensure it fires when a tile has focus.
- Keep the Undo button disabled; handler should be a no-op.

5) Visual neutrality
- Replace hard-coded tile backgrounds with theme-friendly defaults:
  - Defined: use default widget background; add a subtle border or relief for readability.
  - Invalid path state (if present): add a red border only (no background color).
- Keep the “+” tile minimal; use default bg with a bold plus glyph.

6) Context menu availability
- Ensure right‑click context menu is only bound for defined tiles; empty tiles do nothing on right‑click.

## Files To Modify
- `src/ui/window.py`
  - Remove `from tkinter import ttk` (unused).
  - Change Undo binding to `parent.bind_all('<Control-z>', ...)`.
- `src/ui/section.py`
  - Tooltip: guard against duplicates; add `<FocusOut>` destroy.
  - Visuals: remove `bg='lightblue'/'lightcoral'`; rely on default bg; add conditional border color when invalid.
  - Ensure right‑click is only bound in defined state.
- Add: `src/__init__.py`, `src/ui/__init__.py` (empty files).

## Acceptance Criteria
- Running `python -m src.main` launches the app.
- No unused imports in the modified files.
- Hovering repeatedly does not create multiple tooltip windows; moving focus away closes tooltips.
- Ctrl+Z triggers the undo handler regardless of focus location; button remains disabled.
- Tiles use system-default backgrounds; invalid state (simulate by pointing to a missing path) shows only a red border.
- Right‑click on empty tiles does nothing; defined tiles show the menu.

## Test Checklist (manual)
- Verify launch via module mode.
- Exercise hover enter/leave repeatedly on a defined tile; ensure only one tooltip exists and it disappears on leave/focus-out.
- Confirm Ctrl+Z logs the Undo request while the button remains disabled.
- Change a tile path to a non-existent folder; observe only border turns red.
- Right‑click an empty tile → nothing; right‑click a defined tile → menu appears and functions.

