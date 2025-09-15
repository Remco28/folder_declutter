# Phase 8.3 Spec — Overwrite Dialog: Z‑Order and Text Rendering Fix

Status: SPEC READY
Owner: Architect
Date: 2025-09-15

## Objective
Ensure the overwrite conflict dialog appears above the main window and reliably shows button labels/text (no blank options). Maintain existing behavior: Replace, Skip, or Cancel.

## Problems Observed
- Dialog sometimes opens behind the always‑on‑top main window, making it seem unresponsive.
- The three action buttons render as blank lines on some setups (likely font/parenting focus/initialization order).

## Requirements (summary)
- Make dialog transient to parent, wait for visibility, lift/focus, and use modal grab after it is visible.
- Temporarily clear/restore parent `-topmost` around the dialog lifecycle.
- Use explicit text and a known font for buttons; update idle tasks before showing.
- Keep Enter/Escape shortcuts and centered geometry.

