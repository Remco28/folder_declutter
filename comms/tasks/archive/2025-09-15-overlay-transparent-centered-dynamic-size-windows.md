Title: Phase 10B — Overlay logo transparency, centering, and dynamic size (Windows)

Objective
- Render the minimized overlay as a logo-only, non-rectangular window on Windows (no white box), centered over the main window’s position when minimized.
- Make the overlay logo much closer to its original size, scaling dynamically for higher-resolution displays.
- Keep the overlay draggable and click-to-restore; do not move the main window when the overlay is dragged.

Scope
- Windows-only behavior. Provide a safe fallback for other platforms if encountered, but Windows is the target.
- No behavior changes to the main window other than minimize → overlay and restore as already implemented.

User Stories
- As a user, when I minimize the app, I want to see just the app logo floating where the app was (centered over it), not a white rectangle.
- As a user on high-DPI or 4K displays, I want the logo to scale up appropriately so it’s clearly visible.
- As a user, I want to drag the minimized logo to move it out of the way, and a simple click restores the app to its previous position.

Files and Functions
- src/ui/mini_overlay.py
  - Update overlay window attributes to support transparent, logo-only rendering on Windows.
  - Update image loading/scaling logic to support dynamic sizing and preserve PNG transparency.
  - Add API to place the overlay centered over a reference rect (the main window geometry).
- src/ui/window.py
  - On minimize, compute main window geometry and invoke the new centered overlay API.
  - On restore, keep current restore logic; do not modify the main window’s stored geometry based on overlay drags.
- resources/icon.png
  - Source asset; no change required. Ensure code uses this RGBA PNG for overlay rendering.

Technical Requirements
1) Transparent, logo-only overlay (Windows)
   - Create a borderless top-level: `Toplevel(overrideredirect=True)`, `attributes('-topmost', True)`.
   - Use chroma-key transparency via `wm_attributes('-transparentcolor', TRANSPARENT_KEY)` on Windows.
     - Set both the `Toplevel` and the child widget background to `TRANSPARENT_KEY` (e.g., `#FF00FF`).
     - Ensure no other controls paint non-transparent pixels outside the logo area.
   - Draw the PNG with alpha (RGBA) using Pillow `ImageTk.PhotoImage` when available; fallback to Tk `PhotoImage` if Pillow is missing.
   - Known limitation: chroma-key transparency yields crisp shapes but can produce slight edge halos for semi-transparent pixels because Tk composites against the widget background before transparency. This is acceptable for this phase. If unacceptable visually, we will follow up with a per-pixel alpha, layered-window enhancement.

2) Size closer to original, dynamic on high-res
   - Compute a dynamic target size from screen resolution:
     - Let `min_dim = min(screen_width, screen_height)`.
     - `target = round(min_dim / 4.2)`.
     - Clamp to `[192, 512]` and never exceed the image’s natural size; do not upscale.
     - Examples: 1080p ≈ 257 px, 1440p ≈ 343 px, 4K ≈ 514 px (clamped to 512).
   - Use Pillow LANCZOS for high-quality downscaling when available; otherwise use Tk zoom/subsample fallback.
   - Maintain aspect ratio of the source PNG.

3) Centered placement over main window on minimize
   - Before `withdraw()` on minimize, read main window geometry: `x, y, w, h`.
   - Overlay must compute its own rendered image size `(ow, oh)` and position its top-left at:
     - `ox = x + (w - ow) // 2`, `oy = y + (h - oh) // 2`.
   - Always center over the main window on each minimize event; ignore any prior overlay `last_position` for this entry point.

4) Draggable overlay; click-to-restore
   - Preserve existing drag threshold and movement logic on the overlay only; do not update main window geometry based on overlay drags.
   - Single click (no drag) restores: hide overlay, deiconify + focus main window.

5) Fallbacks and guards
   - If Windows-specific transparency attributes are unavailable (unexpected), fall back to the current rectangular overlay with no background fill change; still center it per requirement.
   - All errors should be logged and fail safe.

Pseudocode / Implementation Sketch
- mini_overlay.py
  - TRANSPARENT_KEY = '#FF00FF'
  - def _load_and_scale_icon():
      - Determine `target` using the dynamic size formula.
      - Try PIL: `Image.open('resources/icon.png').resize((tw, th), LANCZOS)` preserving alpha → `ImageTk.PhotoImage`.
      - Fallback: Tk `PhotoImage(file=...)` and zoom/subsample to approximate `target`.
      - Store resulting `self.icon_image` and `self.icon_size = (ow, oh)`.
  - def show_centered_over(rect: tuple[int,int,int,int]):
      - Ensure `self.overlay` created with `overrideredirect(True)`, `attributes('-topmost', True)`, and `bg=TRANSPARENT_KEY`.
      - On Windows: `self.overlay.wm_attributes('-transparentcolor', TRANSPARENT_KEY)`.
      - Create a `Label` (or `Canvas`) with `image=self.icon_image`, `bg=TRANSPARENT_KEY`, `bd=0`, `highlightthickness=0`.
      - Compute `(ox, oy)` using `(ow, oh)` and supplied `rect`.
      - `geometry(f'+{ox}+{oy}')`, `deiconify()`. Bind drag/click as today.
  - def show(x=None, y=None):
      - Retain as-is for explicit placement; do not auto-center here.

- window.py
  - In `_on_window_minimize`:
      - Before `withdraw()`, compute `x = parent.winfo_x()`, `y = parent.winfo_y()`, `w = parent.winfo_width()`, `h = parent.winfo_height()`.
      - Call `self._mini_overlay.show_centered_over((x, y, w, h))`.
      - Then `withdraw()` the main window. If event sequencing requires, compute geometry first, then withdraw, then show overlay.
  - In `_on_overlay_restore`:
      - Hide overlay, `deiconify()`, `lift()`, `focus_force()` as currently implemented. Do not move the main window.

Acceptance Criteria
- When the app is minimized on Windows, the overlay shows only the logo without a white rectangular background.
- The overlay appears centered over the main window’s last position at the moment of minimize.
- The overlay’s size is substantially larger than before on high-resolution displays, following the dynamic sizing rules; no upscaling beyond the source size.
- Dragging the overlay moves only the overlay; a single click restores the main window to its previous position.
- Fallback behavior remains functional if Windows transparency attributes are unavailable (no crashes).

QA Notes
- Test on Windows 10/11 with 100%, 150%, and 200% display scaling.
- Verify edge rendering quality of the PNG. If edge halos are pronounced, flag for a follow-up phase to implement a per-pixel alpha layered window.
- Verify that repeated minimize/restore cycles always re-center the overlay over the main window position regardless of where the overlay was dragged previously.

Docs
- Update how_to_test.md to include the above checks and note the dynamic size formula.
- Update docs/ARCHITECTURE.md overlay section with Windows transparency approach and limitations, plus a note on potential layered-window enhancement.

Out of Scope
- Implementing per-pixel alpha via Win32 layered windows (defer to a follow-up if needed).

