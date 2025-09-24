# Task: Phase 9 — Windows Packaging with PyInstaller

## Specification
- **Author:** Architect
- **Status:** SPEC READY

### 1. Objective
Produce a repeatable Windows build that bundles the Desktop Sorter app into a standalone executable using PyInstaller, including drag-and-drop resources, overlay assets, and a usable desktop shortcut icon.

### 2. Scope & Constraints
- Target platform: Windows 10+ (x64). Building on other platforms is out of scope for this phase.
- Use PyInstaller; do not introduce alternative build systems.
- Bundle the existing `resources/` assets without renaming or flattening directories.
- Include tkinterdnd2’s native `tkdnd` library so drag-and-drop keeps working in the packaged app.
- Automate the build via a script so other phases can trigger packaging without memorizing the PyInstaller command.
- Generated artifacts should live under `dist/` and `build/`, following PyInstaller defaults.
- Keep the repo clean: no large binaries checked in; ensure the script supports cleaning old builds.

### 3. Required Changes
1. **Add build tooling**
   - Create `build/package.py` (or similar) that:
     - Resolves project root and entry module (`src/main.py`).
     - Locates the tkinterdnd2 data directory (`tkinterdnd2` installs `tkdnd2.9` under its package).
     - Invokes PyInstaller with a generated spec file (see next bullet) or directly using `PyInstaller.__main__`.
     - Supports two CLI commands: `build` (default) and `clean` (delete `build/`, `dist/`, and previous spec-generated `DesktopSorter.spec`/`DesktopSorter.exe` if present).
     - Surfaces errors clearly and exits non-zero on failure.

2. **PyInstaller spec**
   - Add `build/DesktopSorter.spec` checked into the repo with:
     - `Analysis` over `src/main.py` with hidden-imports for modules loaded dynamically (e.g., `win32timezone`, `PIL._tkinter_finder` if needed) discovered during testing.
     - `datas` entries to bundle:
       - Entire `resources/` directory to `resources/` within the bundle.
       - The tkinterdnd2 native library directory (`tkdnd2.9` and related `.dll`/`.tcl` files) into a `tkdnd2.9/` folder alongside the executable so `TkinterDnD.Tk()` can load it.
     - `binaries` entries if pywin32 DLLs do not auto-detect (ensure `pythoncom3*.dll` and `pywintypes3*.dll` follow PyInstaller defaults; add explicit entries only if analysis reports missing imports).
     - `EXE` configured with:
       - Windowed mode (`console=False`).
       - Icon file pointing to a Windows `.ico` asset (convert `resources/icon.png` to `resources/icon.ico` inside the repo if not already present; production build must use `.ico`).
       - Name `DesktopSorter.exe`.
     - `COLLECT` stage producing the final dist folder under `dist/DesktopSorter/`.

3. **Resource prep**
   - If an `.ico` variant of the app icon is missing, create `resources/icon.ico` (lossless conversion from `icon.png`, 256×256 max) and update relevant docs/comments noting both assets.
   - Ensure `src/ui/mini_overlay.py` continues to load icons from `resources/icon.png`; do not change runtime paths.

4. **Documentation updates**
   - Extend `docs/ARCHITECTURE.md` (Packaging section) with a short note on the PyInstaller build process and where assets are staged.
   - Update `NEXT_STEPS.md` to mark Phase 9 complete once the build works.
   - Add a section to `resources/README.md` describing the new `.ico` asset and its use in packaging.

5. **Verification & smoke tests**
   - Run the packaging script on Windows to produce `dist/DesktopSorter/DesktopSorter.exe`.
   - Document a short manual test checklist in the spec’s implementation PR/commit message (not in repo) covering: launch, drag-and-drop, pass-through toggle, overlay minimize/restore.
   - Confirm that a clean virtualenv without tkinterdnd2 installed can run the packaged EXE (ensures resources were bundled).

### 4. Pseudocode
```python
# build/package.py
import argparse, pathlib, shutil
from PyInstaller.__main__ import run as pyinstaller_run

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = ROOT / "build" / "DesktopSorter.spec"
DIST = ROOT / "dist"
BUILD = ROOT / "build" / "pyinstaller"

if args.command == "clean":
    shutil.rmtree(DIST, ignore_errors=True)
    shutil.rmtree(BUILD, ignore_errors=True)
else:
    extras = ["--clean", str(SPEC)]
    pyinstaller_run(extras)
```

```python
# build/DesktopSorter.spec (excerpt)
tkdnd_path = get_tkdnd_resource_path()
datas = [
    (str(ROOT / 'resources'), 'resources'),
    (tkdnd_path, 'tkdnd2.9'),
]
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DesktopSorter',
    icon=str(ROOT / 'resources' / 'icon.ico'),
    console=False,
)
```

### 5. Acceptance Criteria
- Running `python build/package.py` on Windows generates `dist/DesktopSorter/DesktopSorter.exe` without errors.
- The resulting EXE launches correctly on a machine without a Python environment, including working drag-and-drop, pass-through, overlay minimise flow, and logging.
- `tkdnd2.9` resources are present beside the executable in `dist/DesktopSorter/`, and the app reports drag-and-drop as available.
- New `.ico` asset (if added) exists only in `resources/` and is referenced by the spec; no duplicate icons elsewhere.
- Documentation (`docs/ARCHITECTURE.md`, `resources/README.md`, `NEXT_STEPS.md`) reflects the completed packaging phase.
- `comms/log.md` contains `SPEC READY`, `IMPL IN_PROGRESS`, and `IMPL DONE` entries for this phase when executed.

### 6. Test Guidance
- Manual smoke test on Windows using the packaged EXE:
  1. Launch DesktopSorter.exe from `dist/DesktopSorter/`.
  2. Verify drag-and-drop accepts multiple files.
  3. Toggle pass-through via the debug shortcut (`Ctrl+Alt+P`) if available.
  4. Minimize to overlay, drag overlay, and restore.
  5. Confirm log files appear under `%APPDATA%/DesktopSorter/logs` for the packaged build.
- Optional: run build in a GitHub Actions Windows runner (future automation) using the packaging script; not required this phase but keep script CI-friendly.
