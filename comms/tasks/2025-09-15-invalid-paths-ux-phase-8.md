# Phase 8 Spec — Invalid Paths UX (Detect, Prompt, and Guard Drops)

Status: SPEC READY
Owner: Architect
Date: 2025-09-15

## Objective
Improve the user experience when a section points to a missing or inaccessible folder by:
- Detecting invalid paths at startup and on interaction.
- Visually indicating invalid sections.
- Prompting users to reselect or remove the location when attempting to drop.
- Preventing moves to invalid targets while offering a quick fix flow.

## Background
Sections persist across runs (Phase 4). Users might rename/move/delete folders or lose access (e.g., unplugged drive, permission changes). Today, tiles render with a red border (basic hint), but drops still attempt to move and then fail later. We need a clear, guided path to recover.

## Scope
- Keep implementation focused in UI components; no OS‑specific code here.
- Add one small dialog to guide the user when dropping onto an invalid section.
- Minimal state tracking: compute validity on demand; no watchers.

## Files To Modify
- `src/ui/window.py` — gate drop on section validity; prompt recover flow; proceed if reselected.
- `src/ui/section.py` — ensure invalid visual is clear; optional small subtitle text for invalid.
- `src/ui/dialogs.py` — add `prompt_invalid_target(label, path, parent=None) -> str|None` returning `'reselect'|'remove'|None`.
- `docs/ARCHITECTURE.md` — update Invalid Paths UX behavior in Data Flow/Runtime notes.

## Behavior & Requirements
1) Detect invalid paths
   - A section is invalid if `path` is missing or not writable: `not os.path.exists(path)` or `not os.access(path, os.W_OK)`.
   - Compute validity:
     - On startup when loading config (existing behavior in SectionTile is acceptable; ensure write check added).
     - On drop attempt: re-check before starting the move.

2) Visual indication
   - For invalid sections:
     - Keep existing red border styling.
     - Add a small, subdued subtitle text inside the tile: `“Missing or inaccessible”`.
     - Tooltip shows: full path and a short reason, e.g., `“Folder not found”` or `“No write permission”`.

3) Drop guard + recovery prompt
   - When user drops onto an invalid section, do not start the move.
   - Show `prompt_invalid_target(label, path, parent)` dialog with message:
     - Title: `Invalid Location`
     - Body: `"'<label>' is missing or inaccessible. What would you like to do?"`
     - Buttons: `Reselect Folder…`, `Remove Location`, `Cancel`.
   - Button behavior:
     - Reselect: open folder picker. If user chooses a folder, update the section and immediately proceed with the pending drop to the new path.
     - Remove: clear the section; cancel the drop.
     - Cancel: do nothing.
   - Pass‑through/topmost behavior: follow existing patterns (temporarily disable pass‑through; drop `-topmost`; restore afterward).

4) Startup rendering
   - When loading config, tiles with invalid paths should immediately render in invalid state (red border + subtitle) and their tooltips should explain the issue.

5) Logging
   - On drop to invalid: log a warning with the reason.
   - On reselect: log the new path; on remove: log removal.

6) Out of scope (future)
   - Background revalidation, filesystem watchers, and granular permission diagnostics.

## Function Signatures
- `src/ui/dialogs.py`
  - `def prompt_invalid_target(label: str, path: str, parent=None) -> Optional[str]`  # returns 'reselect' | 'remove' | None

## Implementation Notes
- Validity helpers can live in SectionTile (e.g., `_is_valid = exists and writable`).
- Revalidate at drop time in `MainWindow.on_drop` before building the move request.
- For tooltip reason: simple check order — exists? if not → `Folder not found`; else if not writable → `No write permission`.
- Keep UI text short and neutral; no intrusive modals except when the user initiates a drop.

## Acceptance Criteria
1) On startup, tiles with broken paths show red border + “Missing or inaccessible” subtitle; tooltip shows reason.
2) Dropping onto an invalid tile opens recovery dialog; choosing Reselect updates the tile and proceeds with the move to the new folder.
3) Choosing Remove clears the tile and cancels the move; choosing Cancel leaves everything unchanged.
4) Dropping onto valid tiles continues to work unchanged.

## Manual Test Checklist
1) Missing folder
   - Configure a tile, then delete/rename the folder. Restart app → tile shows invalid.
   - Drop a file onto the tile → recovery dialog appears. Reselect a valid folder → file moves to new folder; tile updates.
2) Permission denied
   - Point a tile to a path without write access. Drop → recovery dialog appears. Cancel → no move; Remove → tile clears.
3) Normal behavior unaffected
   - Valid tile drops function as before; undo and Recycle Bin flow unchanged.

