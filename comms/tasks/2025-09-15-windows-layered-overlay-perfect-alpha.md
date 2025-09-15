Title: Phase 10C — Windows layered overlay with per‑pixel alpha (perfect edges)

Objective
- Eliminate edge halos by replacing chroma‑key transparency with a Windows layered window that uses per‑pixel alpha (ARGB). The minimized overlay renders the PNG exactly, with smooth edges and full alpha fidelity.

Scope
- Windows‑only. Keeps existing Tk overlay path as a fallback behind a capability flag.
- Preserves all current UX: centered over main window on minimize, dynamic sizing, drag‑to‑move, click‑to‑restore.

User Stories
- As a user, I want the minimized logo to render crisply with smooth edges on any background, without the magenta halo seen with chroma‑keying.

Files and Functions
- New: `src/services/win_overlay.py`
  - `class LayeredOverlay`: Creates and manages a native layered window (WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST) that displays an ARGB bitmap via `UpdateLayeredWindow`.
  - Key methods:
    - `create(image: PIL.Image, x: int, y: int) -> None` — Creates window and paints image.
    - `move(x: int, y: int) -> None` — Repositions window.
    - `show() / hide() / destroy()` — Visibility and cleanup.
    - Internal mouse handling: WM_LBUTTONDOWN/WM_MOUSEMOVE/WM_LBUTTONUP to support drag and click detection.
    - Resource management: create HBITMAP from PIL image, select into a memory DC, call `UpdateLayeredWindow` with `BLENDFUNCTION(AC_SRC_OVER, AC_SRC_ALPHA)`.
  - Implementation with `pywin32` (win32gui, win32con, win32api) or `ctypes` where needed.

- Update: `src/ui/mini_overlay.py`
  - Add a Windows‑only code path that prefers `LayeredOverlay` when available; fallback to current Tk Toplevel chroma‑key variant if initialization fails.
  - Reuse existing dynamic sizing and centering logic to compute the final RGBA image to pass to `LayeredOverlay.create`.
  - Keep the same drag threshold and click‑to‑restore behavior; for the layered window path, route events via the window proc in `LayeredOverlay` and call back into the same `on_restore` callback.
  - API remains: `show_centered_over(rect)`, `show(x,y)`, `hide()`.

- No change: `src/ui/window.py`
  - Continue to compute geometry before `withdraw()` and call `show_centered_over((x,y,w,h))`.

Technical Requirements
1) Window creation
   - Create an owned, borderless `WS_POPUP` window class with `WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST`.
   - Do not apply `WS_EX_TRANSPARENT`; we need hit‑testing for drag/click.
   - Keep Z‑order topmost while visible.

2) Per‑pixel alpha blit
   - Load `resources/icon.png` as RGBA with Pillow; apply dynamic sizing rule from Phase 10B (min_dim/4.2, clamped [192,512], no upscale, preserve aspect).
   - Convert PIL image to a 32‑bit DIB section (BGRA) and select into a memory DC.
   - Call `UpdateLayeredWindow(hwnd, hdcSrc, (x,y), (w,h), hdcMem, (0,0), 0, BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA), ULW_ALPHA)`.
   - Release all GDI objects reliably (SelectObject original, DeleteObject HBITMAP, DeleteDC, ReleaseDC).

3) Input handling
   - Implement a window proc to handle mouse messages:
     - WM_LBUTTONDOWN: record position, set capture, start potential drag.
     - WM_MOUSEMOVE: if capture and movement > threshold, move window by delta.
     - WM_LBUTTONUP: release capture; if not dragged, invoke `on_restore` callback on the Tk thread via `after(0, ...)`.
   - Support hit‑testing over the full client area; optional: ignore fully transparent pixels for hit‑testing in a later phase.

4) Centering & lifecycle
   - `MiniOverlay.show_centered_over(rect)` computes top‑left `(ox, oy)` from icon size and creates/moves the layered window to that point; shows it.
   - `hide()` destroys or hides the layered window and frees resources.
   - Do not change main window geometry based on overlay drags.

5) Fallbacks
   - If any step fails (missing Pillow/pywin32 or API error), log and fall back to the current chroma‑key Tk overlay path.

6) Packaging
   - Ensure `pywin32` and `Pillow` are included for the bundled build. If Pillow is missing at runtime, the feature should fall back cleanly.

Acceptance Criteria
- Overlay edges render smoothly with full alpha (no magenta/white halos) on any desktop background.
- Centering on minimize and dynamic sizing match Phase 10B behavior.
- Dragging moves only the overlay; a single click restores the main window.
- Works correctly on Windows 10/11 at 100%, 150%, 200% scaling.
- Fallback to chroma‑key overlay if layered path is unavailable, with clear WARN logs.

QA Notes
- Visual inspection against dark/light/photographic wallpapers.
- Repeated minimize/restore cycles; verify no resource leaks (watch GDI object count in Task Manager → Columns → GDI Objects).
- DPI changes: test moving between monitors with different scale factors; minimize/restore after move.

Out of Scope
- Pixel‑perfect hit‑test that ignores fully transparent pixels (potential Phase 10D).
- Animation or fade‑in/out effects.

