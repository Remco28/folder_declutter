# Phase 8 Follow‑up — Invalid Paths UX Fixups

Status: ARCHIVED
Owner: Architect
Date: 2025-09-15

## Objective
Polish and stabilize the Phase 8 implementation by fixing the undefined move completion callback and ensuring tiles with no path use the same recovery flow as invalid paths.

## Context
Current behavior largely matches spec (existence+writability checks, invalid UI, recovery dialog). Two issues remain:
1) `_handle_invalid_section_drop` calls `file_operations.move_many(..., self._on_move_complete)` but `_on_move_complete` is undefined.
2) `on_drop` returns early when a section has no path, instead of using the invalid‑target recovery flow (Reselect/Remove).

## Files To Modify
- `src/ui/window.py`

## Requirements
1) Unify move completion handler
   - Extract the existing inner `on_move_done` logic from `on_drop` into a reusable instance method:
     - `def _on_move_done(self, batch_result, undo_actions):`
       - Count ok/skipped/error; log summary
       - If undo_actions present → push to undo stack and update undo button
       - Log individual errors
   - Change both call sites to use it:
     - In `on_drop` → pass `self._on_move_done`
     - In `_handle_invalid_section_drop` (reselect path branch) → pass `self._on_move_done` (replace undefined `_on_move_complete`).

2) No‑path tiles trigger recovery flow
   - In `on_drop`, when `target_dir` is falsy (None/empty), do not return early. Instead:
     - Call `self._handle_invalid_section_drop(section_id, paths, self.tiles[section_id])`
     - Return afterward (the handler will proceed if user reselects a valid folder).

3) Optional logging clarity (nice to have)
   - During `_load_sections_from_config`, when encountering invalid paths, log a reason (missing vs. not writable) for quick triage. Keep it simple; duplicating the checks used in `SectionTile._validate_path` is fine.

## Acceptance Criteria
1) Dropping onto a tile with no path opens the invalid‑target dialog and, upon Reselect, proceeds with the move to the newly chosen folder.
2) No undefined attribute errors; both code paths use the same `_on_move_done` completion handler.
3) Undo stack updates as before; undo button state remains correct.
4) Optional: startup logs for invalid sections include a reason.

## Manual Test Checklist
- No‑path tile: define a tile, then clear its path in config or set to empty; drop → recovery dialog; reselect folder → files move; remove/cancel → no move.
- Invalid path (missing folder): drop → recovery dialog; reselect valid folder → proceeds; remove/cancel → no move.
- Valid tile: drop still works; undo still works; no regressions.
