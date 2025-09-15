# Phase 7.1 Spec — Recycle Bin Flags Compatibility + Robust Fallback

Status: SPEC READY
Owner: Architect
Date: 2025-09-15

## Objective
Fix Recycle Bin failures caused by unavailable shell flags on some pywin32/Windows versions by making IFileOperation flags resilient and ensuring a clean fallback to SHFileOperation when IFileOperation setup fails.

## Problem
User report/log:

```
ERROR - Failed to recycle C:/.../move me again.txt: Unexpected error: AttributeError: module 'win32com.shell.shellcon' has no attribute 'FOFX_NOCOPYSECURITYATTRIBS'
```

Impact: Recycle Bin operation aborts with 0 successes; fallback to SHFileOperation is not taken because the exception occurs while computing flags inside `_delete_with_ifileoperation`, which currently swallows setup errors.

## Root Cause
- Some environments (older pywin32 or platform SDKs) do not expose `shellcon.FOFX_NOCOPYSECURITYATTRIBS`.
- `_delete_with_ifileoperation` computes flags unguarded, triggering `AttributeError` during setup. The function catches broad exceptions and returns error results, preventing `delete_many` from attempting the SHFileOperation fallback.

## Changes Required

### Files To Modify
- `src/services/recycle_bin.py`

### Requirements
1) Flags compatibility (IFileOperation):
   - Build operation flags using feature detection: include `FOFX_NOCOPYSECURITYATTRIBS` only if present; otherwise omit it.
   - Base flags remain: `FOF_ALLOWUNDO | FOF_NOCONFIRMMKDIR | FOF_SILENT | FOF_NOCONFIRMATION`.

2) Robust fallback behavior:
   - Treat setup-time failures in `_delete_with_ifileoperation` (COM init, CoCreateInstance, SetOperationFlags, global flag assembly) as hard failures: re-raise to the caller so `delete_many` can fall back to `_delete_with_shfileoperation`.
   - Continue to handle per-item errors (e.g., SHCreateItemFromParsingName for a specific path) inside `_delete_with_ifileoperation` without aborting the batch.

3) Logging clarity:
   - When omitting an optional flag, log a DEBUG note once (e.g., "FOFX_NOCOPYSECURITYATTRIBS not available; continuing without it").
   - When falling back to SHFileOperation due to setup failure, log a WARN with the exception summary.

## Expected Behavior
- On environments lacking `FOFX_NOCOPYSECURITYATTRIBS`, IFileOperation proceeds without that flag and successfully recycles items.
- If IFileOperation cannot be set up at all, SHFileOperation is attempted automatically; successful deletes are reported as ok in results.
- Error reporting remains per item; summary logs reflect accurate ok/error counts.

## Implementation Notes
- Flag assembly example:
  ```python
  flags = (
      shellcon.FOF_ALLOWUNDO |
      shellcon.FOF_NOCONFIRMMKDIR |
      shellcon.FOF_SILENT |
      shellcon.FOF_NOCONFIRMATION
  )
  extra = getattr(shellcon, 'FOFX_NOCOPYSECURITYATTRIBS', 0)
  if extra:
      flags |= extra
  else:
      logger.debug('IFileOperation: FOFX_NOCOPYSECURITYATTRIBS not available; proceeding without it')
  file_op.SetOperationFlags(flags)
  ```

- Error propagation for fallback:
  - Wrap "setup" code in `_delete_with_ifileoperation` in a try/except that re-raises on failure (e.g., compute flags, COM create, SetOperationFlags). Per-item add errors continue to set `{status: 'error'}` without raising.

## Acceptance Criteria
1) On a system where `shellcon.FOFX_NOCOPYSECURITYATTRIBS` is missing, dropping files to Recycle Bin succeeds; logs show 1+ ok and 0 errors.
2) If IFileOperation setup fails for any reason, SHFileOperation fallback is used automatically; items are recycled if possible.
3) No regressions on systems where the flag exists.
4) Non-Windows still no-ops cleanly with a warning.

## Test Plan (Manual)
- Environment with missing FOFX flag:
  - Drop a single file → appears in Recycle Bin; INFO summary shows 1 ok.
  - Drop mixed files/folder → all appear; correct counts.
  - With `DS_CONFIRM_RECYCLE=1`, verify confirmation dialog and cancel path.
- Sanity on environment with the flag present: repeat above; behavior unchanged.
- Simulate forced IFileOperation setup failure (optional dev toggle) to verify SHFileOperation fallback path executes and succeeds.

