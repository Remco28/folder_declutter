# Phase 2 Spec — UI Scaffold (Desktop Sorter)

Status: SPEC READY
Owner: Architect
Date: 2025-09-12

## Objective
Deliver a minimal, responsive Tkinter UI that matches the provided mock: a fixed 2×3 grid of section tiles, a persistent Recycle Bin drop target at the bottom, and a visible Undo button (disabled) near the Recycle Bin. No drag-and-drop, pass-through, or real file operations in this phase.

## User Stories (v1)
- As a user, I see a compact window titled "Desktop Sorter" with six slots (2×3) for destinations, plus a Recycle Bin icon at the bottom and an Undo button next to it.
- As a user, I can define an empty slot by clicking its “+” tile, selecting a folder, and entering a label. The label is displayed on the tile.
- As a user, I can hover a defined tile to see the full folder path as a tooltip.
- As a user, I can right‑click a defined tile to Change Location, Rename Label, or Remove Location.
- As a user, I see the Undo button but it is disabled (no file operations yet). Pressing Ctrl+Z also maps to Undo (disabled if no actions).

## Scope
In scope
- Tkinter window with always-on-top.
- Fixed 2×3 grid of tiles: defined (label) vs empty (“+”).
- Recycle Bin icon anchored at bottom center.
- Undo button anchored near Recycle Bin, disabled.
- Tooltips showing full path on hover.
- Context menu on defined tiles: Change Location…, Rename Label…, Remove Location.
- In-memory state only; no persistence.

Out of scope (future phases)
- Drag-and-drop (tkinterdnd2).
- Pass-through click behavior (pywin32 window styles).
- File operations and confirmations.
- Recycle Bin behavior.
- Config persistence to %APPDATA%.

## Acceptance Criteria
- Window title: "Desktop Sorter". Window is always-on-top.
- Layout: 2 columns × 3 rows of section tiles with consistent spacing; bottom area shows Recycle Bin icon centered, Undo button to its right.
- Empty tile shows a “+” icon or text; clicking opens folder picker then label prompt; new label appears on tile.
- Hover over a defined tile shows a tooltip with the full absolute path; tooltip disappears on mouse leave.
- Right-click on a defined tile shows a context menu with three items: Change Location…, Rename Label…, Remove Location. Items work and update the tile state in memory.
- Undo button present and disabled; Ctrl+Z bound to the same command.
- No runtime errors on Windows 10/11 with only Tkinter installed.

## Files and Modules
Create
- `src/main.py`
  - Initializes logging to console (basicConfig) and Tk root.
  - Sets title, always-on-top (`root.attributes('-topmost', True)`), fixed min size.
  - Creates and shows `MainWindow`.
- `src/ui/window.py`
  - Class `MainWindow(tk.Frame)`: grid container for six `SectionTile` instances; bottom bar with Recycle Bin icon and Undo button (disabled).
  - Handles tile creation and layout, window padding, and keyboard bindings (Ctrl+Z → undo callback).
- `src/ui/section.py`
  - Class `SectionTile(tk.Frame)` with two states:
    - Empty: plus glyph; on click → `on_add_section()` callback.
    - Defined: label text; tooltip on hover; right-click context menu with Change/Rename/Remove; invalid path shows a subtle red border.
  - Public methods: `set_section(label, path)`, `clear_section()`, `update_label(new_label)`, `update_path(new_path)`.
- `src/ui/dialogs.py` (stub)
  - Functions: `prompt_select_folder() -> str|None`, `prompt_text(title, initial="") -> str|None` for label input; simple wrappers around `filedialog` and `simpledialog`.
- `resources/icon.png`
  - Placeholder; not required to commit now. Code should gracefully handle missing icon.

Note: Do not implement `services/dragdrop.py` or `services/win_integration.py` yet. No persistence layer in this phase.

## Technical Notes & Constraints
- Layout
  - Use a single parent frame with uniform padding; tile size approx 140×80px (tweak as needed for clarity).
  - Recycle Bin area: a small image or text placeholder centered; Undo button (`state='disabled'`) to the right with tooltip "Undo last action".
- Tooltips
  - Implement a minimal tooltip helper inside `section.py` or a small internal class: create a small `Toplevel` with `overrideredirect(1)` on `<Enter>` and destroy on `<Leave>`.
- Context menu
  - Use `tk.Menu` on right-click (`<Button-3>`). Items:
    - Change Location… → folder picker; update path and tooltip.
    - Rename Label… → text prompt; update label.
    - Remove Location → clears tile to empty state.
- Keyboard
  - Bind `<Control-z>` on the root to call `on_undo()` in `MainWindow` (no-op; button disabled).
- Always on top
  - `root.attributes('-topmost', True)`; pass-through comes later.

## Interfaces (to be stable across phases)
- Section model (in-memory for now)
  - `{ id: int, label: str|None, path: str|None, kind: Literal['folder','recycle_bin'] }`
- `MainWindow` callbacks (placeholders for later wiring)
  - `on_undo()` – hook to Undo service (later phases).
  - `on_section_changed(section_id, new_state)` – UI → app state notification for future persistence.

## Pseudocode Sketches
- Adding a section
```
fn on_add_section(tile):
    path = prompt_select_folder()
    if not path: return
    default_label = basename(path)
    label = prompt_text("Label", default_label) or default_label
    tile.set_section(label, path)
    on_section_changed(tile.id, {label, path, kind: 'folder'})
```
- Tooltip
```
class Tooltip:
    on_enter(event): show Toplevel near cursor with path text
    on_leave(event): destroy if exists
```
- Context menu
```
menu = Menu(...)
menu.add_command("Change Location...", command=change_location)
menu.add_command("Rename Label...", command=rename)
menu.add_separator()
menu.add_command("Remove Location", command=clear)
```

## Test Checklist (manual)
- Launches with a 2×3 grid; no errors.
- Click empty tile → select folder → label prompt → label displayed.
- Hover defined tile → tooltip shows full path; leaves correctly.
- Right‑click defined tile → context menu works for Change/Rename/Remove.
- Undo button is visible and disabled; Ctrl+Z does nothing.
- Window stays on top of other windows.

## Notes for Implementer
- Keep UI code small and readable; no threading yet.
- Avoid hardcoding colors; use Tk defaults with minimal accents.
- Handle missing icon gracefully (show text "Recycle Bin" as fallback).

