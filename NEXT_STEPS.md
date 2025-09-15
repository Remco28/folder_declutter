# Next Steps for Desktop Sorter

## Immediate Tasks
- [x] Create .gitignore
- [x] Create requirements.txt (tkinterdnd2, pywin32, pyinstaller)
- [x] Break project into phases (see `comms/phases.md`)
- [x] Create ARCHITECTURE.md from the template
- [x] Ask Architect to update NEXT_STEPS.md
- [x] Create interface mockup (sections grid + minimize icon)

## Phase Implementation
- [x] Phase 1: Repo setup and planning — repo hygiene, requirements, architecture, phased plan.
- [x] Phase 2: UI scaffold — Tk window, always-on-top, fixed 2×3 grid, basic tooltips and context menus. (Completed; spec archived.)
- [x] Phase 2.1: UI polish — package init files, tooltip guard, bind_all for Ctrl+Z, neutral tile styling, context menu binding only on defined tiles.
- [x] Phase 3: Windows pass-through — implement WS_EX_TRANSPARENT toggle via pywin32 with safe transitions; debug toggle in dev mode.
- [x] Phase 4: Config persistence — config manager, defaults (Recycle Bin), load/save wiring. (Completed; spec archived.)
- [x] Phase 5: Drag-and-drop — integrate tkinterdnd2, multi-file drops, highlight states. (Completed; spec archived.)
- [x] Phase 6: File operations + Undo — threaded moves, conflict detection, overwrite/cancel dialog, session multi-level undo. (Completed; spec archived.)
- [x] Phase 7: Recycle Bin — send-to-bin via IFileOperation with FOF_ALLOWUNDO (fallback SHFileOperation). (Completed; spec archived.)
- [x] Phase 7.1: Recycle Bin flags compatibility — guard missing `FOFX_NOCOPYSECURITYATTRIBS`; robust fallback to SHFileOperation. (Completed; spec archived.)
 - [ ] Phase 8: Invalid paths UX — detect missing/inaccessible folders; reselect/remove flow; visual indicators; block drops until resolved.
 - [ ] Phase 8.1: Context menu robustness — lazy toplevel-parented menu; existence checks; safe popup wrapper.
 - [ ] Phase 8.2: Section reset — one‑stop “Reset Section…” to re-pick folder and label.
- [ ] Phase 9: Packaging — PyInstaller spec, include tkdnd resources and icon; produce .exe; smoke test.
- [ ] Phase 10: Accessibility & polish — labels readable, high-contrast, keyboard nav basics; visual refinements.
- [ ] Phase 11: Logging & diagnostics — rotating file logs in %APPDATA%; optional DnD debug flag.
- [ ] Phase 12: Beta QA — edge cases (UNC, long paths, permissions, cross-volume), performance, fixes.

## Documentation
- [ ] Create README.md (usage, build, troubleshooting)
- [ ] Write developer notes for packaging and tkdnd bundling
- [x] Add Windows Recycle Bin service notes once implemented (Phase 7)
 - [ ] Document Invalid Paths UX (Phase 8), Context Menu Robustness (Phase 8.1), Section Reset (Phase 8.2), and Minimize-to-Overlay (Phase 10A)

---

Notes:
- Keep the file in the repository root so the app can fetch it via the GitHub Contents API.
- Use `- [ ]` and `- [x]` checkboxes under headings; the parser recognizes H1–H3 section headers.
