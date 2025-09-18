Title: Softer main window refresh

Intent:
- Make the main window feel friendlier and higher contrast on hi-res monitors without losing the minimalist grid layout
- Improve the prominence and usability of the bottom controls, especially the Recycle Bin and Undo actions
- Tighten the default window sizing so the app opens narrower but still scales gracefully

Target:
- Route(s): Desktop app main window
- Component(s): src/main.py, src/ui/window.py, src/ui/section.py

Run: AUTO

Scope: markup allowed

References:
- comms/current UI.png
- resources/recycle.png

Acceptance Criteria:
- Recycle control: replace the emoji label with the provided recycle PNG, scale the image proportionally based on current window width (re-render on toplevel `<Configure>`), and present it inside a widened pill-style button (>=48 px tall) with comfortable padding that reads clearly at 125–150% DPI.
- Bottom control bar: share a consistent styling for Recycle and Undo (matching background, border, and hover state), increase Undo button font size and padding by ~25%, and keep both controls centered/right-aligned within a taller (≥56 px) bar.
- Visual softening: lighten the root and tile backgrounds (e.g., root `#f4f6f8`, tiles `#ffffff`), reduce tile border heaviness (1 px neutral grey) while keeping hover/active cues, and standardize primary font to a friendly sans-serif (Segoe UI on Windows, fallback to Arial elsewhere) at 11–12 pt.
- Window sizing: default geometry opens at ~680 px width (same height as current) and respects a reduced min width (~620 px) so the layout roughly matches the reference screenshot when first launched; grid should continue to expand responsively.
- Maximize button: on Windows only, remove the native maximize button via window style manipulation while preserving resize handles and working minimize/close buttons; no change needed on other platforms.

Constraints:
- Reuse existing dependencies (tkinter, Pillow, ctypes) and keep styling logic within the listed components.

Notes:
- Ensure recycle image assets are loaded once and resized via Pillow before wrapping in `PhotoImage` to avoid Tkinter cache issues.
