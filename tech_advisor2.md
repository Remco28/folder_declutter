  - What’s good
      - Layered window with premultiplied BGRA and DPI awareness yields crisp visuals.
      - Topmost/toolwindow flags and Tk thread handoff via after() are sensible.
      - Clear hypotheses and next steps captured in the report.
  - Top risks
      - Mixed drag paths (manual WM_LBUTTON* + OS drag via HTCAPTION) conflict and misclassify interactions as “click” → restores too often.
  Severity: high.
      - Client vs non‑client mismatch: you return HTCAPTION but handle only client messages (WM_LBUTTON*/WM_MOUSEMOVE). OS move lifecycle uses
  non‑client (WM_NC*) and WM_(ENTER|EXIT)SIZEMOVE. Severity: high.
      - Single quick‑click restore is inherently ambiguous with drag start thresholds. Severity: medium‑high.
      - Missing double‑click class style may prevent reliable *DBLCLK handling. Severity: medium.

  Concrete actions (do now)

  1. Use pure OS-managed move; remove manual drag

  - In src/services/win_overlay.py::_window_proc:
      - Keep WM_NCHITTEST but do not mix manual movement. Easiest reliable pattern:
          - On WM_LBUTTONDOWN: win32gui.ReleaseCapture(); win32gui.SendMessage(hwnd, win32con.WM_NCLBUTTONDOWN, win32con.HTCAPTION, lparam); return
  0
          - Let DefWindowProc handle the whole move loop. Do not handle WM_MOUSEMOVE/WM_LBUTTONUP for movement.
      - Alternatively, rely solely on returning HTCAPTION and don’t intercept WM_LBUTTON* at all. Key is: pick one path and don’t mix.

  2. Switch restore to double‑click (eliminate quick‑click)

  - In window class registration: wc.style = win32con.CS_DBLCLKS so double‑click messages are generated.
  - Handle WM_NCLBUTTONDBLCLK or WM_LBUTTONDBLCLK to trigger on_restore() via Tk after. Do not restore on single click.

  3. Track move loop for future disambiguation (optional but robust)

  - Add self.in_move_loop flag:
      - On WM_ENTERSIZEMOVE: self.in_move_loop = True
      - On WM_EXITSIZEMOVE: self.in_move_loop = False
  - If you ever re‑enable single‑click restore, only fire when in_move_loop stayed False.

  4. Add targeted instrumentation (temp)

  - Log: WM_NCHITTEST result; WM_(N)CLBUTTONDOWN/UP; WM_(ENTER|EXIT)SIZEMOVE; window rect at DOWN/UP; and whether restore fired. This will confirm
  message flow on user machines.

  5. Optional: per‑pixel hit‑testing

  - For better UX, in WM_NCHITTEST return HTTRANSPARENT for fully transparent pixels and HTCAPTION only on visible pixels. This avoids “grabbing”
  empty regions.

  Notes on styles/flags

  - Keep: WS_POPUP, WS_EX_LAYERED, WS_EX_TOPMOST, WS_EX_TOOLWINDOW (to stay out of Alt‑Tab).
  - Optional: try WS_EX_NOACTIVATE if you want to avoid focus steals; verify that dragging still works for your scenario (it typically does, but
  test).
  - Moving the window: let the OS do it. Avoid calling _update_layered_window during drag; do not compute client deltas yourself.

  Targeted edits in src/services/win_overlay.py

  - Add: during class registration wc.style = win32con.CS_DBLCLKS.
  - Replace mouse handling to:
      - Remove _on_mouse_* usage from _window_proc for drag and quick‑click.
      - Add WM_LBUTTONDOWN handler that forwards to WM_NCLBUTTONDOWN (or drop it and rely purely on HTCAPTION).
      - Add WM_(N)CLBUTTONDBLCLK to invoke on_restore().
      - Add WM_ENTERSIZEMOVE/WM_EXITSIZEMOVE to flip self.in_move_loop (useful if you later want single‑click semantics).

  Validation steps

  - Drag test: Verify logs show WM_NCLBUTTONDOWN then WM_ENTERSIZEMOVE → WM_EXITSIZEMOVE. Overlay moves smoothly; no restore occurs.
  - Restore test: Double‑click anywhere on overlay triggers on_restore() reliably across DPI 100–200%.
  - Optional: With per‑pixel hit test, ensure clicking fully transparent pixels does nothing.
