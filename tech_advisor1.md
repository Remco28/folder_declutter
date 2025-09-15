Hey team. Thanks for the detailed report—it's incredibly clear and lays out the problem perfectly. This is exactly the kind of situation where a fresh pair of eyes can help.

Here's my analysis and recommendation.

### Analysis

Your hypotheses are spot on. I strongly suspect **H1 (Message mismatch)** and **H3 (Hit-test/client handling conflict)** are the root cause.

When your `WM_NCHITTEST` returns `HTCAPTION`, you're telling Windows, "Hey, treat this spot like a title bar." Windows then takes over and sends *non-client* messages (like `WM_NCLBUTTONDOWN`) to `DefWindowProc` to manage the drag. Because your current logic is hooked into the *client* messages (`WM_LBUTTONDOWN`), it never sees the drag happen. The `WM_LBUTTONUP` that it *does* see looks like a simple click with no movement, so it incorrectly triggers the restore.

The core issue is the overloaded gesture: a single click is trying to mean both "start dragging" and "restore window." This ambiguity is notoriously difficult to get right.

### Recommendation

Let's eliminate the ambiguity. I recommend a variation of your proposed next steps **B** and **NS3**.

**Change the restore gesture to a double-click.** This is the most robust and user-friendly solution. It cleanly separates "drag" (single-click-and-hold) from "restore" (double-click).

Here is the concrete plan:

1.  **Modify `_window_proc` in `src/services/win_overlay.py`:**
    *   Keep returning `HTCAPTION` on `WM_NCHITTEST`. This is the right way to get native dragging.
    *   Add a handler for `WM_LBUTTONDBLCLK` (or `WM_NCLBUTTONDBLCLK` to be safe, though the former usually works). When you receive this message, trigger your `on_restore` callback.
    *   **Remove all logic** from your existing `WM_LBUTTONDOWN` and `WM_LBUTTONUP` handlers. Let the messages fall through to `DefWindowProc` so Windows can handle the drag without interference.

This approach is simple, reliable, and aligns with common UX patterns for overlay/tray icons.

### If That Doesn't Work

If for some reason the drag still fails, my next step would be **NS1 (Message-flow instrumentation)**. You can't fix what you can't see. Add simple `print()` statements for all `WM_NC*` and `WM_LBUTTON*` messages to get a definitive trace of what's happening.

Let me know how it goes. You're very close
