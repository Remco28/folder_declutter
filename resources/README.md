# Resources Directory

This directory contains application resources:

## Media Assets
- `icon.png` - Main application icon used in mini overlay and system integration
- `icon.ico` - Windows icon format for PyInstaller packaging and executable icon

## Usage Notes
- The application gracefully handles missing icon files by showing text fallbacks
- Icon scaling is handled automatically based on screen resolution (32-96px bounds)
- Supports both Pillow (high-quality) and tkinter (fallback) scaling methods

## Packaging Assets
- `icon.ico` contains multiple sizes (16x16, 32x32, 48x48, 256x256) optimized for Windows
- PyInstaller uses `icon.ico` for the executable icon in Windows builds
- Both PNG and ICO formats are maintained for cross-platform compatibility
- Runtime code resolves these assets via `src/services/resource_paths.py` so they load correctly from both source and bundled builds.
