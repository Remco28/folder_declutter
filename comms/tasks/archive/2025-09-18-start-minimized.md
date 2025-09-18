# Task: Start Main Window Minimized

## Specification
- **Author:** Architect
- **Status:** SPEC READY

### 1. Objective
Launch the Kondor Decluttering Assistant with its main window minimized to the taskbar so it stays out of the way until the user needs it.

### 2. Scope & Constraints
- Applies to all platforms supported by Tk (Windows, macOS, Linux). No platform-specific branches unless needed.
- Do not alter saved geometry, DPI/scaling logic, or topmost/pass-through behaviors; when restored, the window should appear exactly as before these changes.
- Keep the implementation localized to the main application bootstrap—no changes to `MainWindow` or other services.

### 3. Required Changes
1. **File:** `src/main.py`
   - After the window is fully constructed (Tk root created, geometry/DPI adjustments complete, `MainWindow` instantiated and packed) but before entering the main loop, ensure the root window is minimized.
   - Use `root.update_idletasks()` immediately before calling the minimize method so Tk finishes creating the native window.
   - Invoke `root.iconify()` (or equivalently `root.state('iconic')`) to start the process minimized.
   - Guard the call with a try/except that logs a warning if minimization fails, but still proceeds to `mainloop()`.
   - Leave the existing logging statements intact; optionally add a brief info/debug log once minimization succeeds.

### 4. Pseudocode
```python
# ... after app.pack(...)
try:
    root.update_idletasks()
    root.iconify()
    logger.info("Application started minimized")
except Exception as exc:
    logger.warning("Failed to start minimized: %s", exc)

root.mainloop()
```

### 5. Acceptance Criteria
- When the app launches, the taskbar shows the minimized window immediately; restoring it yields the normal UI with all functionality intact.
- No regressions in DPI scaling, geometry, or pass-through behavior when the user restores the window.
- Non-Windows platforms behave the same (minimized window) without raising errors.

### 6. Test Guidance
- Manual: Run `python -m folder_declutter.main`; confirm the window is minimized at startup and restores cleanly. Repeat on Windows (primary target) and, if available, another platform.
