# Next Steps for Desktop Sorter

## Immediate Tasks
- [x] Create .gitignore
- [x] Create requirements.txt (tkinterdnd2, pywin32, pyinstaller)
- [x] Break project into phases (see `comms/phases.md`)
- [x] Create ARCHITECTURE.md from the template
- [x] Ask Architect to update NEXT_STEPS.md
- [ ] Create interface mockup (sections grid + minimize icon)

## Phase Implementation
- [ ] Phase 1: Repo setup and planning — repo hygiene, requirements, architecture, phased plan.
- [ ] Phase 2: UI scaffold — Tk window, always-on-top, sections grid, minimize-to-icon prototype.
- [ ] Phase 3: Windows pass-through — implement WS_EX_TRANSPARENT toggle; verify clicks pass through when idle.
- [ ] Phase 4: Config persistence — config manager, defaults (Recycle Bin), load/save wiring.
- [ ] Phase 5: Drag-and-drop — integrate tkinterdnd2, multi-file drops, highlight states.
- [ ] Phase 6: File operations — threaded moves, conflict detection, overwrite/cancel dialog, folder move confirm.
- [ ] Phase 7: Recycle Bin — send-to-bin via SHFileOperation/IFileOperation with FOF_ALLOWUNDO.
- [ ] Phase 8: Invalid paths UX — detect missing/inaccessible folders; reselect/delete flow; visual indicators.
- [ ] Phase 9: Packaging — PyInstaller spec, include tkdnd resources and icon; produce .exe; smoke test.
- [ ] Phase 10: Accessibility & polish — labels readable, high-contrast, keyboard nav basics; visual refinements.
- [ ] Phase 11: Logging & diagnostics — rotating file logs in %APPDATA%; optional DnD debug flag.
- [ ] Phase 12: Beta QA — edge cases (UNC, long paths, permissions, cross-volume), performance, fixes.

## Documentation
- [ ] Create README.md (usage, build, troubleshooting)
- [ ] Write developer notes for packaging and tkdnd bundling

---

Notes:
- Keep the file in the repository root so the app can fetch it via the GitHub Contents API.
- Use `- [ ]` and `- [x]` checkboxes under headings; the parser recognizes H1–H3 section headers.
