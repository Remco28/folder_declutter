# Phase 7 Spec — Recycle Bin Support (Windows)

Status: SPEC READY
Owner: Architect
Date: 2025-09-13

## Objective
Send dropped files/folders to the Windows Recycle Bin using pywin32 shell APIs with `FOF_ALLOWUNDO`. Handle multiple items and folders reliably, run off the UI thread, and surface per-item results. Non‑Windows should no‑op cleanly.

## Background
File moves and Undo (Phase 6) are in place. Dropping onto the Recycle Bin target currently logs a warning. This phase wires a Windows‑native delete‑to‑bin. Programmatic restoration from the Recycle Bin is out of scope; users can restore via the Recycle Bin UI.

## Scope
- Implement a `RecycleBinService` using pywin32:
  - Prefer `IFileOperation` (Vista+) with `FOF_ALLOWUNDO`.
  - Fallback to `SHFileOperationW` with `FO_DELETE | FOF_ALLOWUNDO` and double‑null path list.
- Integrate with `MainWindow.on_drop` for the Recycle Bin target.
- Run operations in a background thread and marshal completion back to the UI thread.
- Provide per‑item results and summary logging.

Out of scope: Programmatic restore from Windows Recycle Bin; cross‑platform recycle support.

## Files To Add
- `src/services/recycle_bin.py`

## Files To Modify
- `src/ui/dialogs.py` — add `prompt_confirm_recycle(count)` returning `True|False` (optional confirmation; see Behavior).
- `src/ui/window.py` — call RecycleBinService for Recycle Bin drops; log results; do not push to Undo.
- `docs/ARCHITECTURE.md` — document Recycle Bin service and integration.

## Behavior & Requirements
1) Service API
   - `class RecycleBinService(root, logger=None)`
     - `delete_many(paths: list[str], on_done: callable) -> None` runs in background and calls `on_done(results)` on main thread.
     - `is_available() -> bool` returns True only on Windows with pywin32 present.
   - Result item: `{ path: str, status: 'ok'|'error', error?: str }`.

2) Implementation details
   - Prefer COM‑based `IFileOperation`:
     - Initialize COM apartment (`pythoncom.CoInitialize`/`CoUninitialize` in worker thread).
     - Create `IFileOperation`, set flags including `FOF_ALLOWUNDO | FOF_NOCONFIRMMKDIR | FOFX_NOCOPYSECURITYATTRIBS` (keep confirmation decisions inside our app if using a prompt).
     - For each path, bind to `IShellItem` and call `DeleteItem` (or use `DeleteItems` when available).
     - Execute and collect per‑item success via handler callbacks if easily available; otherwise, assume batch success and map failures by catching exceptions around per‑item add.
   - Fallback `SHFileOperationW`:
     - Build a single string of absolute paths separated by `\0` and terminated with `\0\0`.
     - Call with `wFunc=FO_DELETE`, `fFlags=FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT` (set `FOF_NOCONFIRMATION` only if we prompt beforehand; see next section).
     - Map return code to success/failure; if partial failures are not surfaced, report batch error with a generic message.
   - Normalize all inputs to absolute Windows paths; support files and directories.
   - Long paths: best‑effort — if a path startswith `\\?\`, pass through; otherwise, use standard form (deep long‑path handling can be deferred to Phase 12).

3) Confirmation UX (optional but recommended)
   - Add `dialogs.prompt_confirm_recycle(count)` used only when `count >= 5` or when an env flag `DS_CONFIRM_RECYCLE=1` is set.
   - The dialog is modal, parented to the main window, and uses our existing topmost handling pattern.
   - If user cancels, do not perform any deletion; log a cancellation.

4) UI integration
   - In `MainWindow.on_drop(section_id=None, paths)`:
     - If service unavailable: log a warning and return.
     - Optionally prompt confirmation per above; on cancel, return.
     - Call `RecycleBinService.delete_many(paths, on_done=...)`.
     - In `on_done(results)`: log a summary `ok/errors`; do not push to Undo stack. Consider light UI feedback (later phases) but for now logging is sufficient.

5) Threading & main thread callbacks
   - `RecycleBinService` owns its own small `ThreadPoolExecutor` (1 worker) similar to FileOperations.
   - Marshal `on_done` via `root.after(0, ...)`.

6) Non‑Windows behavior
   - `is_available()` returns False; drops to Recycle Bin continue to log a single warning (no crash).

## Function Signatures (Python)
- `src/services/recycle_bin.py`
  - `class RecycleBinService:`
    - `def __init__(self, root, logger=None)`
    - `def is_available(self) -> bool`
    - `def delete_many(self, paths: list[str], on_done: callable) -> None`
    - `def shutdown(self) -> None`

- `src/ui/dialogs.py`
  - `def prompt_confirm_recycle(count: int, parent=None) -> bool`  # True=proceed, False=cancel

## Pseudocode Highlights
IFileOperation path:
```
def delete_many(paths, on_done):
  def work():
    results = []
    try:
      CoInitialize()
      op = Create IFileOperation
      op.SetOperationFlags(FOF_ALLOWUNDO | FOF_NOCONFIRMMKDIR | FOF_SILENT)
      for p in paths:
        try:
          item = SHCreateItemFromParsingName(p)
          op.DeleteItem(item, None)
          results.append({ 'path': p, 'status': 'ok' })
        except Exception as e:
          results.append({ 'path': p, 'status': 'error', 'error': str(e) })
      op.PerformOperations()
    except Exception as e:
      if not results:
        results = [{ 'path': p, 'status': 'error', 'error': str(e) } for p in paths]
    finally:
      CoUninitialize()
    call_main(on_done, results)
  submit(work)
```

SHFileOperation fallback:
```
def delete_many(paths, on_done):
  def work():
    path_blob = "\0".join(paths) + "\0\0"
    res = SHFileOperationW(FO_DELETE, path_blob, flags=FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT)
    results = [{ 'path': p, 'status': 'ok' if res==0 else 'error', 'error': 'SHFileOperation failed' if res!=0 else None } for p in paths]
    call_main(on_done, results)
  submit(work)
```

## Acceptance Criteria
- Dropping one or more files/folders onto the Recycle Bin target deletes them to the Windows Recycle Bin (they appear in Recycle Bin UI).
- The operation runs in the background; the app remains responsive; a summary log shows counts of ok/error.
- For large drops (>=5), a confirmation prompt appears; cancel aborts without deleting.
- Non‑Windows runs without errors and logs a clear warning for Recycle Bin drops.

## Manual Test Checklist
1) Single file
   - Drop a file onto the Recycle Bin → appears in Recycle Bin; log shows 1 ok.
2) Mixed selection
   - Drop multiple files and a folder → all appear in Recycle Bin; summary logged.
3) Cancel confirmation
   - With `DS_CONFIRM_RECYCLE=1`, drop items → cancel → nothing deleted.
4) Error case
   - Include a locked/in-use file if possible → error reported for that path; others succeed.
5) Non‑Windows
   - On macOS/Linux dev machine, drop to Recycle Bin → no crash; warning logged.

## Notes
- Ensure COM initialization occurs in the worker thread for IFileOperation.
- Packaging (Phase 9): include pywin32 runtime; verify Recycle Bin operations in the bundled exe.

