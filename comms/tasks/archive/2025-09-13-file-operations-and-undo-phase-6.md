# Phase 6 Spec — File Operations + Undo

Status: SPEC READY
Owner: Architect
Date: 2025-09-13

## Objective
Move dropped files/folders to the target section folder reliably without freezing the UI, handle name conflicts with a confirmation dialog, and provide session-only multi-level Undo for completed move batches.

## Background
We have DnD (Phase 5) and persisted sections (Phase 4). Now we need to perform the actual file operations. Operations must run off the Tk main thread, surface results back to the UI, and enable Undo to reverse the last completed batch(es). Recycle Bin logic is deferred to Phase 7, so drops to the Recycle Bin target should be ignored with a warning for now.

## Scope
- Implement threaded move operations with per-item results and aggregate batch result.
- Present a simple overwrite/skip dialog on name conflicts.
- Implement an Undo service that can reverse the most recent batch(es).
- Wire MainWindow to call moves on drop and to trigger undo via button/Ctrl+Z.

Out of scope: Recycle Bin API calls (Phase 7), long-path/UNC edge-case hardening (Phase 12), rich progress UI (log-only for now).

## Files To Add
- `src/file_handler/file_operations.py`
- `src/services/undo.py`
- `src/file_handler/error_handler.py` (simple mapping/log helper)

## Files To Modify
- `src/ui/dialogs.py` — add `prompt_overwrite(target_path)` returning one of `"replace"|"skip"|None` (None = cancel batch).
- `src/ui/window.py` — implement `on_drop` to build and dispatch a MoveRequest; update Undo button state; call UndoService on undo.
- `docs/ARCHITECTURE.md` — confirm flows for File Operations and Undo.

## Data Structures
- MoveRequest: `{ sources: list[str], target_dir: str, options: { overwrite: bool | None } }`
- MoveResult (per-item): `{ src: str, dest: str, status: 'ok'|'skipped'|'error', error?: str, conflict?: bool, backup?: str }`
- BatchResult: `{ items: list[MoveResult], started_at: ts, finished_at: ts }`
- Undo action model (stored per batch): list of actions:
  - MoveAction: `{ kind: 'move', src: str, dest: str }`  # reverse is move dest -> src
  - ReplaceAction: `{ kind: 'replace', dest: str, backup: str }`  # reverse is restore backup -> dest

Backups directory (session): `%APPDATA%/DesktopSorter/backups/<session_id>/...` (or `~/.config/DesktopSorter/backups/...` on non-Windows). Cleaned on app exit or when an action is undone.

## Behavior & Requirements
1) Threading
   - `FileOperations.move_many` runs in a worker thread (ThreadPoolExecutor or a single worker) and never blocks Tk.
   - UI callbacks are marshaled to the main thread via `root.after(0, ...)` by the caller, or FileOperations accepts callbacks and invokes them safely.

2) Move semantics
   - For each source path, compute destination as `target_dir / basename(src)`.
   - If dest does not exist:
     - Try fast same-volume move `os.replace(src, dest)`; on cross-volume or directory moves fallback to `shutil.move`.
   - If dest exists:
     - Ask user via `dialogs.prompt_overwrite(dest)` once per conflict unless `options.overwrite` is already provided.
     - If "skip": record `status='skipped'`.
     - If "replace": create a backup of the existing destination before move:
       - Make unique backup path under session backups dir, move existing dest there (`os.replace` or `shutil.move`).
       - Proceed with move of `src -> dest`.
       - Record a `ReplaceAction` with `backup` and `dest` so Undo can restore.
     - If cancel (None): abort remaining items and mark batch as cancelled (partial results retained).
   - Exceptions are captured and recorded per item with `status='error'` and a short message from ErrorHandler.

3) Undo semantics
   - UndoService maintains a LIFO stack of batches.
   - `undo_last()` iterates the most recent batch’s actions in reverse order:
     - For MoveAction: if `dest` exists and `src` directory exists, move back `dest -> src` (creating parent dirs as needed). Log and continue on failures.
     - For ReplaceAction: restore original by moving `backup -> dest` (overwriting current dest if needed), then delete/cleanup backup.
   - If any actions fail, report summary to log; UI remains consistent (button enabled if stack not empty).

4) UI wiring
   - `MainWindow.on_drop(section_id, paths)`:
     - If `section_id is None` (Recycle Bin): log warning and return (Phase 7 will implement).
     - Validate section exists and has `path`; if missing/invalid, warn and return.
     - Build MoveRequest and call `FileOperations.move_many(request, on_done=...)`.
     - On completion: push the batch’s undo actions to UndoService and enable Undo button. Log summary counts (ok/skipped/error).
   - `MainWindow.on_undo()`:
     - Call `UndoService.undo_last(on_done=...)` on a worker; on completion, update button state (disable if stack empty) and log.
   - Ensure button state matches `UndoService.can_undo()`.

5) Dialogs
   - `prompt_overwrite(target_path)` is modal, owned by the main window, and returns user choice; when called from background move thread, marshal the blocking prompt to the main thread via a thread-safe helper (`root.after` + a `queue`/`Future`).

6) Error handling
   - `error_handler.to_message(exc, path)` returns a concise string and level for logging.
   - Moves continue after recoverable errors; batch stops only if user cancels.

## Function Signatures (Python)
- `src/file_handler/file_operations.py`
  - `class FileOperations:`
    - `def __init__(self, root, logger=None)`
    - `def move_many(self, request: dict, on_done: callable) -> None`  # returns immediately; runs in background and calls `on_done(batch_result, undo_actions)` on main thread
    - Internal helpers: `_move_one(src, dest, backups_dir, prompt_overwrite_cb) -> (result, undo_actions_for_item)`

- `src/services/undo.py`
  - `class UndoService:`
    - `def __init__(self, root, logger=None)`
    - `def can_undo(self) -> bool`
    - `def push_batch(self, actions: list[dict]) -> None`
    - `def undo_last(self, on_done: callable) -> None`  # background, calls `on_done(success_count, failure_count)` on main thread

- `src/ui/dialogs.py`
  - `def prompt_overwrite(target_path: str, parent=None) -> str | None`  # returns 'replace' | 'skip' | None

## Pseudocode Highlights
Move many (simplified):
```
def move_many(self, request, on_done):
  def work():
    backups_dir = ensure_session_backups_dir()
    items = []
    actions = []
    for src in request['sources']:
      dest = target_dir / basename(src)
      try:
        if exists(dest):
          choice = request['options'].get('overwrite') or prompt_overwrite_main_thread(dest)
          if choice is None: break  # cancel
          if choice == 'skip': items.append(result(skipped)); continue
          # replace
          backup = make_unique_backup(dest, backups_dir)
          replace(dest, backup)
          actions.append({'kind':'replace','dest': str(dest), 'backup': str(backup)})
        do_move(src, dest)
        items.append(result(ok))
        actions.append({'kind':'move','src': str(src), 'dest': str(dest)})
      except Exception as e:
        items.append(result(error, msg=to_message(e, src)))
    batch = { 'items': items, 'started_at': ..., 'finished_at': ... }
    self._call_main_thread(lambda: on_done(batch, actions))
  submit_to_thread(work)
```

Undo last (simplified):
```
def undo_last(self, on_done):
  def work():
    actions = stack.pop()
    ok = fail = 0
    for act in reversed(actions):
      try:
        if act['kind']=='move': replace(act['dest'], act['src'])
        elif act['kind']=='replace': replace(act['backup'], act['dest'])
        ok += 1
      except Exception: fail += 1
    self._call_main_thread(lambda: on_done(ok, fail))
  submit_to_thread(work)
```

## Acceptance Criteria
- Drop 10 mixed files/folders onto a defined section pointing to a writable folder:
  - Files move successfully; UI remains responsive; logs report counts.
  - If a name conflict occurs, a modal Replace/Skip/Cancel prompt appears; choices apply per item; Cancel aborts remainder.
  - After completion, Undo button enables; pressing it restores the moved items to their original locations and (for replaced files) restores the previous destination contents.
- Repeated Undo works for successive batches (LIFO).
- Dropping onto Recycle Bin logs a warning and no operations are performed (Phase 7 will implement).
- Errors (e.g., permission denied) are logged per item; remaining items continue.

## Manual Test Checklist
1) Basic move
   - Create a test section; drop a few files; verify files appear in the target folder; UI does not freeze.
2) Conflict handling
   - Drop a file with the same name; choose Skip; verify original dest is preserved. Repeat with Replace; verify replaced; Undo restores prior contents.
3) Cross-volume
   - Move between different drives (if available); verify operation still succeeds.
4) Undo stack
   - Perform two drops to different sections; press Undo twice; verify LIFO behavior.
5) Cancel mid-batch
   - Trigger a conflict and choose Cancel; verify remaining sources are not moved.
6) Recycle Bin target
   - Drop onto Recycle Bin label; verify a warning log; nothing moves.

## Notes
- Keep file I/O off the UI thread. Use a simple worker thread pool; no heavy progress UI yet.
- Make sure to create parent directories for undo operations if needed.
- Clean up backup files after they are restored or when the app exits (best-effort cleanup if session folders remain).

