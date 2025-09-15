Title: Windows overlay — pure OS drag + double‑click restore (replace quick‑click)

Objective
- Make the minimized overlay reliably draggable by delegating movement to Windows (non‑client drag), and restore the app only on double‑click. Remove all single "quick‑click" restore logic on the layered path. Align Tk fallback to double‑click restore as well.

Scope
- Platform: Windows only for the layered overlay; Tk fallback must mirror the double‑click restore gesture.
- No per‑pixel hit‑testing in this pass. No style churn beyond enabling double‑click messages.

Changes Required

Files
- src/services/win_overlay.py
- src/ui/mini_overlay.py
- docs/ARCHITECTURE.md (overlay interaction section)
- how_to_test.md (brief test steps update)

Layered overlay (src/services/win_overlay.py)
1) Ensure window class generates double‑click messages
   - During window class registration, include `CS_DBLCLKS` in `wc.style`.

2) Use OS‑managed dragging exclusively
   - Keep returning `HTCAPTION` from `WM_NCHITTEST` for all points over the overlay (whole window is draggable for now).
   - Remove or bypass any manual drag logic based on `WM_LBUTTONDOWN/WM_MOUSEMOVE/WM_LBUTTONUP` and screen‑space deltas. Do not compute or apply movement yourself while the user drags.
   - Let `DefWindowProc` handle the full move loop. Do not call `SetWindowPos`/`MoveWindow` in response to client mouse messages during drag.

3) Switch restore to double‑click (no single‑click restore)
   - Handle double‑click to restore: implement handlers for `WM_NCLBUTTONDBLCLK` and `WM_LBUTTONDBLCLK` that trigger the existing `on_restore` callback.
   - Do not restore on `WM_LBUTTONUP` or any single‑click path. Remove prior “quick‑click” duration/pixel‑threshold logic entirely for the layered overlay.
   - Threading: schedule the restore callback onto the Tk thread via `root.after(0, on_restore)` as currently done.

4) Optional safety (not required now, but acceptable if trivial)
   - Add internal flag hooks for `WM_ENTERSIZEMOVE`/`WM_EXITSIZEMOVE` (e.g., `self.in_move_loop`) without changing behavior. This can help future diagnostics but should be inert in this pass.

Tk fallback overlay (src/ui/mini_overlay.py)
5) Align gesture and keep drag
   - Maintain existing Tk drag bindings for movement (<B1‑Motion> with start coords).
   - Change restore behavior to require double‑click: bind `<Double-Button-1>` to restore; remove any single‑click/quick‑click restore logic on the Tk path.

Behavioral Details / Constraints
- Styles: keep `WS_POPUP`, `WS_EX_LAYERED`, `WS_EX_TOPMOST`, `WS_EX_TOOLWINDOW`. Do not add `WS_EX_NOACTIVATE` in this pass.
- Do not implement per‑pixel hit‑testing yet; the entire overlay remains draggable.
- Maintain current rendering quality via `UpdateLayeredWindow` with premultiplied BGRA and existing DPI awareness.
- Input expectations:
  - Drag: click‑and‑hold moves the overlay smoothly; releasing the mouse does not restore.
  - Restore: double‑click anywhere on the overlay restores the main window consistently.

Pseudocode (window proc highlights)
```
def _window_proc(hwnd, msg, wparam, lparam):
    if msg == WM_NCHITTEST:
        return HTCAPTION  # let Windows handle dragging

    # Remove prior WM_LBUTTONDOWN/UP/MOVE drag + quick‑click logic

    if msg in (WM_NCLBUTTONDBLCLK, WM_LBUTTONDBLCLK):
        schedule_on_tk_thread(on_restore)
        return 0

    return DefWindowProc(hwnd, msg, wparam, lparam)
```

Integration Notes
- Verify layered overlay creation and MiniOverlay integration do not depend on single‑click semantics (they should not). Only the restore trigger changes.
- Keep the existing centering behavior when showing the overlay and hide/destroy lifecycle as‑is.

Acceptance Criteria
- Dragging the layered overlay works reliably across Windows 10/11 at 100–200% DPI with no accidental restore.
- Double‑clicking the overlay consistently restores the main window (both layered and Tk overlay paths).
- No regression to transparency, edge crispness, z‑order/topmost, or DPI rendering.
- No Alt‑Tab entry for the overlay (WS_EX_TOOLWINDOW preserved).

Testing Steps (manual)
1) Minimize the main app to show the overlay.
2) Drag the overlay around by click‑and‑hold; confirm it follows the cursor smoothly and does not restore when releasing.
3) Double‑click the overlay; confirm the main window restores.
4) Repeat at different DPIs (100%, 150%, 200%).
5) Force Tk fallback (if a toggle exists) and verify the same double‑click restore behavior while drag remains via Tk.

Out of Scope
- Per‑pixel hit‑testing, style changes beyond `CS_DBLCLKS`, or gesture experimentation.

Notes for Developer
- Keep the implementation minimal and remove obsolete quick‑click code paths to avoid ambiguity.
- If needed during development, you may temporarily print trace lines for `WM_NCHITTEST` and double‑click messages, but remove or guard them behind an internal debug flag before finalizing.

