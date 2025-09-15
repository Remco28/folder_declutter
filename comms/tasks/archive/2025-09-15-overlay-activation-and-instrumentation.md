Title: Overlay activation and instrumentation — ensure layered path, add force modes, and make Tk drag reliable

Objective
- Ensure the native Windows layered overlay path actually activates on user machines by adding the missing dependency and clear selection logs. Provide a force switch for mode selection, and make the Tk fallback drag reliably update position for troubleshooting.

Why
- Logs show we are falling back to the Tk overlay and its drag position never changes. Likely causes: missing Pillow (required for layered path image + premultiply), silent fallbacks masking the root error, and Tk geometry not flushing. This task removes ambiguity and adds targeted visibility.

Scope
- Platform: Windows focus, but the Tk fallback improvements are cross‑platform and harmless.
- No visual/UX changes aside from clearer logs; layered path remains OS‑drag + double‑click restore.

Changes Required

Files
- requirements.txt
- src/ui/mini_overlay.py
- how_to_test.md (add troubleshooting steps)
- docs/ARCHITECTURE.md (brief note on env var switch)

1) Add missing dependency
- requirements.txt: add `Pillow` under Runtime. This is needed for `win_overlay` premultiply and `MiniOverlay._load_icon_as_pil()`.

2) Add overlay mode switch (env var)
- In `MiniOverlay.__init__`, read `DS_OVERLAY_MODE` from environment: values are `auto` (default), `layered`, `tk`.
  - `auto`: current behavior (try layered, fallback to Tk), but with stronger logging (below).
  - `layered`: force the layered path. If layered init or show fails at any point, raise/log the exception; do NOT silently fall back to Tk.
  - `tk`: force Tk fallback; do not attempt layered init.

3) Improve selection and error logging (INFO level)
- `MiniOverlay.__init__`:
  - Log platform and mode selection: e.g., `Overlay mode: auto (Windows detected)`.
  - After attempting to init layered: log `Using layered overlay` when successful, or `Layered overlay disabled: <reason>` on failure (include exception message).
- `MiniOverlay.show_centered_over` (layered branch):
  - On success (after `create()`): log `LayeredOverlay shown at (x,y), size WxH` (already for win_overlay). Keep it at INFO.
  - On exception: call `logger.exception("LayeredOverlay failed; falling back to Tk")` so stack trace is captured.

4) Add debug flag for verbose event/move logs
- Respect `DS_OVERLAY_DEBUG` env var (truthy values '1', 'true', 'yes'). When enabled:
  - In Tk fallback `_on_click/_on_drag/_on_release`, log: raw event coords (`event.x_root/y_root`), current and new geometry, and post‑flush `winfo_x/y()`.
  - On init, log Tk scaling (`root.tk.call('tk', 'scaling')`) and screen size.

5) Make Tk fallback drag reliably update
- After each `self.overlay.geometry(f"+{new_x}+{new_y}")` in `_on_drag`, call `self.overlay.update_idletasks()` to flush geometry so `winfo_x/y` reflect the change and the move is applied immediately.
- Keep the small threshold (3 px), bindings on both toplevel and label.

Documentation updates
- how_to_test.md: Add a short “Overlay troubleshooting” section showing how to force modes and enable debug logs:
  - PowerShell examples:
    - `$env:DS_OVERLAY_MODE = "layered"; python -m src.main`
    - `$env:DS_OVERLAY_MODE = "tk"; $env:DS_OVERLAY_DEBUG = "1"; python -m src.main`
  - Expected logs in each mode and what to look for.
- docs/ARCHITECTURE.md: Mention `DS_OVERLAY_MODE` and `DS_OVERLAY_DEBUG` in Integration/Runtime notes.

Acceptance Criteria
- With Pillow installed, on Windows and `DS_OVERLAY_MODE=auto`, the app logs `Using layered overlay` and shows the layered window; drag works and double‑click restores.
- With `DS_OVERLAY_MODE=layered`, any failure during layered init/show surfaces as an exception with a stack trace (no silent fallback).
- With `DS_OVERLAY_MODE=tk`, the fallback path is used; dragging the Tk overlay moves it immediately and logs positions when `DS_OVERLAY_DEBUG=1`.
- Logs clearly state which overlay path is active and why when not layered.

Out of Scope
- No per‑pixel hit‑testing; no changes to layered drag/restore behavior.
- No packaging changes beyond adding Pillow to requirements.

Notes for Developer
- Keep logs concise at INFO; use `logger.debug` for noisy per‑event details gated by `DS_OVERLAY_DEBUG`.
- Prefer `logger.exception` for the layered path failure in `show_centered_over` to capture stack traces.

