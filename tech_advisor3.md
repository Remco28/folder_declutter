  - What the logs show
      - You’re on the Tk fallback path, not the native layered window: “Tk overlay (fallback) shown centered at (1440, 693) …”. There’s no
  “LayeredOverlay shown …” line.
      - Every “Overlay dragged to” reads the exact same coords: (1440, 693). That’s the initial center, so the overlay’s position is not changing
  despite drag events.
  - Why drag “doesn’t work”
      - The native OS-move path (our recommendation) isn’t being exercised at all. Either LayeredOverlay.create(...) threw and you fell back, or
  use_layered is False (platform/import), or _load_icon_as_pil() returned None.
      - The Tk fallback’s drag handler runs, but the geometry never changes (or is immediately reset). Given the identical coordinates, either:
          - geometry("+x+y") isn’t taking effect (needs a flush like update_idletasks()), or
          - movement deltas (event.x_root/y_root) are not producing new positions (threshold not crossed or coords mismatch on DPI/multi‑monitor),
  or
          - some other code re-centers the window after release (less likely from current code).
  - Alignment with architect’s hypothesis
      - Agree: the issue you’re seeing here is not the layered window drag at all; it’s that the app is falling back to the Tk overlay and that
  overlay’s position never updates. Root cause to solve first is “Why are we in fallback?”
  - Concrete actions (do now)
      - Log selection and failures at INFO:
          - In MiniOverlay.__init__: log “Using layered overlay” vs “Layered overlay disabled (reason)”.
          - In show_centered_over: on success log “LayeredOverlay shown …”; on exception log the exception message and stack.
      - Force the layered path for validation:
          - Temporarily hard‑code self.use_layered = True and raise on any failure (no silent fallback) to surface the real error.
      - Instrument Tk fallback drag:
          - In _on_drag, log event.x_root/y_root, current_x/current_y, and new_x/new_y; after geometry(), call self.overlay.update_idletasks() and
  log winfo_x/y() to confirm the move sticks.
      - Quick Tk fallback tweaks (if you must keep it):
          - After each geometry(), call update_idletasks() to flush the move.
          - Ensure bindings are on the toplevel and label (you already do) and keep the threshold small (3px is fine).
          - If DPI scaling is on, confirm Tk’s scaling isn’t interfering: log self.parent_root.tk.call('tk', 'scaling') and screen size.
  - Native path checklist (once layered path is active)
      - Don’t mix manual WM_LBUTTON* with HTCAPTION; use OS move only.
      - Ensure wc.style = CS_DBLCLKS and trigger restore only on DBLCLK.
      - Optional: track WM_ENTERSIZEMOVE/WM_EXITSIZEMOVE to disambiguate moves vs clicks.
  - Likely root cause candidates for fallback
      - PIL image load/resize returned None or raised (bad path or missing Pillow).
      - Exception during CreateWindowEx or UpdateLayeredWindow (missing pixel format/DC resources).
      - Import failure (pywin32/Pillow) or platform.system() not returning “Windows” in the runtime environment.
