# Task: Force PyInstaller output into build/dist

## Objective
Make sure the `build/package.py` wrapper explicitly directs PyInstaller to place artefacts in `build/dist`, so the executable exists where the script checks and Windows builds succeed without manual cleanup.

## Background
After the last update, `build/package.py` now looks for `DesktopSorter.exe` under `build/dist/DesktopSorter/`. However, PyInstaller still writes to the project-level `dist/` folder:
```
61202 INFO: Build complete! The results are available in: .../dist
ERROR: Build completed but executable not found
```
Because the wrapper doesn’t pass a `--distpath`, PyInstaller uses its default (`cwd/dist`). The executable ends up in the root-level directory, our success check fails, and running the bundle still imports relative modules from the wrong location.

## Scope & Constraints
- Keep all changes inside `build/package.py` and `build/DesktopSorter.spec` if needed.
- Preserve current logging style and clean/build flow.
- Continue cleaning legacy `dist/` directories so users aren’t left with stale folders.

## Requirements
1. **Dist path enforcement**
   - Pass PyInstaller an explicit dist path (`--distpath`) pointing at `build/dist` (the existing `DIST` constant).
   - If additional spec changes are necessary (e.g., `COLLECT(..., distpath=...)`), ensure they stay consistent with the CLI value.
2. **Success check alignment**
   - After the build, verify the executable in the enforced location (`build/dist/DesktopSorter/DesktopSorter.exe`). If it’s missing, emit an error that includes both the expected path and any unexpected directories that still contain a build artefact.
3. **Logging clarity**
   - Update the informational log that currently echoes PyInstaller’s message so it references the enforced path (or adds a warning if PyInstaller reported a different location).
4. **Backward cleanup**
   - Keep removing the top-level `dist/` during `clean_build()`. If a build ever produces files there, warn that it indicates a misconfiguration rather than silently deleting it.

## Acceptance Checklist
- Running `python build/package.py clean` deletes `build/dist/` and warns if a root-level `dist/` exists (and removes it).
- Running `python build/package.py build` prints a success message that names `build/dist/DesktopSorter/DesktopSorter.exe` and returns exit code 0 when the executable is present.
- The PyInstaller log no longer announces `.../dist` at the project root; our wrapper either suppresses or immediately clarifies the enforced path.
- Launching the rebuilt `DesktopSorter.exe` no longer fails due to missing imports (covered by the prior task).
- No other files are modified.
