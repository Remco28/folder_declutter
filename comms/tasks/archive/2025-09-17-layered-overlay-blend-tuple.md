# Layered Overlay Blend Tuple Fix

## Context
- The previous fix attempted to construct a `BLENDFUNCTION` struct with `ctypes` and pass `ctypes.byref(blend)` into `win32gui.UpdateLayeredWindow`.
- Pywin32's wrapper expects the fourth parameter to be a tuple of four `BYTE` values, not a pointer. Passing the struct now raises `TypeError: BLENDFUNCTION must be a tuple of four small ints (0-255)` and the mini overlay still falls back to the Tk path.
- We only need to supply the blend coefficients; pywin32 will marshal the tuple into the Win32 `BLENDFUNCTION` internally.

## Objective
Restore the layered overlay by providing the blend data as a tuple, ensuring compatibility with modern pywin32 while keeping per-pixel alpha.

## Changes Required
- File: `src/services/win_overlay.py`
  - Remove the custom `BLENDFUNCTION` `ctypes.Structure` definition.
  - In `_update_layered_window()`, build the blend tuple `(win32con.AC_SRC_OVER, 0, 255, win32con.AC_SRC_ALPHA)` and pass it directly to `UpdateLayeredWindow` instead of `ctypes.byref(...)`.
  - Add a concise inline comment noting that pywin32 expects a 4-tuple and handles the struct marshalling.
  - Clean up any now-unused imports or helpers introduced for the struct if they are no longer needed.

## Constraints / Notes
- Keep the Windows-only guard intact; avoid touching non-Windows code paths or the Tk fallback.
- Maintain existing logging and error handling.
- Ensure the blend tuple uses literal ints in the 0–255 range.

## Acceptance Criteria
- Minimize-to-overlay on Windows no longer raises the `TypeError`, and the native layered overlay renders with transparency.
- No regressions in other overlay functionality (move, destroy, etc.).
- Project tests/checks remain green.
