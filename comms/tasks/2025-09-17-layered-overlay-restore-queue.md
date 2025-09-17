# Layered Overlay Restore Queue

## Context
- The layered overlay now renders correctly, but double-clicking it crashes Python with `Fatal Python error: PyEval_RestoreThread`.
- Root cause: the layered window’s native WndProc invokes our `_restore_cb`, which currently calls `Tk.after`. When the Windows message arrives, we are inside the native callback on the Win32 side, and CPython 3.13 now aborts if Tk is touched from that context because the thread isn’t holding Tk’s interpreter state.
- We need to bounce the restore request off to the Tk main thread without calling into Tk from the WndProc.

## Objective
Route layered-overlay restore events through a thread-safe queue that is drained on the Tk thread, so the WndProc never touches Tk directly.

## Changes Required
- File: `src/ui/mini_overlay.py`
  1. Import `queue` (standard library) and initialize a thread-safe queue, e.g. `queue.SimpleQueue`, during `MiniOverlay` construction. Add small state to manage a Tk `after` loop (e.g. `_restore_queue`, `_restore_poll_id`, `_restore_poll_interval_ms`).
  2. Replace the current layered `_restore_cb` to **only** enqueue a sentinel (e.g. `self._restore_queue.put('restore')`). Do not call Tk from inside this callback.
  3. Add helper methods, for example `_start_restore_pump()` and `_process_restore_queue()`, that run on the Tk thread. The pump should schedule itself with `after` while the layered overlay is active or pending work exists, drain the queue, and invoke the real `self.on_restore()` for each queued event (with try/except around user callbacks as today).
  4. Ensure the pump starts when the layered overlay is shown (e.g. in `show_centered_over` after `LayeredOverlay.create` succeeds) and stops/clears when the overlay is hidden/destroyed (`hide()` and/or when layered overlay initialization fails). Clear any stale queue items during shutdown.
  5. Keep logging behavior similar (maintain the existing info log in the WndProc and when the restore actually runs). Add a brief comment near the queue explaining the thread hop rationale.

- File: `src/services/win_overlay.py`
  - No functional change required beyond possibly updating the double-click comment to mention the callback is asynchronous now. Ensure the WndProc continues to call `self.on_restore()` exactly once per double-click.

## Constraints / Notes
- The queue must be thread-safe because the WndProc runs in the Win32 callback context.
- Avoid tight polling loops; the pump should reschedule itself only as needed (e.g., fixed small interval while overlay visible, or only when work remains).
- Do not regress the Tk fallback path—its double-click handler can continue to call `self.on_restore()` directly because it already runs on the Tk thread.

## Acceptance Criteria
- Double-clicking the layered overlay restores the main window without crashing.
- Logs show the layered overlay double-click message followed by `Overlay restore requested` as before.
- Subsequent minimize/restore cycles continue to work; no stray overlays remain.
- No new crashes or regressions in overlay dragging.
