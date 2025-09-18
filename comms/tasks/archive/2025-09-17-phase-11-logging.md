Title: Phase 11 — Logging & diagnostics foundation

Intent:
- Persist actionable logs to disk so support/debug doesn’t rely on console capture
- Keep console output readable while capturing richer context (session id, thread) in files
- Expose a simple way to elevate verbosity when diagnosing issues

Target:
- Route(s): Desktop app lifecycle (startup, background workers)
- Component(s): src/main.py, src/config/config_manager.py, src/services (new logging helper module if helpful), docs/ARCHITECTURE.md

Run: AUTO

Scope: JS allowed

References:
- docs/ARCHITECTURE.md

Acceptance Criteria:
- On startup the app ensures `%APPDATA%/DesktopSorter/logs/` (platform equivalent via ConfigManager) exists and attaches a `RotatingFileHandler` (`app.log`, ≥1 MB cap, ≥5 backups) that captures INFO+ messages from all modules without suppressing existing console output.
- File log format includes at minimum timestamp, level, logger name, thread name, and a generated session id (one per process run) so multi-session diagnostics stay readable; session id also appears in the startup banner.
- Respect an environment variable `DS_LOG_LEVEL` (case-insensitive) that overrides both console and file handler levels (default INFO); invalid values fall back gracefully and log a warning.
- Documented touchpoints log a succinct startup summary (version, config path, drag/drop availability) and significant operations (move batches, recycle, undo, pass-through toggles) continue flowing into the file log.
- Update `docs/ARCHITECTURE.md` Logging section to describe the new rotating file handler, log directory, and session id behaviour.

Constraints:
- Reuse stdlib logging + existing ConfigManager helpers; avoid new external dependencies.

Notes:
- Consider housing setup logic in a dedicated helper (e.g., `services/logging_utils.py`) to keep `main.py` readable; expose a `get_logs_dir()` helper if needed for future “open logs” UI.
