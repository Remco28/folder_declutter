# Desktop Sorter Architecture Overview

This document outlines the architecture of the Desktop Sorter application: a lightweight Windows-only utility built with Python (Tkinter + tkinterdnd2 + pywin32) and packaged with PyInstaller. The focus is on how components relate and where Windows integration occurs.

## System Components

### Core Services
- UI Window (`src/ui/window.py`) – Floating always-on-top window; lays out a fixed 2×3 grid of section drop zones, provides visual highlighting during drag-over, and will handle minimize-to-icon later.
- Section Component (`src/ui/section.py`) – Represents a single section (label, path/type, UI state), with edit/delete controls and validity indicators.
- Dialogs (`src/ui/dialogs.py`) – Overwrite/Cancel, Folder Move Confirmation, Invalid Folder prompts.
- Config Manager (`src/config/config_manager.py`) – Loads/saves JSON config at `%APPDATA%/DesktopSorter/config.json`; applies defaults from `src/config/defaults.py`; maintains a small schema version.
- File Operations (`src/file_handler/file_operations.py`) – Moves files/folders, detects conflicts, executes overwrite behavior, runs operations off the UI thread, and reports results. On Windows, uses Shell IFileOperation for moves (with shutil fallback) to ensure Explorer refreshes immediately.
- Undo Service (`src/services/undo.py`) – Session-only multi-level undo of the last move batches; stores action groups (move/overwrite/recycle) and attempts reverse operations; surfaces failures.
- Drag-and-Drop Bridge (`src/services/dragdrop.py`) – Wraps `tkinterdnd2` to receive Explorer drags; normalizes file paths (including multi-select) and emits drop events to the UI. The app creates a `TkinterDnD.Tk()` root when available; otherwise, drag-and-drop is disabled gracefully.
- Windows Integration (`src/services/win_integration.py`) – Manages window handle (HWND), always-on-top, and pass-through behavior by toggling `WS_EX_TRANSPARENT` via `pywin32` (`SetWindowLong`/`GetWindowLong`). Note: we avoid `WS_EX_LAYERED` unless paired with `SetLayeredWindowAttributes` due to Tk rendering issues; current design uses only `WS_EX_TRANSPARENT` for click-through.
- Recycle Bin Service (`src/services/recycle_bin.py`) – Sends files/folders to the Windows Recycle Bin using `IFileOperation` (preferred) or `SHFileOperation` (fallback) with `FOF_ALLOWUNDO` (via `pywin32`). Runs operations in background threads with per-item result reporting. Includes optional confirmation dialog for large batches.
- Error Handler (`src/file_handler/error_handler.py`) – Maps exceptions (permissions, missing paths, long-path issues) to user-facing dialogs and safe fallbacks.
 - Mini Overlay (`src/ui/mini_overlay.py`) – Small floating always-on-top overlay shown when the app is minimized; displays a resizable logo (scaled by screen resolution), supports drag-to-move and double-click-to-restore. On Windows, the preferred path uses a native layered window with per-pixel alpha for perfect transparency; the Tk chroma-key path (`wm_attributes('-transparentcolor')`) remains a fallback.

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
          → destination is Recycle Bin? → RecycleBinService.delete_many(paths, on_done)
          → else → move via IFileOperation on Windows (shutil fallback elsewhere) → Explorer refreshes immediately → report per-item success/failure
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
User can:
  - Change Location… → prompt_select_folder → update path
  - Rename Label… → prompt_text → update label
  - Reset Section… → prompt_select_folder → prompt_text → update path+label in one flow
Validation: ConfigManager.update_and_save → Window refreshes section state
```

### Invalid Paths UX (Phase 8)
```
Startup: tiles with missing/not-writable paths render invalid (red border + subtitle)
Drop to invalid: block move → prompt_invalid_target (Reselect/Remove/Cancel)
  → Reselect: user picks folder → section updates → proceed with pending move
  → Remove/Cancel: no action taken
```

### Minimize to Overlay (Phase 10A/10B)
```
Minimize main window → compute window rect → show MiniOverlay (borderless, topmost) centered over that rect
On Windows, overlay uses chroma-key transparency to render only the logo
Drag overlay to reposition (overlay only); minimize again → overlay re-centers
Click overlay → hide overlay → deiconify + raise + focus main window
```

## Key Abstractions
- Section: `{ id, label, kind: [folder|recycle_bin], path?, valid }`.
- MoveRequest: `{ sources: [paths], target: Section, options: { overwrite: bool } }`.
- Config schema: `{ version: n, sections: [Section] }` with forward-compatible defaults.

## Configuration
- Central: `src/config/config_manager.py`; defaults in `src/config/defaults.py`.
- Paths: `%APPDATA%/DesktopSorter/config.json` and `%APPDATA%/DesktopSorter/logs/app.log`.
- Environment variables (optional): `LOG_LEVEL`, `DS_DND_DEBUG`, `DS_OVERLAY_MODE`, `DS_OVERLAY_DEBUG`.

## Integration Points
- Windows Shell APIs (pywin32):
  - Recycle Bin: Prefers `IFileOperation` with `FOF_ALLOWUNDO | FOF_NOCONFIRMMKDIR | FOF_SILENT | FOF_NOCONFIRMATION` for Vista+; falls back to `SHFileOperation` with `FO_DELETE | FOF_ALLOWUNDO | FOF_SILENT | FOF_NOCONFIRMATION` for older systems.
    - Flags compatibility (Phase 7.1): include `FOFX_NOCOPYSECURITYATTRIBS` only if available; otherwise omit and continue, falling back to `SHFileOperation` if IFileOperation setup fails.
  - File moves: Uses `IFileOperation.MoveItem` per item (Windows) with flags `FOF_SILENT | FOF_NOCONFIRMATION | FOF_NOCONFIRMMKDIR` (+ `FOFX_NOCOPYSECURITYATTRIBS` when available) to trigger native shell notifications so Desktop/Explorer views update instantly. Falls back to `shutil.move` if unavailable or on failure.
- Window styles: `GetWindowLong/SetWindowLong` to toggle `WS_EX_TRANSPARENT` for pass-through; keep always-on-top. Avoid `WS_EX_LAYERED` to prevent blank/transparent client area with Tk.
 - Tk overlay transparency (Windows fallback): `Toplevel(overrideredirect=True, -topmost)` with `wm_attributes('-transparentcolor', '#FF00FF')`; overlay and content widgets use the same background key color. PNG alpha is composited by Tk against this key color, which can create slight edge halos. Drag remains via Tk bindings; restoring the app requires a double-click.
 - Layered overlay (Windows preferred): Native `WS_EX_LAYERED` popup window with `UpdateLayeredWindow` using a premultiplied BGRA bitmap for perfect edges; input is delegated to Windows by returning `HTCAPTION` from `WM_NCHITTEST` for OS-managed dragging. The window class enables `CS_DBLCLKS`, and restoring the app is triggered by a double-click (`WM_(NC)LBUTTONDBLCLK`). The process is DPI-aware to prevent OS scaling blur.
- TkinterDnD2: must bundle TkDND resources with PyInstaller; normalizes Explorer drops to file paths.
- Filesystem: Robust moves (cross-volume rename → copy+delete), long path prefixes (`\\?\\`) if needed, permission error handling.

## Runtime & Operations Notes
- Pass-through behavior: The window should allow clicks to pass through when not actively handling drag/drop. Implementation toggles `WS_EX_TRANSPARENT` when idle; disable transparency while dialogs are open or during drag/drop; re-enable afterward. We do not set `WS_EX_LAYERED` to avoid Tk paint issues. The grid is fixed at 2×3 to keep the layout predictable and minimal.
 - Context menu robustness (Phase 8.1): Context menus are toplevel-parented, created lazily, checked for existence at popup, and retried safely to avoid Tcl command invalidation during widget redraws.
- Concurrency: Use worker threads for file operations; schedule UI updates via `Tk.after` to avoid cross-thread UI calls.
- Drag sessions: DragDropBridge tracks a drag sequence across tiles; pass-through is disabled on first enter and restored once the drag leaves the toplevel or on drop, preserving the prior pass-through state.
- Dialog z-order: Dialogs are parented to the main window; the app temporarily clears `-topmost` so system dialogs (folder picker, text input, overwrite) appear above, then restores it afterward.
- Overlay mode control: `DS_OVERLAY_MODE` env var controls overlay implementation ('auto', 'layered', 'tk'); `DS_OVERLAY_DEBUG` enables verbose overlay event logging for troubleshooting.
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

## Implementation Status
- Completed: Phase 2.1 (UI polish), Phase 3/3.1 (Windows pass-through + stabilization), Phase 4 (Config persistence), Phase 5 (Drag-and-drop), Phase 6 (File operations + Undo), Phase 7 (Recycle Bin support with Windows shell integration), Phase 7.1 (Recycle Bin flags compatibility + robust fallback), Phase 8 (Invalid paths UX), Phase 8.1 (Context menu robustness), Phase 8.2 (Section reset), Phase 8.3 (Overwrite dialog z-order and text rendering fix), Phase 10A (Minimize to overlay), Phase 10B (Overlay transparency, centering, dynamic sizing). Windows moves now use IFileOperation for shell-integrated refresh.

---
This overview captures how components connect, where Windows integration occurs, and the expected data flows. Update it when adding new integration points or changing flows materially.
