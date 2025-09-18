# Layered Overlay WNDCLASS Brush Fix

## Context
- When the mini overlay tries the native layered overlay path, `LayeredOverlay.create()` registers a `WNDCLASS` and sets `wc.hbrBackground = None`.
- On Windows with pywin32 306+, assigning `None` raises `TypeError: Unable to convert NoneType to pointer-sized value`, aborting the layered overlay creation and forcing the Tk fallback.
- This regression prevents the transparent native overlay from appearing after minimize, causing a visual downgrade on Windows.

## Objective
Restore the layered overlay path by ensuring we pass a valid brush handle to `WNDCLASS.hbrBackground` while keeping the window fully transparent and avoiding paint flicker.

## Changes Required
- File: `src/services/win_overlay.py`
  - In `LayeredOverlay.create()`, replace the `wc.hbrBackground = None` assignment with a stock null brush handle (`win32gui.GetStockObject(win32con.NULL_BRUSH)`), or equivalent logic that yields an `HBRUSH` avoiding background fills.
  - Add a short code comment explaining why the null brush is used (prevent flicker, maintain transparency, and satisfy pywin32 handle requirements).
  - Keep the rest of the registration logic intact.

## Constraints / Notes
- Do not introduce additional module-level imports that break non-Windows platforms; keep the `WIN32_AVAILABLE` guard intact.
- Ensure the fix works for repeated registrations (the class may already exist); no change should be needed beyond the brush handle assignment.
- Avoid altering the fallback behavior or other overlay logic.

## Acceptance Criteria
- Running the mini overlay flow on Windows no longer raises `TypeError` when creating the layered overlay.
- The layered overlay window appears with expected transparency instead of falling back to Tk.
- Existing automated checks (if any) remain green.
