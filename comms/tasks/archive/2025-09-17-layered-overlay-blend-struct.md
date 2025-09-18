# Layered Overlay Blend Struct Fix

## Context
- After applying the null-brush fix, `LayeredOverlay._update_layered_window()` raises `AttributeError: module 'win32gui' has no attribute 'BLENDFUNCTION'` when constructing the per-pixel alpha blend descriptor.
- Pywin32 306+ no longer exposes a `BLENDFUNCTION` helper on `win32gui`; callers must provide the struct bytes themselves (typically via `ctypes`).
- The exception prevents the native layered overlay from updating and forces the Tk fallback.

## Objective
Create the `BLENDFUNCTION` structure manually (using `ctypes`) and pass it to `UpdateLayeredWindow` so the layered overlay path works again.

## Changes Required
- File: `src/services/win_overlay.py`
  - Define a small helper (module-level or inside the Windows-only block) that uses `ctypes.Structure` to represent `BLENDFUNCTION` with the four `BYTE` fields (`BlendOp`, `BlendFlags`, `SourceConstantAlpha`, `AlphaFormat`).
  - In `_update_layered_window()`, instantiate this struct with `AC_SRC_OVER`, `0`, `255`, and `AC_SRC_ALPHA`, then pass it to `UpdateLayeredWindow` using `ctypes.byref()`.
  - Add a brief comment clarifying why `ctypes` is used (pywin32 no longer exposes `BLENDFUNCTION`).
  - Ensure the helper only runs on Windows; do not break the non-Windows guard or introduce imports that run on Linux.

## Constraints / Notes
- Keep existing logging and error handling intact.
- Do not change the fallback behavior or other overlay logic.
- The struct creation should live in the Windows-available branch so non-Windows imports are avoided.

## Acceptance Criteria
- The layered overlay no longer raises `AttributeError` when minimized on Windows.
- The native overlay updates correctly with per-pixel alpha.
- Existing tests/checks continue to pass.
