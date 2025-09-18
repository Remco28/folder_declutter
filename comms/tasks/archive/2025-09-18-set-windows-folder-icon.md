# Task: Set Windows Folder Icon for Application Window

## Specification
- **Author:** Architect
- **Status:** SPEC READY

### 1. Objective
Replace the generic Tk icon that appears in the Windows taskbar with the standard yellow folder icon so the app looks native alongside File Explorer windows (see user screenshot).

### 2. Scope & Constraints
- Target platform: Windows only. Other platforms must keep their current behaviour.
- Do not add external image assets; use the icon that ships with Windows (e.g. via `shell32.dll`).
- Implementation must rely on `ctypes` so it works even when `pywin32` is missing.
- Any Windows handles obtained must be released properly to avoid USER32 handle leaks.

### 3. Required Changes
1. **`src/services/win_integration.py`**
   - Introduce a helper that loads the default folder icon (both large and small variants) using `ctypes.windll.shell32.SHGetFileInfoW` with `FILE_ATTRIBUTE_DIRECTORY` and the `SHGFI_USEFILEATTRIBUTES` flag.
   - Add a public function `set_window_icon_to_folder(hwnd: int, logger: Optional[Logger] = None)` that:
     - Validates `IS_WINDOWS` and `hwnd`.
     - Calls the helper to retrieve handles for `ICON_BIG` and `ICON_SMALL`.
     - Uses `user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)` and the small variant to apply the icons.
     - Destroys both the newly retrieved icons and any previous icons returned from `SendMessageW` via `user32.DestroyIcon`.
     - Emits debug/info logs on success and warnings when any Windows API call fails (include `ctypes.GetLastError()` where practical).
   - Update `get_hwnd` to fall back to `ctypes.windll.user32` calls when `pywin32` is unavailable so the icon can still be applied.

2. **`src/ui/window.py`**
   - During `MainWindow` initialisation (after the root window exists), invoke the new `set_window_icon_to_folder` helper using the root HWND from `win_integration.get_hwnd`.
   - Wrap the call in a Windows guard and ensure unexpected failures are logged.

### 4. Pseudocode
```python
from ctypes import windll, byref, wintypes

class _IconHandles(NamedTuple):
    large: wintypes.HICON
    small: wintypes.HICON

def _load_standard_folder_icons():
    shell32 = windll.shell32
    user32 = windll.user32
    flags = SHGFI_ICON | SHGFI_USEFILEATTRIBUTES

    info_large = SHFILEINFOW()
    shell32.SHGetFileInfoW("C:\\", FILE_ATTRIBUTE_DIRECTORY, byref(info_large), sizeof(info_large),
                           flags | SHGFI_LARGEICON)
    info_small = SHFILEINFOW()
    shell32.SHGetFileInfoW("C:\\", FILE_ATTRIBUTE_DIRECTORY, byref(info_small), sizeof(info_small),
                           flags | SHGFI_SMALLICON)
    return _IconHandles(info_large.hIcon, info_small.hIcon)

def set_window_icon_to_folder(hwnd):
    if not IS_WINDOWS or not hwnd:
        return
    icons = _load_standard_folder_icons()
    prev_big = user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, icons.large)
    prev_small = user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, icons.small)
    for handle in [icons.large, icons.small, prev_big, prev_small]:
        if handle:
            user32.DestroyIcon(handle)
```

### 5. Acceptance Criteria
- On Windows, the application displays the familiar yellow folder icon in the taskbar and Alt+Tab view.
- No new image assets are shipped with the project.
- Handle leaks are avoided (verified via code review: every icon handle obtained is released).
- Non-Windows builds remain unchanged and logging shows no new warnings outside Windows.

### 6. Test Guidance
- Manual: Launch the app on Windows; confirm the taskbar entry shows the folder icon and no warnings/errors are emitted.
- Optional: Add temporary debug logging of icon handles to confirm they are cleaned up; remove before commit.
