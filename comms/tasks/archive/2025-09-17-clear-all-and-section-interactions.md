# Task: Clear-All control and streamlined section interactions

## Context
Users want faster ways to reset their layout, quickly jump into section folders, and a simplified section context menu. We already have persistent section state in `MainWindow` + `SectionTile`, along with config persistence and pass-through handling helpers. We need to extend that UI while keeping the pass-through safe guards and platform quirks in mind.

## Goals
1. Add a dedicated control in the bottom bar that clears every configured section, with a simple confirmation prompt.
2. Enable double-click on a populated section tile to open its folder in the system file explorer, without interfering with existing drag/drop or add flows.
3. Replace the existing multi-option right-click menu with only two actions: rename the section label, or remove the location (reverting the tile to its default "+" state so paths/labels can be reconfigured).

## Requirements & Constraints

### Clear All Sections control
- Add a third button to the bottom controls row (next to Recycle Bin & Undo) labelled `Clear All`.
- Use the existing `_style_button` helper for consistent appearance, and default the button to a disabled state when there are no configured sections.
- On click, display a `messagebox.askyesno` confirmation with the copy `"Clear all folders?"`. If the user cancels, do nothing.
- When confirmed, iterate every populated tile:
  - Call the tile's `clear_section()` so UI state and `on_section_changed` notifications fire as they do today.
  - Ensure `MainWindow.sections` dictionary is cleared and config persistence runs (so the saved config ends up with all section entries cleared).
- After the reset, disable the `Clear All` button until a new section is configured again. The button should enable whenever at least one tile has an assigned path/label, and re-disable when none remain. Update logic should run on initialization, when sections load from config, and on every section change event.

### Double-click to open section folder
- Extend `SectionTile` so that while in a defined state it binds `<Double-Button-1>` on the displayed label (or container) to a new callback provided by `MainWindow`. Make sure the binding coexists with existing tooltip/context-menu behavior and does not import double-click handling on the empty tile state.
- In `MainWindow`, add a handler that receives the section id, revalidates the tile/path (reuse existing validation helpers), and if the path is missing/inaccessible surface the same recovery flow we use for drops (e.g., warn, prompt for reconfiguration rather than attempting to open a dead path).
- If the path is valid, temporarily disable pass-through/hide topmost as we already do for dialogs (when `pass_through_controller` is present) before launching the folder.
- Implement cross-platform folder opening logic:
  - Windows: `os.startfile(path)`.
  - macOS: `subprocess.Popen(["open", path])`.
  - Linux/Other: `subprocess.Popen(["xdg-open", path])` with graceful failure (log a warning if the command is missing/returns non-zero).
- Log the open attempt and any errors via the window logger. On failure, show a messagebox informing the user the folder could not be opened (include the exception string for context).

### Simplified section context menu
- Update `SectionTile._populate_context_menu` so the only menu items are:
  - `Rename Section...` (same behavior as current rename flow).
  - `Remove Location` (same behavior as existing remove option: confirmation prompt, then clears the tile).
- Remove the other menu entries (`Change Location`, `Reset Section`, etc.) and any separators that are no longer needed.
- Ensure removing the location routes through `clear_section` so the `Clear All` button state remains accurate.

### Shared considerations
- Update the undo button refresh helpers (if needed) so `Clear All` actions refresh the undo state after sections clear. If the clear triggers any undo stack updates, ensure the button label/state is accurate post-action.
- Keep styling consistent with the softened/minimal theme. Button spacing should mirror the existing controls spacing (e.g., 12px gap).
- Preserve existing drag-and-drop behavior; double-click bindings must not interfere with drag highlight or drop registration (no additional bindings on `<Button-1>`).

## Acceptance Criteria
- Launching the app with populated config shows the new `Clear All` button enabled. Clicking it prompts `"Clear all folders?"`; cancel does nothing; confirm clears all tiles back to `+`, disables `Clear All`, and persists the empty configuration.
- With at least one tile configured, double-click opens the folder in Explorer/Finder/xdg-open. Invalid paths prompt the same remediation flow as a drop onto an invalid section, rather than crashing or silently failing.
- Right-clicking a populated section shows only the two specified menu entries, and each performs as described.
- Manual regression passes: drag-and-drop moves still work, undo button state updates properly, and tooltips/context menus still appear as before.

## Implementation Notes
- Consider adding a helper on `MainWindow` such as `_update_clear_all_button_state()` and call it from `_load_sections_from_config`, `on_section_changed`, and after a successful clear-all action.
- If the open-folder logic grows, you may encapsulate it in a private `_open_path(path)` helper within `MainWindow`.
- Add or update doc strings/comments sparingly where behavior is non-obvious (e.g., around the new open logic or button state management).

## Documentation & Logging
- Append summary of this new UI behavior to any relevant user-facing docs (e.g., section in `docs/structure.md` describing controls) so users know about Clear All and double-click-to-open.
- Update `comms/log.md` once the spec is ready and again after implementation review as usual.

