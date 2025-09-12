# Phase 3 Spec — Windows Pass-Through (pywin32)

Status: SPEC READY
Owner: Architect
Date: 2025-09-12

## Objective
Implement Windows click pass-through for the Tk window using pywin32. The window should not intercept clicks when idle; we will later disable pass-through during drag-over (Phase 5). In this phase, build the Windows integration service and safe state transitions, with an optional developer-only keybind for testing.

## Behavior
- When pass-through is enabled, clicks on the app surface fall through to the underlying window.
- Pass-through is automatically disabled when the app shows a modal dialog (e.g., folder picker, label prompt) and re-enabled afterward.
- Developer-only testing: when `DS_DND_DEBUG=1`, `Ctrl+Alt+P` toggles pass-through on/off to verify the effect (not shown in the UI; no persistent toggle in product).

## Integration Notes
- Use `pywin32` to obtain the HWND of the Tk root and set extended window styles:
  - Enable pass-through: set `WS_EX_TRANSPARENT` and `WS_EX_LAYERED` bits via `SetWindowLongPtr(GWL_EXSTYLE, ...)`.
  - Disable pass-through: clear `WS_EX_TRANSPARENT` bit; retain always-on-top if set.
- Ensure no tight polling; operations occur on UI thread via Tk `after` callbacks.

## Files and Modules
Create
- `src/services/win_integration.py`
  - Functions:
    - `get_hwnd(tk_root) -> int`
    - `enable_pass_through(hwnd) -> None`
    - `disable_pass_through(hwnd) -> None`
    - `set_always_on_top(hwnd, on: bool) -> None` (optional helper)
  - Class `PassThroughController` with methods:
    - `attach(tk_root)` → retrieves HWND and wires focus/dialog hooks
    - `enable()` / `disable()` → idempotent
    - `temporarily_disable_while(func)` → context manager to disable during dialogs
  - Must no-op gracefully on non-Windows (import guard), logging a warning once.

Modify
- `src/main.py`
  - After creating Tk root, instantiate `PassThroughController` and attach it.
  - On startup, call `controller.enable()` (Windows only).
  - If env `DS_DND_DEBUG=1`, bind `Ctrl+Alt+P` to toggle enable/disable for manual testing.
- `src/ui/window.py`
  - Wrap calls that open dialogs (add section, change location, rename) with `controller.temporarily_disable_while(...)` so UI remains interactive during prompts.
  - Controller should be passed into `MainWindow` (new optional parameter) or exposed via a small app context.

## Acceptance Criteria (Windows 10/11)
- With the app over a clickable window (e.g., Notepad), pass-through enabled causes clicks to land in the underlying window.
- After invoking any app dialog, the UI is clickable until the dialog closes; then pass-through re-enables automatically.
- `DS_DND_DEBUG=1` + `Ctrl+Alt+P` visibly toggles behavior without crashes.
- Non-Windows: app runs normally; logs one warning that pass-through is disabled.

## Pseudocode
```
def get_hwnd(tk_root):
    # Use tk_root.wm_frame() or .winfo_id(); wrap via pywin32 to ensure correct handle

def enable_pass_through(hwnd):
    ex = GetWindowLong(hwnd, GWL_EXSTYLE)
    SetWindowLong(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED | WS_EX_TRANSPARENT)

def disable_pass_through(hwnd):
    ex = GetWindowLong(hwnd, GWL_EXSTYLE)
    SetWindowLong(hwnd, GWL_EXSTYLE, ex & ~WS_EX_TRANSPARENT)

class PassThroughController:
    def attach(self, tk_root): self.hwnd = get_hwnd(tk_root)
    def enable(self): enable_pass_through(self.hwnd)
    def disable(self): disable_pass_through(self.hwnd)
    @contextmanager
    def temporarily_disable_while(self, func):
        self.disable()
        try: return func()
        finally: self.enable()
```

## Test Checklist (manual)
- Place the window over Notepad; click on tiles → with pass-through enabled, clicks reach Notepad; after opening a dialog (add section), clicks operate on the app until dialog closes, then pass-through resumes.
- Toggle in debug mode to confirm no style flicker or crashes.
- Verify no-op behavior on non-Windows environments.

