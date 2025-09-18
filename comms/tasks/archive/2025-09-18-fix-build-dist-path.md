# Task: Fix build/package.py dist path expectations

## Objective
Ensure the PyInstaller packaging script reports success only when the generated executable actually exists, and align the script's clean/build logic with PyInstaller's default output directory when running from `build/DesktopSorter.spec`.

## Background
Running `python build/package.py build` currently prints:
```
61202 INFO: Build complete! The results are available in: .../build/dist/DesktopSorter
ERROR: Build completed but executable not found
```
PyInstaller succeeds and drops `DesktopSorter.exe` in `build/dist/DesktopSorter/`, but our wrapper checks `dist/DesktopSorter/DesktopSorter.exe` at the project root. Because `DesktopSorter.spec` lives under `build/`, PyInstaller's default `distpath` is `build/dist`, so the script's `DIST = ROOT / "dist"` constant is incorrect. The clean step also skips `build/dist`, leaving stale outputs behind.

## Scope & Constraints
- Touch only the packaging script; do not relocate the spec or rewrite the build tooling.
- Preserve existing logging tone/structure where practical.
- Windows-focused packaging remains the only target.

## Requirements
1. **Path alignment**
   - Update `build/package.py` so all references to the distribution directory (`DIST`, success messages, and `exe_path`) point to `build/dist` (i.e., `BUILD_ROOT / "dist"`).
   - Optionally guard against future relocations by tolerating both locations, but the primary path must be the in-tree default (`build/dist`).
2. **Clean step correctness**
   - Ensure `clean_build()` deletes the actual PyInstaller `dist` output directory (`build/dist`) and the workpath. If you add fallback removal for an old top-level `dist`, log it clearly as a legacy cleanup.
3. **Success criteria**
   - After running PyInstaller, the script should detect `DesktopSorter.exe` in the corrected location, print the success message with the accurate path, and exit with status 0 when the executable exists.

## Acceptance Checklist
- `python build/package.py clean` removes `build/dist` (and any legacy top-level `dist`, if present) without raising errors.
- `python build/package.py build` completes without errors and prints `SUCCESS: Package built at .../build/dist/DesktopSorter/DesktopSorter.exe` (path matches the on-disk executable).
- The final return code is 0 when the executable is present; failures are reported otherwise.
- No other files or directories are modified.
