Title: Tooltips topmost + Recycle Bin refresh — centralized tooltip helper and robust Shell notifications (PIDL-based)

Objective
- Ensure all tooltips render above the always-on-top main window.
- Ensure Desktop/Explorer refreshes immediately after Recycle Bin delete operations using a robust IDLIST (PIDL) notification path, with a configurable fallback to PATHW.

Why
- Current tooltips (Section tiles, Undo button) are plain Toplevels without explicit topmost/transient; they can appear behind the root when the root is topmost.
- Recycle Bin deletes succeed but Explorer/desktop icons sometimes persist until manual refresh. A previous attempt to use PATHW-based `SHChangeNotify` after delete hit a Unicode conversion error in some environments. Using IDLIST (PIDL)-based notifications avoids Unicode coercion and is more reliable across pywin32 versions.

Scope
- Windows-focused behavior; tooltip improvements apply cross-platform with guards.
- Do not change existing file move notifications (those already fixed); add notifications specifically for Recycle Bin deletes.

Files
- src/ui/tooltip.py (NEW)
- src/ui/section.py
- src/ui/window.py
- src/services/recycle_bin.py
- src/services/shell_notify.py (NEW, shared utility for Shell notifications)
- docs/ARCHITECTURE.md (brief update for new utilities)

Deliverables
1) Centralized tooltip helper used by Section tiles and Undo button.
2) Post-delete shell notifications using PIDL/IDLIST for:
   - Each deleted item (SHCNE_DELETE)
   - Each parent directory touched (SHCNE_UPDATEDIR)
   - Desktop roots when applicable (SHCNE_UPDATEDIR)
   - All notifications dispatched on the Tk main thread. Provide a runtime fallback to PATHW-based notifications via env var.

Part A — Centralized Tooltip Helper

Add src/ui/tooltip.py
- Provide a minimal, reusable API to attach/detach tooltips to widgets with correct z-order.

API
- bind_tooltip(widget, text_provider, *, offset=(10, 10), wraplength=240, font=('Arial', 8), bg='lightyellow')
  - text_provider: either a string or a zero-arg callable returning the tooltip text at hover time (supports dynamic text like Undo count).
  - Behavior: on <Enter> create tooltip Toplevel; on <Leave>/<FocusOut> destroy it.
  - Z-order: ensure tooltip appears above a topmost root via: overrideredirect(True), transient(root), attributes('-topmost', True), lift(). Wrap platform-specific calls in try/except.
  - Store the created window on `widget._tooltip_win` to prevent duplicates.
- unbind_tooltip(widget)
  - Remove event bindings added by bind_tooltip and destroy any active tooltip.

Expected behavior
- Tooltip appears at screen coords (event.x_root + offset[0], event.y_root + offset[1]).
- No focus steal; tooltip does not interfere with keyboard focus.
- Multiple rapid enters/leaves do not leak windows; only one tooltip per widget.

Modify src/ui/section.py
- Replace current tooltip binding logic with the centralized helper.
  - In `_bind_tooltip`, call `tooltip.bind_tooltip(self.display_label, lambda: self._build_section_tooltip_text())`.
  - Implement `_build_section_tooltip_text()` to return the existing path line plus invalid reason when applicable (mirrors current logic in `_show_tooltip`).
  - In `_unbind_tooltip`, call `tooltip.unbind_tooltip(self.display_label)`.
- Remove or inline `_show_tooltip` / `_hide_tooltip` usage so they no longer create their own Toplevels. If kept for clarity, make them thin wrappers over the helper to avoid duplication.

Modify src/ui/window.py
- Replace `_add_tooltip` implementation to delegate to the helper:
  - Initialize `self.undo_button.tooltip_text = "Undo last action"` in `_create_bottom_controls`.
  - Call `tooltip.bind_tooltip(self.undo_button, lambda: getattr(self.undo_button, 'tooltip_text', 'Undo last action'))`.
- Keep `_update_undo_button` updating `self.undo_button.tooltip_text` (already present); ensure this property exists on init.

Pseudocode (tooltip helper)
```
def bind_tooltip(widget, text_provider, *, offset=(10,10), ...):
    root = widget.winfo_toplevel()
    def get_text():
        return text_provider() if callable(text_provider) else str(text_provider)
    def on_enter(event):
        if getattr(widget, '_tooltip_win', None):
            return
        tip = tk.Toplevel(root)
        tip.wm_overrideredirect(True)
        try: tip.transient(root)
        except: pass
        try: tip.attributes('-topmost', True)
        except: pass
        try: tip.lift()
        except: pass
        x, y = event.x_root + offset[0], event.y_root + offset[1]
        tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tip, text=get_text(), bg=bg, relief=tk.SOLID, borderwidth=1, font=font, wraplength=wraplength, justify='left')
        label.pack()
        widget._tooltip_win = tip
    def on_leave(event):
        win = getattr(widget, '_tooltip_win', None)
        if win:
            try: win.destroy()
            except: pass
            widget._tooltip_win = None
    # Bindings
    widget.bind('<Enter>', on_enter)
    widget.bind('<Leave>', on_leave)
    root.bind('<FocusOut>', lambda e: on_leave(e))
    # Store bound handlers if unbind_tooltip needs to detach them explicitly.
```

Constraints
- Keep UI style consistent (colors, fonts).
- Do not steal focus; do not change main window topmost behavior.
- Keep pass-through behavior intact (no changes to PassThroughController).

Acceptance (Tooltips)
- Hovering section tiles shows a tooltip above the main window, including invalid reason when applicable.
- Hovering the Undo button shows the latest text reflecting current undo stack depth.
- No tooltip remains after leaving the widget or switching focus.

Part B — Explorer Refresh After Recycle Bin Delete (PIDL-first)

Approach
- Use Shell IDLIST (PIDL)-based notifications as the default to avoid Unicode conversion issues:
  - For each deleted item: `SHChangeNotify(SHCNE_DELETE, SHCNF_IDLIST, pidl(item), None)`
  - For each parent directory: `SHChangeNotify(SHCNE_UPDATEDIR, SHCNF_IDLIST, pidl(dir), None)`
  - For Desktop roots (user/public) when any touched path is under them: same UPDATEDIR notification once each.
- Dispatch notifications from the Tk main thread using `root.after(0, ...)`.
- Provide an opt-in runtime fallback to PATHW for diagnostics or environments where PATHW is known-good: `DS_SHELL_NOTIFY_MODE=pathw`.

Modify src/services/recycle_bin.py
- After computing `results` in `delete_many` and before invoking `on_done`, schedule a main-thread function to:
  1) Extract `deleted_paths = [Path(r['path']).resolve() for r in results if r.get('status') == 'ok']`
  2) Call `shell_notify.notify_batch_delete_and_parents(deleted_paths)`
  3) Only after scheduling notifications, call `on_done(results)` (either immediately after scheduling or inside the scheduled function as the last step; pick one and document ordering).
- Guard all shell notify calls with Windows + pywin32 checks.

Add src/services/shell_notify.py (NEW)
- Expose a single entry point:
  - `notify_batch_delete_and_parents(paths: list[Path]) -> None`
    - Mode detection: `mode = os.getenv('DS_SHELL_NOTIFY_MODE', 'pidl').lower()`
    - For each `p in paths`: send delete event using PIDL (default) or PATHW fallback.
    - Compute `parents = {str(p.parent) for p in paths}` and send UPDATEDIR for each parent.
    - If any `p` under Desktop roots, also UPDATEDIR for those roots once.
- Helpers (guarded by Windows/pywin32 availability):
  - `_pidl_from_path(abs_path: str) -> pidl | None` using `shell.SHParseDisplayName`.
  - `_notify_delete_pidl(p: Path)` / `_notify_updatedir_pidl(p: Path)`
  - `_notify_delete_pathw(p: Path)` / `_notify_updatedir_pathw(p: Path)`
  - `get_desktop_folders() -> list[Path]` (mirrors FileOperations logic).
- Logging: INFO for high-level actions, DEBUG for per-path success; WARN on exceptions with clear context.

Optional refactor in src/file_handler/file_operations.py
- Replace internal `_shell_notify_updatedir` and `_shell_notify_many` with calls to `services.shell_notify` to keep one source of truth. Preserve existing behavior and performance.

Acceptance (Recycle Bin)
- Dropping files from Desktop onto the app’s Recycle Bin updates the Desktop immediately—icons disappear without manual refresh.
- Per-item delete notifications are issued along with parent/Desktop UPDATEDIR.
- Repeating the operation multiple times remains consistent; no Unicode errors are logged.
- No changes to move operations’ refresh behavior or performance.

Testing Notes
- Windows only for refresh verification. Use small test files on Desktop (including OneDrive Desktop) and in a normal folder.
- Verify tooltip layering by ensuring the tooltip is visible even when the main window is set as always-on-top.
- With default mode (PIDL): confirm no Unicode errors and immediate refresh.
- With `DS_SHELL_NOTIFY_MODE=pathw`: verify PATHW fallback works in this environment; ensure we pass `None` for dwItem2 and use absolute paths from `Path.resolve()`.

Non-Goals
- No changes to overlay windows, pass-through toggling, or drag/drop semantics.
- No new configuration surface.

Docs
- Add a short subsection in docs/ARCHITECTURE.md under “Supporting Services” for `ui.tooltip` (UI utility) and `services.shell_notify` (Windows shell notifications utility), noting:
  - PIDL-first strategy with PATHW fallback.
  - Main-thread dispatching from RecycleBinService and FileOperations.

Definition of Done
- Code implements the helper and replaces existing tooltip usages in SectionTile and MainWindow.
- RecycleBinService issues shell notifications post-delete; behavior verified manually on Windows Desktop.
- Minor doc update committed.

