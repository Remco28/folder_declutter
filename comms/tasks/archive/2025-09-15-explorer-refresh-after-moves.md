Title: Ensure Explorer/Desktop refresh after moves — explicit SHChangeNotify (per-item + batched)

Objective
- Make icon/list updates in Explorer (especially Desktop) immediate and consistent after moves. Use explicit Shell change notifications to supplement IFileOperation and cover shutil fallback.

Why
- Intermittent stale views suggest some moves do not surface to Explorer reliably (e.g., shutil fallback, timing). A lightweight, explicit `SHChangeNotify` on touched directories closes the gap.

Scope
- Windows only; no-ops on other platforms. Keep existing IFileOperation logic intact.

Files
- src/file_handler/file_operations.py
- how_to_test.md (add verification steps)

Required Changes
1) Collect touched directories during a batch
   - In `move_many` work() loop, when a move finishes with status 'ok' or 'skipped-replace' equivalent, collect:
     - `src.parent` (old parent directory)
     - `dest.parent` (new parent directory)
   - Use a `set[str]` of absolute, normalized paths.

2) Notify Explorer after each successful move (lightweight) and once at end (batched)
   - Add helper methods (Windows only):
     - `_shell_notify_updatedir(path: Path)` → calls `shell.SHChangeNotify(shellcon.SHCNE_UPDATEDIR, shellcon.SHCNF_PATHW, str(path), 0)` inside a try/except.
     - Optionally `_shell_notify_updateitem(path: Path)` for the moved item path when helpful; start with directories only to keep it simple and robust.
   - After each successful move (both in `_move_one_windows_shell` after `PerformOperations()` and in `_move_one_shutil` after `shutil.move`), call `_shell_notify_updatedir(src.parent)` and `_shell_notify_updatedir(dest.parent)`.
   - At the end of `move_many` (before invoking `on_done`), iterate the collected parent paths and call `_shell_notify_updatedir` for each to coalesce any missed updates.

3) Optional belt-and-suspenders for Desktop
   - If any touched path is under the user Desktop or Public Desktop, also notify those roots once at batch end.
   - Retrieve with `shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, 0, 0)` and `shellcon.CSIDL_COMMON_DESKTOPDIRECTORY` (guard for availability). Only attempt when pywin32 is available.

Constraints
- Windows guard: wrap imports and calls so non-Windows builds run unchanged.
- Keep notifications lightweight (quick function call); the per-item + batch pass should not introduce noticeable latency.
- Do not alter existing overwrite/backup logic.

Acceptance Criteria
- Repeated moves from Desktop (user Desktop) update immediately without manual refresh.
- Moves into and out of non-Desktop folders reflect in Explorer views right away.
- Behavior consistent whether the operation used IFileOperation or shutil fallback.
- No regressions in performance, threading, or error handling.

