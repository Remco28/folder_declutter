# Phase 8.2 Spec — Section Reset (Re-pick Folder and Label)

Status: SPEC READY
Owner: Architect
Date: 2025-09-15

## Objective
Allow users to reset a defined section in a single flow: reselect a folder and update the label. This replaces the existing folder/label with the user’s new choices. Cancel leaves the section unchanged.

## Background
Users want a simple way to “set a new location” for an existing section without first removing it. Today, the context menu offers Change Location… and Rename Label… separately. This spec adds a one‑stop “Reset Section…” flow for convenience and parity with the mental model.

## Scope
- UI only; config plumbing already supports updates and persistence.
- Reuse existing dialogs: folder picker and text prompt.
- Integrate with Phase 8 invalid‑path behavior (revalidation happens after reset).

## Files To Modify
- `src/ui/section.py` — add context menu item: `Reset Section…` for defined tiles; implement combined re-prompt flow.
- `src/ui/window.py` — no changes expected; ensure `on_section_changed` continues to persist both label and path.
- `src/ui/dialogs.py` — no changes; reuse `prompt_select_folder` and `prompt_text`.
- `docs/ARCHITECTURE.md` — note the reset capability under “Edit Section”.

## Behavior & Requirements
1) Availability
   - `Reset Section…` appears only for defined tiles (i.e., tiles with a label/path).

2) Flow
   - When clicked, temporarily disable pass‑through and drop `-topmost` (existing pattern), then:
     1) Prompt folder selection (`prompt_select_folder(parent=…)`). If cancelled → abort; no change.
     2) Prompt label (`prompt_text("Enter Label", default=<basename(new folder)>)`). If cancelled → abort; no change. Empty label defaults to folder basename.
   - On success, call `set_section(new_label, new_path)` and propagate `on_section_changed` to persist config.

3) Visual/State
   - Tile updates immediately with new label and path; validity is recalculated based on existence/writability.

4) Logging
   - Log start and finish of reset with section id; log cancellations.

## Acceptance Criteria
1) Right‑clicking a defined tile shows `Reset Section…`.
2) Completing the flow updates both path and label, persists to config, and updates UI state.
3) Cancelling at either step leaves the section unchanged.
4) Works for tiles in invalid state as well (offers a direct reset path).

## Manual Test Checklist
- Reset a valid section → pick a new folder, change the label → tile updates and persists across restart.
- Cancel folder prompt → nothing changes.
- Cancel label prompt → nothing changes.
- On invalid tile (missing folder), `Reset Section…` still works and clears the invalid styling when a valid folder is selected.

