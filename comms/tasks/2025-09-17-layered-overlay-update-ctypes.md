# Layered Overlay UpdateLayeredWindow Fallback

## Context
- Passing the blend tuple solved the earlier type mismatch, but `win32gui.UpdateLayeredWindow` now returns `0` (failure). The mini overlay keeps falling back to the Tk path.
- The failure indicates the underlying Win32 call is rejecting one of the parameters, yet the wrapper surfaces only a `RuntimeError("UpdateLayeredWindow failed")` without exposing the real Windows error code.
- The pywin32 helper has been flaky across releases (we already lost `BLENDFUNCTION`), so we should call the User32 API directly via `ctypes`, where we control the structures exactly and can capture `GetLastError()` for diagnostics.

## Objective
Switch the layered overlay update path to a direct `ctypes` call to `UpdateLayeredWindow`, log detailed Windows error information when it fails, and ensure we pass correctly-marshalled `POINT`, `SIZE`, and `BLENDFUNCTION` structs.

## Changes Required
- File: `src/services/win_overlay.py`
  1. Inside the Windows-only import block:
     - Import `ctypes` and `from ctypes import wintypes` (shared by `_create_argb_bitmap`).
     - Define reusable `class BLENDFUNCTION(ctypes.Structure)` and, if convenient, lightweight helpers/aliases for `POINT` and `SIZE` (either via `wintypes.POINT`/`SIZE` or explicit `ctypes.Structure`). Retain existing comments about pywin32 behaviour.
  2. Update `_update_layered_window()` to:
     - Build `dest = wintypes.POINT(x, y)` (or equivalent) and `size = wintypes.SIZE(self.width, self.height)`.
     - Build `src_pos = wintypes.POINT(0, 0)`.
     - Instantiate `blend = BLENDFUNCTION(win32con.AC_SRC_OVER, 0, 255, win32con.AC_SRC_ALPHA)`.
     - Call `ctypes.windll.user32.UpdateLayeredWindow` (store the function once for reuse if you prefer) passing pointers via `ctypes.byref(...)`.
     - On failure (`result == 0`), fetch `last_error = ctypes.windll.kernel32.GetLastError()` and include both the numeric code and `win32api.FormatMessage(last_error).strip()` in the log before raising. Make sure to reset `last_error` to 0 before the call (`ctypes.windll.kernel32.SetLastError(0)`) so we don't report stale values.
  3. Remove the temporary blend tuple logic and any now-unused imports resulting from that change.
  4. Ensure `_create_argb_bitmap()` continues to work with the shared `ctypes` import (no behavioural change expected aside from moving the import).

## Constraints / Notes
- Keep all functionality guarded by `WINDOWS_AVAILABLE` so non-Windows platforms still raise the existing runtime error.
- Do not alter window creation, fallback behaviour, or drag logic; only touch the blend/update portion and logging.
- Use concise logging—single info-level line when successful (current logging is fine) and detailed error line when failing.

## Acceptance Criteria
- `UpdateLayeredWindow` succeeds on Windows so the layered overlay renders instead of dropping to the Tk fallback.
- If Windows still rejects the call, logs now show the underlying `GetLastError()` code/message to aid debugging.
- All existing tests/checks remain green.
