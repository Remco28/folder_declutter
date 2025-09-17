"""
Centralized tooltip helper for consistent tooltip behavior across the application.

Provides a reusable API to attach/detach tooltips to widgets with correct z-order.
Ensures tooltips appear above topmost windows and handle dynamic text updates.
"""

import tkinter as tk
import logging

logger = logging.getLogger(__name__)


def bind_tooltip(widget, text_provider, *, offset=(16, -20), wraplength=240, font=('Arial', 8), bg='white'):
    """
    Bind a tooltip to a widget with proper z-order handling.

    Args:
        widget: The widget to attach the tooltip to
        text_provider: Either a string or a zero-arg callable returning the tooltip text at hover time
        offset: Tuple of (x, y) offset from cursor position
        wraplength: Maximum text width before wrapping
        font: Font tuple for tooltip text
        bg: Background color for tooltip
    """
    root = widget.winfo_toplevel()

    def get_text():
        """Get the current tooltip text"""
        return text_provider() if callable(text_provider) else str(text_provider)

    def on_enter(event):
        """Handle mouse enter event"""
        # Prevent duplicate tooltips
        if getattr(widget, '_tooltip_win', None):
            return

        try:
            # Create tooltip window
            tip = tk.Toplevel(root)
            tip.wm_overrideredirect(True)

            # Set z-order to appear above topmost root
            try:
                tip.transient(root)
            except Exception:
                pass

            try:
                tip.attributes('-topmost', True)
            except Exception:
                pass

            try:
                tip.lift()
            except Exception:
                pass

            # Create tooltip label
            label = tk.Label(
                tip,
                text=get_text(),
                bg=bg,
                relief=tk.SOLID,
                borderwidth=1,
                font=font,
                wraplength=wraplength,
                justify='left'
            )
            label.pack()

            tip.update_idletasks()

            # Determine placement relative to cursor, keeping tooltip onscreen
            tip_width = tip.winfo_width()
            tip_height = tip.winfo_height()
            screen_width = tip.winfo_screenwidth()
            screen_height = tip.winfo_screenheight()
            cursor_x, cursor_y = event.x_root, event.y_root

            x = cursor_x + offset[0]
            y = cursor_y + offset[1]

            if x + tip_width > screen_width:
                x = max(0, cursor_x - tip_width - abs(offset[0]))

            if y < 0:
                y = cursor_y + abs(offset[1])
            elif y + tip_height > screen_height:
                y = max(0, cursor_y - tip_height - abs(offset[1]))

            tip.wm_geometry(f"+{x}+{y}")

            # Store tooltip window reference
            widget._tooltip_win = tip

            logger.debug(f"Tooltip shown for widget: {widget.__class__.__name__}")

        except Exception as e:
            logger.error(f"Failed to create tooltip: {e}")

    def on_leave(event):
        """Handle mouse leave event"""
        _destroy_tooltip(widget)

    def on_focus_out(event):
        """Handle focus out event from root window"""
        _destroy_tooltip(widget)

    # Bind events
    widget.bind('<Enter>', on_enter)
    widget.bind('<Leave>', on_leave)
    root.bind('<FocusOut>', on_focus_out)

    # Store bound handlers for potential cleanup
    if not hasattr(widget, '_tooltip_handlers'):
        widget._tooltip_handlers = []
    widget._tooltip_handlers.extend([
        ('<Enter>', on_enter),
        ('<Leave>', on_leave)
    ])


def unbind_tooltip(widget):
    """
    Remove tooltip bindings and destroy any active tooltip.

    Args:
        widget: The widget to remove tooltip from
    """
    # Destroy any active tooltip
    _destroy_tooltip(widget)

    # Remove event bindings if they exist
    if hasattr(widget, '_tooltip_handlers'):
        for event_type, handler in widget._tooltip_handlers:
            try:
                widget.unbind(event_type, handler)
            except Exception:
                pass
        delattr(widget, '_tooltip_handlers')

    logger.debug(f"Tooltip unbound from widget: {widget.__class__.__name__}")


def _destroy_tooltip(widget):
    """
    Destroy the tooltip window if it exists.

    Args:
        widget: The widget whose tooltip should be destroyed
    """
    tooltip_win = getattr(widget, '_tooltip_win', None)
    if tooltip_win:
        try:
            tooltip_win.destroy()
        except Exception:
            pass
        widget._tooltip_win = None
