# Phase 4 Spec — Config Persistence

Status: SPEC READY
Owner: Architect
Date: 2025-09-13

## Objective
Persist the 2×3 grid section definitions to a JSON config under the user’s AppData directory so that sections restore on restart. Validate paths on load and visually flag invalid sections in the UI.

## Background
To date, sections exist only in memory. We need a small, forward‑compatible JSON config with a schema version and sane defaults. The Recycle Bin remains a dedicated control in the bottom bar and is not stored as a grid section in this phase.

## Scope
- Add a `config` package with a Config Manager and defaults.
- Load config at startup and populate the grid.
- Save updates when sections are added/renamed/path-changed/removed.
- Detect invalid paths at load and after updates; reflect in tile state.
- Provide a minimal migration hook for future schema bumps.

Out of scope: Undo persistence; drag-and-drop; moving files; Recycle Bin service; logging to a file (covered in Phase 11).

## Files To Add
- `src/config/__init__.py` (empty or module exports)
- `src/config/defaults.py`
- `src/config/config_manager.py`

## Files To Modify
- `src/main.py` — load config early; pass to `MainWindow`.
- `src/ui/window.py` — initialize tiles from config; write back on changes via Config Manager.
- `src/ui/section.py` — no functional changes required if validity border uses `os.path.exists` (it does). Keep as-is unless small hooks are helpful.

## Data Model
Config JSON at `%APPDATA%/DesktopSorter/config.json` (Windows). On non‑Windows (dev), use `~/.config/DesktopSorter/config.json`.

Schema (v1):
```
{
  "version": 1,
  "sections": [
    { "id": 0, "label": "Work",   "kind": "folder", "path": "C:\\Users\\me\\Desktop\\Work" },
    { "id": 1, "label": null,       "kind": "folder", "path": null },
    ... ids 0..5 ...
  ]
}
```
- Always exactly 6 entries (ids 0..5) matching the grid positions.
- `label` and `path` are null for empty tiles.
- Only `kind: "folder"` in this phase. Recycle Bin is not part of `sections`.

## Defaults
- `version = 1`
- `sections`: six entries (ids 0..5) with `label = null`, `path = null`, `kind = "folder"`.

## Behavior & Requirements
1) Configuration paths
   - Function `get_appdata_dir(app_name: str = "DesktopSorter") -> Path`:
     - Windows: `Path(os.environ["APPDATA"]) / app_name`
     - Else: `Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / app_name`
   - Ensure directory exists on first save.

2) Loading
   - `load() -> dict` reads JSON if present, else returns deep copy of defaults.
   - Validate structure:
     - If `version` missing/newer: treat as best‑effort; if newer, log a warning and still try to read known fields.
     - Ensure `sections` is length 6; fill/trim as needed using defaults (preserving known items by `id`).
   - For each section, compute `is_valid = bool(path) and os.path.exists(path)`; the UI will reflect validity by existing logic.

3) Saving
   - `save(config: dict) -> None` writes atomically:
     - Write to `config.json.tmp` then `replace()` to `config.json`.
   - Preserve `version` and full `sections` array (ids 0..5).

4) Update helpers
   - `update_section(config: dict, section_id: int, *, label: Optional[str], path: Optional[str]) -> dict` returns mutated config (copy or in‑place per implementation choice) with that section updated. `label`/`path` may be None (clears). Ensure index by `id`.
   - `clear_section(config: dict, section_id: int) -> dict` sets label/path to null.

5) UI integration
   - `src/main.py`:
     - Import Config Manager, call `cfg = ConfigManager.load()` before building UI.
     - Pass `cfg` and a Config Manager handle to `MainWindow`.
   - `src/ui/window.py`:
     - On init, iterate `cfg["sections"]` and for each non‑empty entry call `tile.set_section(label, path)` which already sets validity.
     - In `on_section_changed(section_id, section_data)`:
       - If `section_data is None`: `ConfigManager.clear_section(cfg, section_id)` then `ConfigManager.save(cfg)`.
       - Else: `ConfigManager.update_section(cfg, section_id, label=..., path=...)` then `ConfigManager.save(cfg)`.

6) Migration hook
   - Constant `CURRENT_VERSION = 1`.
   - `migrate(config: dict) -> dict`:
     - If `config.version < CURRENT_VERSION`: add any missing keys and set `version = CURRENT_VERSION`.
     - If `config.version > CURRENT_VERSION`: warn; proceed best‑effort.

7) Error handling
   - All file I/O wrapped in try/except with clear log messages; failure to load falls back to defaults in memory; failure to save surfaces a warning log but does not crash the UI.

## Function Signatures (Python)
- `class ConfigManager:`
  - `@staticmethod def get_appdata_dir(app_name: str = "DesktopSorter") -> Path`
  - `@staticmethod def get_config_path() -> Path`
  - `@staticmethod def load() -> dict`
  - `@staticmethod def save(config: dict) -> None`
  - `@staticmethod def update_section(config: dict, section_id: int, *, label: Optional[str], path: Optional[str]) -> dict`
  - `@staticmethod def clear_section(config: dict, section_id: int) -> dict`
  - `@staticmethod def migrate(config: dict) -> dict`

`defaults.py`
- `CURRENT_VERSION = 1`
- `def default_config() -> dict` returning a deep copy of the defaults.

## Pseudocode Highlights
Load:
```
def load():
  p = get_config_path()
  if not p.exists():
    return default_config()
  data = json.load(p.open())
  data = migrate(data)
  # normalize sections length to 6 by id
  normalized = default_config()
  for s in data.get("sections", []):
    i = int(s.get("id", -1))
    if 0 <= i < 6:
      normalized["sections"][i].update({
        "label": s.get("label"),
        "path": s.get("path"),
      })
  return normalized
```

Save (atomic):
```
def save(cfg):
  p = get_config_path()
  p.parent.mkdir(parents=True, exist_ok=True)
  tmp = p.with_suffix(p.suffix + ".tmp")
  json.dump(cfg, tmp.open("w", encoding="utf-8"))
  tmp.replace(p)
```

Window init:
```
cfg = ConfigManager.load()
for s in cfg["sections"]:
  if s["label"] and s["path"]:
    tiles[s["id"]].set_section(s["label"], s["path"])
```

On change:
```
if section_data is None:
  ConfigManager.clear_section(cfg, section_id)
else:
  ConfigManager.update_section(cfg, section_id, label=section_data["label"], path=section_data["path"])
ConfigManager.save(cfg)
```

## Acceptance Criteria
- Start app, add labels/paths to several tiles, close and relaunch: tiles restore exactly.
- Removing a location clears it from config and from UI after restart.
- Invalid paths on load render with the invalid state (visible border) and logs a warning per invalid section.
- Non‑Windows dev environments store config under `~/.config/DesktopSorter/config.json`.
- No crashes on missing or malformed config; app continues with defaults and logs a warning.

## Manual Test Checklist
1) Fresh start
   - Delete existing config if any; launch; all tiles empty; no errors.
2) Add and persist
   - Define tiles 0, 3 with valid folders; rename labels; restart; verify restoration.
3) Remove and persist
   - Remove tile 3; restart; tile 3 empty.
4) Invalid path
   - Manually edit config to a nonexistent path; restart; tile shows invalid border; logs warning.
5) Malformed config
   - Truncate config file; restart; app loads defaults and logs warning.

## Notes
- Do not block the UI thread with slow disk I/O; config files are tiny, so direct calls are acceptable, but keep code simple and safe.
- Recycle Bin remains a dedicated bottom control and is not part of the persisted sections in this phase.

