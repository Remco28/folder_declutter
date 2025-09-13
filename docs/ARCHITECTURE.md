# Desktop Sorter Architecture Overview

This document outlines the architecture of the Desktop Sorter application: a lightweight Windows-only utility built with Python (Tkinter + tkinterdnd2 + pywin32) and packaged with PyInstaller. The focus is on how components relate and where Windows integration occurs.

## System Components

### Core Services
- UI Window (`src/ui/window.py`) – Floating always-on-top window; lays out a fixed 2×3 grid of section drop zones, handles minimize-to-icon (later) and visual highlighting during drag-over (later).
- Section Component (`src/ui/section.py`) – Represents a single section (label, path/type, UI state), with edit/delete controls and validity indicators.
- Dialogs (`src/ui/dialogs.py`) – Overwrite/Cancel, Folder Move Confirmation, Invalid Folder prompts.
- Config Manager (`src/config/config_manager.py`) – Loads/saves JSON config at `%APPDATA%/DesktopSorter/config.json`; applies defaults from `src/config/defaults.py`; maintains a small schema version.
- File Operations (`src/file_handler/file_operations.py`) – Moves files/folders, detects conflicts, executes overwrite behavior, runs operations off the UI thread, and reports results.
- Undo Service (`src/services/undo.py`) – Session-only multi-level undo of the last move batches; stores action groups (move/overwrite/recycle) and attempts reverse operations; surfaces failures.
- Drag-and-Drop Bridge (`src/services/dragdrop.py`) – Wraps `tkinterdnd2` to receive Explorer drags; normalizes file paths (including multi-select) and emits drop events to the UI.
- Windows Integration (`src/services/win_integration.py`) – Manages window handle (HWND), always-on-top, and pass-through behavior by toggling `WS_EX_TRANSPARENT` via `pywin32` (`SetWindowLong`/`GetWindowLong`). Note: we avoid `WS_EX_LAYERED` unless paired with `SetLayeredWindowAttributes` due to Tk rendering issues; current design uses only `WS_EX_TRANSPARENT` for click-through.
- Recycle Bin Service (`src/services/recycle_bin.py`) – Sends files/folders to the Recycle Bin using `SHFileOperation`/`IFileOperation` with `FOF_ALLOWUNDO` (via `pywin32`).
- Error Handler (`src/file_handler/error_handler.py`) – Maps exceptions (permissions, missing paths, long-path issues) to user-facing dialogs and safe fallbacks.

### Supporting Services
- Logging – Standard Python logging; file handler writes to `%APPDATA%/DesktopSorter/logs/app.log` with rotation.
- No external DB, cache, or broker. Persistent state is the JSON config file.

### Process Architecture
```
[ Tk mainloop (UI process) ]
        |            \
        |             +-- [Worker thread pool: file moves]
        +-- DragDrop (tkinterdnd2)
        +-- Win Integration (pywin32)
        +-- Undo Service (in-memory)
```
Single process with Tk mainloop. Long-running file operations run on a small worker thread pool; results are marshaled back to the UI thread.

## Data Flow Examples

### Drag-and-Drop Move
```
Explorer → tkinterdnd2 (Drop) → DragDrop → UI highlights target section
      → FileOperations.move_many(request) [worker thread]
          → conflict? → Dialogs.overwrite_cancel (UI thread)
          → destination is Recycle Bin? → RecycleBin.send(paths)
          → else → move (cross-volume aware), report per-item success/failure
      → UI updates counts/errors; clear highlight
      ```

### Undo (Session-Only)
```
User clicks Undo → UndoService.pop_last_group()
    → for each item reverse (to → from / restore backup / recycle restore)
    → report failures (missing path, permission)
    → UI updates: enable/disable Undo button
```

### Startup and Config Load
```
main → ConfigManager.load(appdata_path) → apply defaults (Recycle Bin section)
     → Window builds sections grid → DragDrop registers drop targets
```

### Edit Section
```
User clicks Edit → Dialog (label + folder picker) → validate path
    → ConfigManager.update_and_save → Window refreshes section state
```

## Key Abstractions
- Section: `{ id, label, kind: [folder|recycle_bin], path?, valid }`.
- MoveRequest: `{ sources: [paths], target: Section, options: { overwrite: bool } }`.
- Config schema: `{ version: n, sections: [Section] }` with forward-compatible defaults.

## Configuration
- Central: `src/config/config_manager.py`; defaults in `src/config/defaults.py`.
- Paths: `%APPDATA%/DesktopSorter/config.json` and `%APPDATA%/DesktopSorter/logs/app.log`.
- Environment variables (optional): `LOG_LEVEL`, `DS_DND_DEBUG`.

## Integration Points
- Windows Shell APIs (pywin32):
  - Recycle Bin: `SHFileOperation`/`IFileOperation` with `FO_DELETE | FOF_ALLOWUNDO`.
  - Window styles: `GetWindowLong/SetWindowLong` to toggle `WS_EX_TRANSPARENT` for pass-through; keep always-on-top. Avoid `WS_EX_LAYERED` to prevent blank/transparent client area with Tk.
- TkinterDnD2: must bundle TkDND resources with PyInstaller; normalizes Explorer drops to file paths.
- Filesystem: Robust moves (cross-volume rename → copy+delete), long path prefixes (`\\?\\`) if needed, permission error handling.

## Runtime & Operations Notes
- Pass-through behavior: The window should allow clicks to pass through when not actively handling drag/drop. Implementation toggles `WS_EX_TRANSPARENT` when idle; disable transparency while dialogs are open or during drag/drop; re-enable afterward. We do not set `WS_EX_LAYERED` to avoid Tk paint issues. The grid is fixed at 2×3 to keep the layout predictable and minimal.
- Concurrency: Use worker threads for file operations; schedule UI updates via `Tk.after` to avoid cross-thread UI calls.
- Packaging: `pyinstaller.spec` must include `tkinterdnd2` resources and `resources/icon.png`. Verify DnD works in the bundled .exe.
- Observability: INFO logs include actions (drop target, counts), WARN/ERROR capture failures (path, errno). Avoid logging full sensitive paths in public builds if required.
- Accessibility/UX: Labels are readable by screen readers; highlight state visible in high contrast.

## Development Guidelines
- Keep OS-specific logic in `services/` or `file_handler/`, not in UI widgets.
- Guard UI responsiveness: no blocking I/O on main thread; use dialogs sparingly and contextually.
- Validate and normalize user-provided paths; prompt for reselect on missing paths.
- Add focused tests around config persistence and conflict resolution logic; manual checklist covers DnD and pass-through.

## Related Docs
- Scope: `scope.md`
- Structure: `structure.md`
- Task specs: `comms/tasks/YYYY-MM-DD-*.md`

---
This overview captures how components connect, where Windows integration occurs, and the expected data flows. Update it when adding new integration points or changing flows materially.
