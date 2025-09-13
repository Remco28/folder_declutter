# Phase 3.1 Spec — Pass-Through Stabilization (Windows Rendering)

Status: SPEC READY
Owner: Architect
Date: 2025-09-13

## Objective
Fix a Windows rendering issue where the Tk window appears blank when pass-through is enabled. Simplify the implementation to avoid `WS_EX_LAYERED` side effects and ensure clean enable/disable transitions.

## Background
Phase 3 implemented pass-through by setting both `WS_EX_TRANSPARENT` and `WS_EX_LAYERED`. On some Windows/Tk builds, enabling `WS_EX_LAYERED` without also calling `SetLayeredWindowAttributes` causes the client area not to paint, making the window appear blank. Disabling pass-through cleared only `WS_EX_TRANSPARENT`, leaving `WS_EX_LAYERED` set, which can preserve the blank state.

## Approach
Adopt a minimal and robust approach:
- Use only `WS_EX_TRANSPARENT` for pass-through click-through.
- Do not set `WS_EX_LAYERED` at enable.
- At disable, explicitly clear both `WS_EX_TRANSPARENT` and `WS_EX_LAYERED` (defensive cleanup in case it was set previously).
- Keep always-on-top behavior managed by Tk (`root.attributes('-topmost', True)`). Do not change z-ordering here.

## Files To Modify
- `src/services/win_integration.py`
  - In `enable_pass_through(hwnd)`: remove `WS_EX_LAYERED` from the bitmask; set only `WS_EX_TRANSPARENT`.
  - In `disable_pass_through(hwnd)`: clear both `WS_EX_TRANSPARENT` and `WS_EX_LAYERED`.
  - Optional (comment): brief note explaining why `WS_EX_LAYERED` is avoided unless paired with `SetLayeredWindowAttributes`.
- No changes required to other modules; existing `temporarily_disable_while(...)` logic remains valid.

## Expected Behavior
- With pass-through enabled, UI renders normally and clicks fall through to underlying windows.
- Disabling pass-through restores normal hit-testing and maintains correct rendering.
- Dialog interactions continue to temporarily disable pass-through and re-enable afterward.

## Acceptance Criteria
- Launch on Windows: `python -m src.main` shows the 2×3 grid, Recycle Bin, and Undo button with pass-through enabled.
- With `DS_DND_DEBUG=1`, `Ctrl+Alt+P` toggles pass-through; UI remains visible during both states (no blank window).
- After toggle cycles (enable/disable multiple times), rendering remains correct and no exceptions are logged.
- Non-Windows continues to no-op cleanly with a single warning.

## Test Checklist (manual)
1) Baseline render
   - Run `python -m src.main` → verify tiles render.
2) Debug toggle
   - Set `DS_DND_DEBUG=1`; re-run → press `Ctrl+Alt+P` several times; no blanking; logs reflect state.
3) Dialog coverage
   - Add Section → folder picker opens; after closing, pass-through re-enables; rendering persists.
4) Regression
   - Close and relaunch; repeat toggle and dialog tests; ensure stability.

## Notes
- We intentionally avoid `WS_EX_LAYERED` to prevent Tk painting issues. If layered windows are needed in the future (e.g., alpha/colorkey), they must be paired with `SetLayeredWindowAttributes` and tested against Tk.

