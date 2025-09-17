Title: Trim empty session backup folders on shutdown

Intent:
- Avoid leaving hundreds of empty `%APPDATA%/DesktopSorter/backups/<session-id>` directories after normal use
- Keep genuine overwrite backups intact for diagnostics and undo
- Ensure cleanup happens without slowing shutdown noticeably

Target:
- Route(s): App startup/shutdown lifecycle
- Component(s): src/file_handler/file_operations.py, src/config/config_manager.py (helper), docs/ARCHITECTURE.md (if behaviour documented)

Run: AUTO

Scope: JS allowed

References:
- docs/ARCHITECTURE.md

Acceptance Criteria:
- On app shutdown (e.g., `FileOperations.shutdown()` or a new dedicated helper) the app removes any empty session directories under `%APPDATA%/DesktopSorter/backups/` while leaving non-empty ones untouched.
- Cleanup tolerates failure (permissions, races) by logging at DEBUG and continuing without crashing shutdown.
- When the app launches it may optionally perform the same empty-directory sweep so lingering past-session empties are removed; behaviour must be idempotent.
- Update architecture/docs or inline comments so future devs know backups are session-scoped and auto-pruned when empty.

Constraints:
- Use existing ConfigManager helpers for locating the app-data directory; keep logic within current modules (no new dependencies).

Notes:
- If multiple threads shut down, ensure cleanup only runs once (e.g., guard in FileOperations or top-level shutdown path).
