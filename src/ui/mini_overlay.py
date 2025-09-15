"""
MiniOverlay - Small floating overlay shown when main window is minimized
Displays app logo/icon with drag-to-move and click-to-restore functionality
"""

import tkinter as tk
import logging
import os
from typing import Callable, Optional


class MiniOverlay:
    """Small floating always-on-top overlay for minimized app"""

    def __init__(self, parent_root: tk.Tk, on_restore: Callable[[], None], logger=None):
        """
        Initialize mini overlay

        Args:
            parent_root: Main application root window
            on_restore: Callback to restore main window
            logger: Optional logger instance
        """
        self.parent_root = parent_root
        self.on_restore = on_restore
        self.logger = logger or logging.getLogger(__name__)

        # State
        self.overlay = None
        self.last_position = None
        self.drag_data = {'x': 0, 'y': 0, 'dragging': False}

        # Try to load and scale icon
        self.icon_image = self._load_and_scale_icon()

        self.logger.debug("MiniOverlay initialized")

    def _load_and_scale_icon(self):
        """Load and scale app icon based on screen resolution"""
        try:
            # Calculate target size based on screen resolution
            screen_w = self.parent_root.winfo_screenwidth()
            screen_h = self.parent_root.winfo_screenheight()
            min_dimension = min(screen_w, screen_h)
            target_size = max(32, min(96, round(min_dimension * 0.04)))

            self.logger.debug(f"Screen: {screen_w}x{screen_h}, target icon size: {target_size}")

            # Look for icon file
            icon_path = None
            for possible_path in [
                "resources/icon.png",
                "folder_declutter.png",  # Found this in the root
                "icon.png"
            ]:
                if os.path.exists(possible_path):
                    icon_path = possible_path
                    break

            if not icon_path:
                self.logger.warning("No icon file found, using text fallback")
                return None

            self.logger.info(f"Loading icon from: {icon_path}")

            # Try to use Pillow for high-quality scaling if available
            try:
                from PIL import Image, ImageTk
                pil_image = Image.open(icon_path)
                pil_image = pil_image.resize((target_size, target_size), Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(pil_image)
            except ImportError:
                self.logger.debug("Pillow not available, using tkinter scaling")
            except Exception as e:
                self.logger.warning(f"Error with Pillow scaling: {e}")

            # Fallback to tkinter scaling
            try:
                original = tk.PhotoImage(file=icon_path)
                original_w = original.width()
                original_h = original.height()

                if original_w <= 0 or original_h <= 0:
                    raise ValueError("Invalid image dimensions")

                # Calculate scaling factors
                scale_x = target_size / original_w
                scale_y = target_size / original_h

                if scale_x > 1 or scale_y > 1:
                    # Zoom (integer factors only)
                    zoom_factor = int(min(scale_x, scale_y)) or 1
                    return original.zoom(zoom_factor, zoom_factor)
                else:
                    # Subsample
                    subsample_factor = int(max(1/scale_x, 1/scale_y)) or 1
                    return original.subsample(subsample_factor, subsample_factor)

            except Exception as e:
                self.logger.warning(f"Error loading/scaling icon: {e}")
                return None

        except Exception as e:
            self.logger.error(f"Error in icon loading: {e}")
            return None

    def _get_default_position(self):
        """Get default position (bottom-right with margin)"""
        try:
            screen_w = self.parent_root.winfo_screenwidth()
            screen_h = self.parent_root.winfo_screenheight()

            # Account for taskbar with margin
            margin = 16
            overlay_size = 96  # Maximum possible size

            x = screen_w - overlay_size - margin
            y = screen_h - overlay_size - margin - 40  # Extra margin for taskbar

            return x, y
        except Exception:
            return 300, 300  # Safe fallback

    def show(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """
        Show the overlay at specified position

        Args:
            x: X coordinate (uses last position or default if None)
            y: Y coordinate (uses last position or default if None)
        """
        if self.overlay:
            self.logger.debug("Overlay already shown")
            return

        try:
            # Create overlay window
            self.overlay = tk.Toplevel()
            self.overlay.overrideredirect(True)  # Remove window decorations
            self.overlay.attributes('-topmost', True)  # Always on top

            # Determine position
            if x is not None and y is not None:
                pos_x, pos_y = x, y
            elif self.last_position:
                pos_x, pos_y = self.last_position
            else:
                pos_x, pos_y = self._get_default_position()

            # Create content
            if self.icon_image:
                # Use scaled icon
                self.overlay_label = tk.Label(
                    self.overlay,
                    image=self.icon_image,
                    cursor="hand2"
                )
            else:
                # Text fallback
                self.overlay_label = tk.Label(
                    self.overlay,
                    text="DS",
                    font=('Arial', 24, 'bold'),
                    bg='lightblue',
                    fg='darkblue',
                    cursor="hand2",
                    relief=tk.RAISED,
                    borderwidth=2,
                    padx=10,
                    pady=10
                )

            self.overlay_label.pack()

            # Bind events
            self._bind_events()

            # Position and show
            self.overlay.geometry(f"+{pos_x}+{pos_y}")
            self.overlay.deiconify()

            self.logger.info(f"Mini overlay shown at ({pos_x}, {pos_y})")

        except Exception as e:
            self.logger.error(f"Error showing overlay: {e}")
            if self.overlay:
                try:
                    self.overlay.destroy()
                except Exception:
                    pass
                self.overlay = None

    def hide(self) -> None:
        """Hide/destroy the overlay"""
        if self.overlay:
            try:
                # Store current position for next time
                x = self.overlay.winfo_x()
                y = self.overlay.winfo_y()
                self.last_position = (x, y)
                self.logger.debug(f"Stored overlay position: ({x}, {y})")

                self.overlay.destroy()
                self.logger.info("Mini overlay hidden")
            except Exception as e:
                self.logger.error(f"Error hiding overlay: {e}")
            finally:
                self.overlay = None

    def set_last_position(self, x: int, y: int) -> None:
        """Set last known position for the overlay"""
        self.last_position = (x, y)
        self.logger.debug(f"Set last overlay position: ({x}, {y})")

    def _bind_events(self):
        """Bind mouse events for drag and click"""
        if not self.overlay_label:
            return

        # Bind to both overlay window and label for full coverage
        for widget in [self.overlay, self.overlay_label]:
            widget.bind('<Button-1>', self._on_click)
            widget.bind('<B1-Motion>', self._on_drag)
            widget.bind('<ButtonRelease-1>', self._on_release)

    def _on_click(self, event):
        """Handle mouse click - start potential drag or restore"""
        self.drag_data['x'] = event.x_root
        self.drag_data['y'] = event.y_root
        self.drag_data['dragging'] = False

    def _on_drag(self, event):
        """Handle mouse drag - move overlay"""
        if not self.overlay:
            return

        # Calculate movement
        dx = event.x_root - self.drag_data['x']
        dy = event.y_root - self.drag_data['y']

        # Use threshold to distinguish drag from click
        if not self.drag_data['dragging'] and (abs(dx) > 3 or abs(dy) > 3):
            self.drag_data['dragging'] = True

        if self.drag_data['dragging']:
            # Move overlay
            current_x = self.overlay.winfo_x()
            current_y = self.overlay.winfo_y()
            new_x = current_x + dx
            new_y = current_y + dy

            self.overlay.geometry(f"+{new_x}+{new_y}")

            # Update drag reference point
            self.drag_data['x'] = event.x_root
            self.drag_data['y'] = event.y_root

    def _on_release(self, event):
        """Handle mouse release - restore if not dragging"""
        try:
            if not self.drag_data['dragging']:
                # Click without drag - restore main window
                self.logger.info("Overlay clicked - restoring main window")
                self.on_restore()
            else:
                # Drag ended - log final position
                final_x = self.overlay.winfo_x()
                final_y = self.overlay.winfo_y()
                self.logger.info(f"Overlay dragged to: ({final_x}, {final_y})")
                self.last_position = (final_x, final_y)
        finally:
            self.drag_data['dragging'] = False