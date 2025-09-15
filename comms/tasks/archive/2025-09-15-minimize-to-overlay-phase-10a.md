# Phase 10A Spec — Minimize to Overlay (Floating Logo)

Status: SPEC READY
Owner: Architect
Date: 2025-09-15

## Objective
When the main window is minimized, show a small floating, always‑on‑top overlay with the app logo. The overlay can be dragged to reposition and clicked to restore the main window. Logo size should adapt to screen resolution (with sensible bounds).

## Scope
- Add a dedicated overlay component.
- No drag‑and‑drop support on the overlay in this phase.
- Session‑only position memory (optional persistent position is a future enhancement).

## Files To Add
- `src/ui/mini_overlay.py` — encapsulate the overlay Toplevel.

## Files To Modify
- `src/ui/window.py` — wire window state changes (minimize/restore) to show/hide overlay.
- `docs/ARCHITECTURE.md` — document overlay component and lifecycle.

## Behavior & Requirements
1) Overlay window
   - Implement as a borderless `tk.Toplevel` with `overrideredirect(True)` and `-topmost True`.
   - Contains a clickable `tk.Label` with the app icon loaded from `resources/icon.png`; if icon missing or cannot be scaled, show a simple text fallback (e.g., "DS").
   - Left‑click restores the main window (deiconify + raise + focus) and hides/destroys the overlay.
   - Dragging: user can click‑and‑drag anywhere on the overlay to move it; use a small motion threshold to distinguish drag from click.

2) Size adaptation
   - Compute target size from screen resolution: `target = clamp(round(min(screen_w, screen_h) * 0.04), 32, 96)`.
   - Attempt to scale the icon to `target` x `target`.
     - Prefer Pillow (if available) for high‑quality scaling: `Image.resize(..., LANCZOS)`; DO NOT add Pillow as a dependency; only use it if present.
     - Otherwise, fall back to `tk.PhotoImage` subsample/zoom to approximate, or pick among 3 preset sizes by nearest rounding.

3) Show/hide lifecycle
   - On main window minimize (`<Unmap>` or `iconify`), withdraw/hide the main window and show the overlay at bottom‑right with a small margin (e.g., 16 px). Maintain `always on top`.
   - On overlay click, restore: deiconify the main window, raise, focus, and destroy the overlay.
   - Do not enable pass‑through on the overlay; it must be clickable.

4) Positioning
   - Default position: bottom‑right (account for panel/taskbar with a margin).
   - During the session, remember last dragged position for subsequent minimize events.

5) Logging
   - Log overlay show/hide, restore clicks, and drag end (final position).

## Class/API Sketch (`src/ui/mini_overlay.py`)
```python
class MiniOverlay:
    def __init__(self, parent_root, on_restore: Callable[[None], None], logger=None):
        # create toplevel, load scaled icon, bind drag/click

    def show(self, x=None, y=None) -> None:  # position and deiconify overlay
        ...

    def hide(self) -> None:  # destroy/withdraw overlay
        ...

    def set_last_position(self, x: int, y: int) -> None:  # optional helper
        ...
```

Integration in `MainWindow`:
- Track `self._overlay` and optional `self._overlay_pos`.
- Bind to minimize: `parent.bind('<Unmap>', ...)` or override WM_DELETE/WM_STATE; when `parent.state() == 'iconic'` or upon minimize action, create `MiniOverlay` and show.
- On restore: handler calls back `on_restore` to deiconify main window and then `overlay.hide()`.

## Acceptance Criteria
1) Minimizing the app hides the main window and shows a small floating logo overlay on top of other windows.
2) Clicking the overlay restores the main window and hides the overlay.
3) The overlay can be dragged to reposition; subsequent minimizations in the same session reuse the last position.
4) Logo scales with screen resolution within 32–96 px bounds; if scaling is unavailable, overlay still shows a readable fallback.

## Manual Test Checklist
- Minimize → overlay appears bottom‑right; click → restores.
- Drag overlay to a new position; minimize again → overlay reappears at last position for this session.
- On high‑res and low‑res displays, overlay size adjusts within bounds.
- Remove/rename `resources/icon.png` → overlay shows text fallback and remains functional.

