# Phase 5 Spec — Drag-and-Drop Integration (tkinterdnd2)

Status: SPEC READY
Owner: Architect
Date: 2025-09-13

## Objective
Receive multi-file/folder drops from Windows Explorer using `tkinterdnd2`, highlight the target tile during drag-over, and emit normalized file paths to the UI layer. Do not move files yet (that’s Phase 6).

## Background
We now persist 6 sections (Phase 4). The next step is wiring Explorer drag-and-drop so users can drop items onto a section tile. While dragging over the app, we must temporarily disable pass-through and provide clear visual feedback for the current target.

## Scope
- Integrate `tkinterdnd2` and register drop targets on each section tile and the Recycle Bin label.
- Normalize drop data to a list of absolute Windows paths (support multi-select).
- Provide enter/leave highlighting and drop handling callbacks to the UI.
- Temporarily disable Windows pass-through during drag, then restore after drop/leave.

Out of scope: Moving files, conflict dialogs, and Undo (Phase 6+). Packaging of TkDND resources (Phase 9).

## Files To Add
- `src/services/dragdrop.py`

## Files To Modify
- `src/main.py` — initialize DragDrop and pass into `MainWindow`.
- `src/ui/window.py` — hook tile widgets to DragDrop; implement on_enter/on_leave highlighting; route on_drop to a new handler that currently logs the drop.
- `src/ui/section.py` — add simple highlight state methods used during drag-over.
- `docs/ARCHITECTURE.md` — confirm integration details for Drag-and-Drop bridge.

## Behavior & Requirements
1) Initialization
   - A `DragDrop` (or `DragDropBridge`) service attaches to the Tk root using `TkinterDnD.Tk()` semantics via `tkinterdnd2`. Do not change existing `tk.Tk()` creation; instead, import and use `tkinterdnd2`’s `DND_FILES` and registration APIs against existing widgets.
   - If `tkinterdnd2` is unavailable, log a single warning and gracefully disable DnD.

2) Registration
   - Register each section tile’s top-level frame widget as a drop target for `DND_FILES`.
   - Also register the Recycle Bin label as a drop target.
   - Provide callbacks for `<<DropEnter>>`, `<<DropLeave>>`, and `<<Drop>>`.

3) Normalization
   - Accept raw `event.data` strings and normalize to `List[str]` absolute paths.
   - Handle Windows-style brace-wrapped paths with spaces (e.g., `{C:\\Path With Spaces}`), and multiple items separated by spaces.
   - Accept file and folder drops; no filtering or filesystem checks yet (Phase 6 will validate before moving).

4) Pass-through coordination
   - On any `DropEnter` over the app, call `PassThroughController.disable()`.
   - On `DropLeave` and after `Drop`, call `PassThroughController.enable()` if it was previously enabled.

5) UI feedback
   - SectionTile: add methods `set_drag_highlight(on: bool)` to toggle a visible highlight (e.g., change relief to `SOLID`, border/background color), reverting on leave.
   - Recycle Bin label: apply a simple visual change (e.g., relief raised/sunken) during drag-over.

6) Emitting drops
   - Add `MainWindow.on_drop(section_id: int | None, paths: list[str])` that logs the drop and stores a lightweight last-drop state for debugging. No file operations yet.

## Function Signatures (Python)
- `src/services/dragdrop.py`
  - `class DragDropBridge:`
    - `def __init__(self, root, pass_through_controller=None, logger=None)`
    - `def register_widget(self, widget, on_enter, on_leave, on_drop) -> None`
    - `@staticmethod def parse_drop_data(data: str) -> list[str]`
    - Internal: no-ops if `tkinterdnd2` not available.

## Pseudocode Highlights
DragDrop.parse_drop_data:
```
def parse_drop_data(data: str) -> list[str]:
  # Examples:
  # '{C:\\A File.txt} {C:\\Dir With Spaces} C:\\PlainPath'
  items = []
  buf = ''
  in_braces = False
  for ch in data:
    if ch == '{': in_braces = True; continue
    if ch == '}': in_braces = False; items.append(buf); buf=''; continue
    if ch == ' ' and not in_braces:
      if buf: items.append(buf); buf=''
    else:
      buf += ch
  if buf: items.append(buf)
  return [i.strip() for i in items if i.strip()]
```

Registering a tile:
```
bridge.register_widget(tile_widget,
  on_enter=lambda e: (tile.set_drag_highlight(True), pass_ctrl.disable()),
  on_leave=lambda e: (tile.set_drag_highlight(False), pass_ctrl.enable()),
  on_drop=lambda e: (tile.set_drag_highlight(False),
                     on_drop_tile(tile.section_id, DragDropBridge.parse_drop_data(e.data)),
                     pass_ctrl.enable()))
```

MainWindow.on_drop:
```
def on_drop(self, section_id, paths):
  self.logger.info(f"Drop to {section_id}: {len(paths)} items")
  self.last_drop = { 'section_id': section_id, 'paths': paths }
  # Phase 6 will call FileOperations.move_many(...)
```

## Acceptance Criteria
- Dropping one or more files/folders from Explorer onto any defined or empty tile triggers a log entry in the app with the correct count and normalized absolute paths.
- The hovered tile visibly highlights on drag enter and clears on leave/drop.
- Dropping onto the Recycle Bin label triggers a log entry with `section_id = None` (or a special code) and the correct normalized paths.
- While dragging over the app, clicks do not pass through (pass-through disabled). After drop or leaving the window, pass-through is re-enabled.
- If `tkinterdnd2` is not installed, the app still runs; DnD features are disabled with a warning.

## Manual Test Checklist
1) Single file
   - Drop `C:\\Temp\\file.txt` onto tile 0 → log shows that path and section 0.
2) Multiple items with spaces
   - Select two files and a folder with spaces in names; drop onto tile 3 → log shows all absolute paths.
3) Recycle Bin target
   - Drop items onto Recycle Bin label → log shows `section_id = None` and paths.
4) Pass-through behavior
   - With `DS_DND_DEBUG=1`, ensure `Ctrl+Alt+P` can toggle outside drag. Start a drag over the app → pass-through auto-disables; after leaving, it re-enables.
5) Missing tkinterdnd2
   - Uninstall/remove `tkinterdnd2` in a test venv → app runs with a warning; no crashes.

## Notes
- Keep DragDropBridge isolated in `services/`; do not entangle OS logic in UI files.
- Packaging of TkDND resources (Phase 9) will ensure DnD works in the bundled exe.

