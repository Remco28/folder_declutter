# Task: Fix main entry imports for PyInstaller runtime

## Objective
Ensure the packaged Windows executable can start without relative-import failures by making the main entry point resilient whether executed as a script (`python src/main.py`), a module (`python -m src.main`), or from the PyInstaller bootloader.

## Background
When running the PyInstaller-built `DesktopSorter.exe`, the app aborts with:
```
ImportError: attempted relative import with no known parent package
```
`src/main.py` currently imports project modules using relative syntax (`from .ui.window import ...`). That only works when `src` is imported as a package (e.g., `python -m src.main`). PyInstaller executes the entry script as a top-level module, so `__package__` is empty and the relative imports fail.

## Scope & Constraints
- Limit changes to `src/main.py` (and any necessary lint/tests). Do not refactor broader package structure.
- Maintain current logging, initialization order, and behavior.
- Preserve compatibility with both packaged and developer workflows on Windows and non-Windows.

## Requirements
1. **Absolute imports**
   - Replace the relative imports at the top of `src/main.py` with absolute package imports (e.g., `from src.ui.window import MainWindow`). Apply the same treatment to every `from .xyz` import in this file.
2. **Entry-point guard**
   - Keep the `if __name__ == "__main__": main()` guard intact so direct execution still works.
3. **Manual test guidance**
   - Update or add inline comments if helpful, but avoid verbose commentary. No additional documentation changes are required.

## Acceptance Checklist
- `python src/main.py` no longer raises the ImportError; the app boots (ignoring environment-related warnings such as logging permissions in sandboxed environments).
- `python -m src.main` continues to work.
- Running the PyInstaller build (`python build/package.py build`) and launching the resulting `DesktopSorter.exe` on Windows no longer triggers the relative import failure.
- No other files are modified.
