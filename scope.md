# Desktop Sorter App Specification

## Overview
The Desktop Sorter is a lightweight, free, Windows-only application designed to help users declutter their desktops by dragging files and folders into a floating window with customizable sections. Each section represents a user-defined folder on their computer (e.g., Documents/Research, OneDrive/Backup). The app supports multi-select drag-and-drop, persists user configurations, handles file name conflicts, and provides visual feedback for a seamless experience.

## Functional Requirements
1. **Floating Window**:
   - A small, always-on-top window (resizable based on section count) that floats over other applications, such as Windows Explorer.
   - Supports up to 8 user-defined sections, each tied to a folder path (e.g., C:/Users/Documents/Research).
   - Window auto-resizes vertically or horizontally to accommodate the number of sections (e.g., 2x4 grid for 8 sections).
   - Can be minimized to a floating icon, draggable on the screen. Clicking the icon restores the window.
   - Window does not block clicks to underlying apps when not actively receiving drags.

2. **Section Management**:
   - Users can add sections (up to 8) via a button or right-click menu in the window.
   - Each section requires a user-defined label (e.g., "OneDrive Backup for Frank," "Old Work Stuff") and a folder path selected via a Windows file picker dialog.
   - Sections can be deleted with a single click (e.g., a small "X" button on the section).
   - If a section's folder path no longer exists, the app prompts the user to either reselect a valid folder or delete the section.
   - One default section is pre-configured for the Recycle Bin.

3. **Drag-and-Drop Functionality**:
   - Supports dragging files and folders from the Desktop or Windows Explorer into sections.
   - Multi-select drag-and-drop is supported (e.g., select multiple files and drag them to a section).
   - When a file/folder is dragged over a section, the section highlights (e.g., border glow or background color change) to indicate the drop target.
   - Dropped files/folders are moved (not copied) to the target folder.

4. **File Handling and Error Management**:
   - If a file/folder with the same name exists in the target folder, a confirmation dialog appears with options: Overwrite or Cancel.
   - If a folder move is initiated, a confirmation dialog confirms the move to avoid accidental data loss.
   - If a target folder is inaccessible (e.g., deleted or no permissions), a dialog prompts the user to reselect a folder or delete the section.
   - No restrictions on file types or folders; all valid Windows files/folders are supported.

5. **Persistence**:
   - Section configurations (labels and folder paths) are saved to a JSON file in the user's AppData folder (e.g., `C:/Users/<User>/AppData/Roaming/DesktopSorter/config.json`).
   - On app startup, the JSON file is loaded to restore sections and their settings.

6. **Portability**:
   - The app is a standalone executable (e.g., built with PyInstaller) requiring no installation.
   - The JSON config file is the only external file created, stored in AppData for portability.

## Non-Functional Requirements
- **Platform**: Windows only (Windows 10/11 compatible).
- **Tech Stack**: Python-based (e.g., Tkinter or PyQt/PySide for UI, built-in libraries for file operations and JSON).
- **Performance**: Lightweight, with minimal CPU/memory usage to avoid slowing down the system during normal operation.
- **UX**: Simple, intuitive interface with no onboarding required beyond drag-and-drop. Visual feedback (highlighting) ensures clarity during drags.
- **Accessibility**: Basic support for screen readers (e.g., section labels readable) and high-contrast mode compatibility.

## Wireframe Description
### Main Window
- **Layout**: A compact, rectangular window (default ~400x300px) with a grid of sections (e.g., 2x4 for 8 sections, auto-adjusting based on section count).
- **Components**:
  - **Header**: Contains a "Minimize" button (to collapse to icon) and an "Add Section" button (+ icon).
  - **Sections**: Rectangular drop zones (e.g., ~100x100px each), each displaying:
    - Custom label (e.g., "OneDrive Backup for Frank") in bold text.
    - Small "X" button in the top-right corner for quick deletion.
    - Small "Edit" button (e.g., pencil icon) to change label or folder path.
    - Highlight effect (e.g., blue border or light background) when a file is dragged over.
  - **Recycle Bin Section**: Always present, labeled "Recycle Bin," with a distinct trash icon or subtle background tint.
- **Behavior**:
  - Window is always-on-top but allows clicks to pass through to underlying apps when not active.
  - Dragging files/folders over a section highlights it; dropping moves the item to the linked folder.
  - Right-clicking a section opens a context menu: "Edit Label/Path," "Delete Section."
  - If a folder is invalid, the section shows a red border with a tooltip: "Folder not found—reselect or delete."

### Minimized State
- **Appearance**: A small (~32x32px), semi-transparent floating icon (e.g., a stylized folder or arrow).
- **Behavior**:
  - Draggable anywhere on the screen.
  - Single-click restores the full window.
  - No additional features (e.g., no right-click menu).

### Dialogs
- **Conflict Dialog**: Pops up when a file/folder name conflict occurs. Options: "Overwrite/Replace" (replaces existing file/folder), "Skip" (leave existing and keep source), or "Cancel" (abort remaining items in the batch).
- **Folder Move Confirmation**: Pops up when dragging a folder. Message: "Move folder '<name>' to '<section>'?" with "Confirm" or "Cancel" buttons.
- **Invalid Folder Dialog**: When a section's folder is inaccessible, shows: "Folder '<path>' not found. Reselect folder or delete section?" with buttons: "Reselect" (opens file picker), "Delete" (removes section).

## Future Considerations
- Potential for high-contrast themes or resizable section sizes if user feedback demands it.
- Optional tray icon for background running, though not a priority for the initial release.
