Title: Drag-to-move overlay — investigation summary and hypotheses

Context
- Goal: When the main window is minimized, show a floating logo (overlay) that the user can drag to move around. A quick click should restore the main window. Transparency should be perfect (no white box), and edges should be crisp.
- Platform: Windows only. UI uses Tk for the app window; overlay uses either Tk Toplevel (fallback) or a native layered window (preferred).

Current Implementation (at time of writing)
- Preferred path: Native layered window (`src/services/win_overlay.py`).
  - Window: `WS_POPUP` with `WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST`.
  - Rendering: `UpdateLayeredWindow` with a 32‑bit premultiplied BGRA DIB (fix for edge quality). Transparency looks good.
  - Input: window proc handles mouse messages. We tried two approaches:
    1) Manual drag — WM_LBUTTONDOWN/MOVE/UP with screen‑space deltas; threshold 1–2 px. Quick‑click restore on UP if short duration and tiny movement.
    2) OS drag — Return `HTCAPTION` on `WM_NCHITTEST` so Windows moves the window natively; on mouse up, restore only if the window position did not change and the click was quick.
  - Restore callback runs on the Tk thread via `root.after(0, on_restore)`.
  - DPI awareness enabled to avoid blurry OS scaling.
- Fallback path: Tk Toplevel with `overrideredirect(True)` + `-topmost` + `-transparentcolor` (magenta key). Drag handled by Tk bindings (<B1‑Motion>); quick‑click restore on <ButtonRelease>. This path is currently secondary.

Observed Behavior (from user testing)
- Transparency and edge quality are good after premultiplying and layered window changes.
- Dragging still does not work: any interaction on the overlay ends up restoring the main app. No amount of dragging moves the overlay.
- Main window/overwrite dialog sizing issues have been addressed and are now acceptable.

Changes Attempted (chronological highlights)
1) Tk overlay drag logic (Phase 10A/10B)
   - Bind <Button‑1>, <B1‑Motion>, <ButtonRelease‑1>; threshold 3 px; restore if no drag.
   - Issue: very small motion often resulted in restore (felt like a click). Lowered threshold helped but not reliable.

2) Layered overlay (Phase 10C initial)
   - Implemented native layered window with per‑pixel alpha; manual drag via WM_LBUTTON* with client deltas.
   - Quick‑click: ≤ 200 ms, ≤ 1 px.
   - Result: still restored too often; drag unreliable.

3) Thread safety + quality pass
   - Restore callback scheduled via Tk `after(0, ...)` to avoid cross‑thread UI calls.
   - Premultiplied alpha for crisp edges; DPI awareness to avoid blur.
   - Visuals improved; drag remained unreliable.

4) Screen‑space drag and movement detection
   - Switched to `GetCursorPos()` for deltas (screen coords), computed movement from starting screen position; compared window rect before/after to infer movement.
   - Added `SetWindowPos` when moving to ensure position change is applied.
   - Result: user still reports any interaction restores; no drag.

5) OS‑level dragging via hit‑test
   - Return `HTCAPTION` on `WM_NCHITTEST` so Windows moves the window natively when dragging anywhere on the overlay.
   - On UP, check if the rect changed; only restore if not moved and within quick‑click thresholds.
   - Result: still reports restore, no drag.

Hypotheses (why drag still fails)
H1) Message mismatch (non‑client vs client): Returning `HTCAPTION` may push the drag flow into non‑client messages (WM_NCLBUTTONDOWN/NCMOUSEMOVE). Our current logic watches client WM_LBUTTON* and doesn’t see the OS move lifecycle, leading us to classify interactions as quick‑clicks. Even with rect comparison, if OS never enters move (e.g., not enough motion) or if we never get a final state, we default to restore.

H2) Quick‑click condition too permissive: The duration/movement thresholds might still fire in edge cases (e.g., WM messages timing, high DPI). We may be evaluating “no movement” quickly before the OS move takes effect, or our movement measurement is off by coordinate transforms.

H3) Hit‑test return + client handling conflict: By both returning `HTCAPTION` and handling WM_LBUTTONDOWN/UP, we might be interfering with the system move loop. The OS expects DefWindowProc to handle these; our return of 0 for client messages could be benign or could short‑circuit expected transitions on some systems.

H4) Layered window nuance: Some combinations of styles (`WS_EX_TOOLWINDOW`, topmost, layered) can influence hit‑testing/drag. We haven’t tried alternate style combos or explicit `SendMessage(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, lparam)` to initiate a move.

H5) Tk topmost interactions: The parent Tk window is set `-topmost`. Although we clear it for dialogs, there could be interactions that affect focus or mouse capture at the moment of minimize/overlay show on some desktops.

Concrete Next Steps (seeking outside input)
NS1) Message‑flow instrumentation (targeted)
  - Temporarily log all of: WM_NCHITTEST return, WM_NCLBUTTONDOWN/UP/MOVE, WM_LBUTTONDOWN/UP/MOVE, window rect at DOWN/UP, and quick‑click decision (moved? duration? pixels?).
  - This will tell us which path is actually occurring on user machines and why movement isn’t recognized.

NS2) Pure OS‑move initiation (no client handling)
  - Do not implement any WM_LBUTTON* logic. On client `WM_LBUTTONDOWN`, call `SendMessage(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)` and return DefWindowProc for everything (let Windows handle the full move). Only implement WM_NCLBUTTONUP to decide on quick‑click vs restore (or require double‑click to restore).

NS3) Change restore gesture
  - Avoid “single quick‑click restores” on layered path; require double‑click to restore. This removes ambiguity between “start drag” vs “click” completely. Many tray/overlay UIs use double‑click for restore by design.

NS4) Style variations
  - Try removing `WS_EX_TOOLWINDOW` (or using `WS_EX_APPWINDOW`) to see if hit‑testing/drag behavior changes.
  - Verify we are not setting `WS_EX_TRANSPARENT` (we aren’t) and not using `WS_EX_LAYERED` incorrectly (we do use layered properly with UpdateLayeredWindow).

NS5) Fallback proof
  - Force the Tk overlay path and confirm drag works there reliably with a very low threshold (1 px) and “double‑click to restore”, to validate user hardware/mouse behavior isn’t the limiting factor.

References to Code
- Layered overlay: `src/services/win_overlay.py`
  - `_window_proc` (message handling), `_on_mouse_down/_move/_up` (manual logic), `_update_layered_window` (rendering), `create/move/hide/destroy` (lifecycle).
- Mini overlay integration: `src/ui/mini_overlay.py`
  - Chooses layered path on Windows, otherwise Tk fallback; centers overlay; schedules restore via Tk after().
- Window minimize handler: `src/ui/window.py` `_on_window_minimize()`.

Request for Suggestions
- Given the above, which approach would you recommend to guarantee dependable drag?
  - A) “SendMessage + DefWindowProc only” OS move path with no client handlers and double‑click to restore.
  - B) Keep HTCAPTION but move restore gesture to double‑click (eliminate quick‑click entirely on layered path).
  - C) Keep manual move, but rely solely on screen‑space deltas and suppress any restore logic (require a dedicated restore button/gesture).
  - D) Alternative style/flags you’ve used successfully with layered popup icons.

Environment Notes
- Python (Tk), pywin32, Pillow; Windows 10/11; DPI scaling 100–200%. DPI awareness is enabled at process start; Tk scaling set from monitor DPI. UpdateLayeredWindow uses premultiplied alpha BGRA.

