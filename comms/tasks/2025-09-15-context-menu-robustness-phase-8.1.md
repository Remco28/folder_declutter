# Phase 8.1 Spec — Context Menu Robustness (Fix TclError: invalid command name)

Status: SPEC READY
Owner: Architect
Date: 2025-09-15

## Objective
Eliminate intermittent `_tkinter.TclError: invalid command name "...!menu"` when opening the section tile context menu on Windows/Tk (Python 3.13), by making context menu creation and usage resilient to widget lifecycle and ensuring a valid Tcl object at popup time.

## Problem (from user log)
```
_tkinter.TclError: invalid command name ".!mainwindow.!frame.!frame.!sectiontile2.!menu"
```
Occurs on right‑click (`_show_context_menu → tk_popup`). This indicates the underlying Tcl widget for the Menu has been destroyed or was never fully realized when `tk_popup` is invoked.

## Likely Root Cause
- The `Menu` is parented to a transient `SectionTile` frame and may be destroyed across state redraws (`_show_empty_state`/`_show_defined_state`) or due to focus/tooltips timing.
- A stale Python reference to a destroyed Tcl object triggers `invalid command name` when calling `tk_popup`.

## Changes Required

### Files To Modify
- `src/ui/section.py`

### Requirements
1) Lazy, toplevel‑parented menu
   - Create the context menu lazily at first use and parent it to the toplevel (`self.winfo_toplevel()`), not the tile frame.
   - Keep a strong reference on `self.context_menu`.

2) Existence check + recreate on demand
   - Before showing, verify the Tcl object still exists: `self.context_menu.winfo_exists()`.
   - If missing or not yet created, rebuild the menu (idempotent helper `_ensure_context_menu()`).

3) Safe popup wrapper
   - Wrap `tk_popup(x, y)` in try/except for `tk.TclError`; on failure, recreate menu once and retry; if it still fails, log and return.
   - Continue to call `grab_release()` in finally, as done today.

4) State redraw interaction
   - Ensure `_show_empty_state`/`_show_defined_state` do not destroy the context menu instance. They should only unbind/rebind events on `display_label`.

5) Optional: use `post/unpost`
   - If needed for stability, prefer `post(x, y)` and `unpost()` over `tk_popup` (leave `tk_popup` if testing shows it’s stable after (1)–(3)).

## Pseudocode
```python
def _ensure_context_menu(self):
    if getattr(self, 'context_menu', None) is None:
        self.context_menu = Menu(self.winfo_toplevel(), tearoff=0)
        self._populate_context_menu(self.context_menu)
    elif not self.context_menu.winfo_exists():
        self.context_menu = Menu(self.winfo_toplevel(), tearoff=0)
        self._populate_context_menu(self.context_menu)
    return self.context_menu

def _populate_context_menu(self, menu):
    menu.delete(0, 'end')
    menu.add_command(label='Change Location...', command=self._change_location)
    menu.add_command(label='Rename Label...', command=self._rename_label)
    menu.add_separator()
    menu.add_command(label='Remove Location', command=self._remove_location)
    # Optionally: add 'Reset Section…' later (Phase 8.2)

def _show_context_menu(self, event):
    if not self._path: return
    menu = self._ensure_context_menu()
    try:
        menu.tk_popup(event.x_root, event.y_root)
    except tk.TclError:
        menu = self._ensure_context_menu()  # recreate once
        try:
            menu.tk_popup(event.x_root, event.y_root)
        except tk.TclError as e:
            self.logger.error(f"Context menu popup failed: {e}")
    finally:
        try:
            menu.grab_release()
        except Exception:
            pass
```

## Acceptance Criteria
1) Right‑clicking a defined tile reliably opens the context menu with no exceptions across repeated opens and state changes.
2) No `_tkinter.TclError: invalid command name ...!menu` in logs during popup.
3) Existing actions (Change Location…, Rename Label…, Remove Location) still work and persist.

## Manual Test Checklist
- Open context menu repeatedly on multiple tiles; switch tiles between empty/defined; no errors.
- Change path/label and reopen menu; still works.
- With tooltips on/off and quick right‑click sequences, no exceptions.

