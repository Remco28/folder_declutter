# Project Phases — Desktop Sorter

This document outlines project phases at a slightly deeper level to guide future task specs in `comms/tasks/`.

## Phase 1 — Setup & Planning
- Outcomes: requirements.txt drafted; architecture finalized; phased plan written.
- Tasks: confirm dependencies (tkinterdnd2, pywin32, pyinstaller), finalize architecture, align UX scope.
- Acceptance: NEXT_STEPS updated; ARCHITECTURE.md present; dependencies agreed.

## Phase 2 — UI Scaffold
- Outcomes: Tk window with always-on-top; sections grid; minimize-to-floating icon prototype.
- Tasks: base layout; section widgets; simple highlight placeholder; load icon asset.
- Acceptance: window runs; grid shows; minimize/restore works.

## Phase 3 — Windows Pass-through
- Outcomes: click-through when idle; drops still accepted during drag-over.
- Tasks: obtain HWND; toggle WS_EX_TRANSPARENT; state transitions around drag enter/move/leave.
- Acceptance: underlying apps receive clicks when idle; drag-over disables pass-through; restored after drop/leave.

## Phase 4 — Config Persistence
- Outcomes: config in %APPDATA% with schema version and defaults (Recycle Bin section).
- Tasks: config_manager.load/save; defaults; bind UI to config; basic migration hook.
- Acceptance: restart restores sections; invalid path flagged.

## Phase 5 — Drag-and-Drop Integration
- Outcomes: receive multi-file drops from Explorer via tkinterdnd2.
- Tasks: normalize URIs/paths; register drop targets; section highlight; emit drop events.
- Acceptance: dropping multiple files triggers a callback with correct paths.

## Phase 6 — File Operations + Undo
- Outcomes: reliable moves with conflict handling and confirmations; session-only multi-level Undo for last move batches.
- Tasks: threaded move_many; cross-volume copy+delete; overwrite/cancel dialog; folder move confirm; implement Undo service (action groups for move/overwrite/recycle) and UI wiring (enable/disable, Ctrl+Z).
- Acceptance: large/mixed drops complete without freezing UI; conflicts prompt correctly; repeated Undo reverses successive batches; failures are reported when items can’t be restored.

## Phase 7 — Recycle Bin Support
- Outcomes: sending to Recycle Bin works using pywin32 shell APIs.
- Tasks: wrap SHFileOperation/IFileOperation with FOF_ALLOWUNDO; per-item results.
- Acceptance: dropping to Recycle Bin section sends items to bin; restore possible from Recycle Bin.

## Phase 8 — Invalid Path UX
- Outcomes: robust handling of missing/inaccessible section paths.
- Tasks: detect on startup and before moves; prompt reselect/delete; visible error state.
- Acceptance: user can resolve invalid sections without crashes; clear visual cues.

## Phase 9 — Packaging
- Outcomes: standalone .exe via PyInstaller.
- Tasks: spec file; include tkdnd resources and icons; verify DnD and pass-through in bundle.
- Acceptance: deliver DesktopSorter.exe; manual smoke tests pass.

## Phase 10 — Accessibility & Polish
- Outcomes: readable labels, basic keyboard focus, high-contrast friendliness.
- Tasks: focus rings; accessible labels; color choices; small UI refinements.
- Acceptance: visual feedback clear in Windows high contrast; basic screen reader reads labels.

## Phase 11 — Logging & Diagnostics
- Outcomes: actionable logs under %APPDATA%/DesktopSorter/logs.
- Tasks: rotating file handler; contextual IDs; optional DnD debug flag.
- Acceptance: errors and key actions recorded; logs help triage issues.

## Phase 12 — Beta QA & Hardening
- Outcomes: confidence on edge cases and performance.
- Tasks: test UNC paths, long paths (\\?\\ prefix), permissions, cross-volume; fix issues.
- Acceptance: checklist complete; no critical defects.

## Notes for Spec Authors
- Derive implementation tasks from these phases; keep each spec focused and testable.
- When adding components that change interactions (e.g., new services), update `docs/ARCHITECTURE.md`.
