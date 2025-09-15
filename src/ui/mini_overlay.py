"""
MiniOverlay - Small floating overlay shown when main window is minimized
Displays app logo/icon with drag-to-move and click-to-restore functionality
"""

import tkinter as tk
import logging
import os
import platform
from typing import Callable, Optional

# Transparency key for Windows chroma-key transparency
TRANSPARENT_KEY = '#FF00FF'

# Try to import LayeredOverlay for Windows per-pixel alpha
try:
    from ..services.win_overlay import LayeredOverlay
    LAYERED_OVERLAY_AVAILABLE = True
except ImportError:
    LAYERED_OVERLAY_AVAILABLE = False


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
        self.layered_overlay = None
        self.use_layered = False
        self.last_position = None
        self.drag_data = {'x': 0, 'y': 0, 'dragging': False}

        # Try to load and scale icon
        self.icon_image = self._load_and_scale_icon()
        self.icon_size = (0, 0)  # Will be set by _load_and_scale_icon

        # Try to initialize layered overlay for Windows
        if platform.system() == 'Windows' and LAYERED_OVERLAY_AVAILABLE:
            try:
                # Ensure Tk UI actions happen on the Tk thread via after()
                def _restore_cb():
                    try:
                        self.parent_root.after(0, self.on_restore)
                    except Exception as e:
                        self.logger.error(f"Error scheduling restore on Tk thread: {e}")

                self.layered_overlay = LayeredOverlay(_restore_cb, logger=self.logger)
                self.use_layered = True
                self.logger.info("LayeredOverlay initialized for Windows per-pixel alpha")
            except Exception as e:
                self.logger.warning(f"LayeredOverlay not available, using fallback: {e}")
                self.use_layered = False
        else:
            self.logger.debug("LayeredOverlay not available on this platform")

        self.logger.debug("MiniOverlay initialized")

    def _load_and_scale_icon(self):
        """Load and scale app icon based on screen resolution"""
        try:
            # Calculate target size based on screen resolution using new formula
            screen_w = self.parent_root.winfo_screenwidth()
            screen_h = self.parent_root.winfo_screenheight()
            min_dimension = min(screen_w, screen_h)
            target_size = round(min_dimension / 4.2)
            target_size = max(192, min(512, target_size))  # Clamp to [192, 512]

            self.logger.debug(f"Screen: {screen_w}x{screen_h}, min_dim: {min_dimension}, target icon size: {target_size}")

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
                original_w, original_h = pil_image.size

                # Don't upscale beyond natural size
                final_w = min(target_size, original_w)
                final_h = min(target_size, original_h)

                # Maintain aspect ratio
                aspect_ratio = original_w / original_h
                if final_w / aspect_ratio < final_h:
                    final_h = round(final_w / aspect_ratio)
                else:
                    final_w = round(final_h * aspect_ratio)

                self.icon_size = (final_w, final_h)
                self.logger.debug(f"Pillow scaling: original {original_w}x{original_h} -> {final_w}x{final_h}")

                pil_image = pil_image.resize((final_w, final_h), Image.Resampling.LANCZOS)
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

                # Don't upscale beyond natural size
                final_w = min(target_size, original_w)
                final_h = min(target_size, original_h)

                # Maintain aspect ratio
                aspect_ratio = original_w / original_h
                if final_w / aspect_ratio < final_h:
                    final_h = round(final_w / aspect_ratio)
                else:
                    final_w = round(final_h * aspect_ratio)

                self.icon_size = (final_w, final_h)
                self.logger.debug(f"Tkinter scaling: original {original_w}x{original_h} -> {final_w}x{final_h}")

                # Calculate scaling factors based on final size
                scale_x = final_w / original_w
                scale_y = final_h / original_h

                if scale_x > 1 or scale_y > 1:
                    # Zoom (integer factors only)
                    zoom_factor = int(min(scale_x, scale_y)) or 1
                    result = original.zoom(zoom_factor, zoom_factor)
                    self.icon_size = (result.width(), result.height())
                    return result
                else:
                    # Subsample
                    subsample_factor = int(max(1/scale_x, 1/scale_y)) or 1
                    result = original.subsample(subsample_factor, subsample_factor)
                    self.icon_size = (result.width(), result.height())
                    return result

            except Exception as e:
                self.logger.warning(f"Error loading/scaling icon: {e}")
                self.icon_size = (target_size, target_size)  # Default size for text fallback
                return None

        except Exception as e:
            self.logger.error(f"Error in icon loading: {e}")
            self.icon_size = (96, 96)  # Safe fallback size
            return None

    def _load_icon_as_pil(self):
        """Load icon as PIL Image for layered overlay"""
        try:
            # Look for icon file
            icon_path = None
            for possible_path in [
                "resources/icon.png",
                "folder_declutter.png",
                "icon.png"
            ]:
                if os.path.exists(possible_path):
                    icon_path = possible_path
                    break

            if not icon_path:
                self.logger.warning("No icon file found for PIL loading")
                return None

            # Load with PIL
            from PIL import Image
            pil_image = Image.open(icon_path)

            # Apply same sizing logic as _load_and_scale_icon
            screen_w = self.parent_root.winfo_screenwidth()
            screen_h = self.parent_root.winfo_screenheight()
            min_dimension = min(screen_w, screen_h)
            target_size = round(min_dimension / 4.2)
            target_size = max(192, min(512, target_size))

            original_w, original_h = pil_image.size

            # Don't upscale beyond natural size
            final_w = min(target_size, original_w)
            final_h = min(target_size, original_h)

            # Maintain aspect ratio
            aspect_ratio = original_w / original_h
            if final_w / aspect_ratio < final_h:
                final_h = round(final_w / aspect_ratio)
            else:
                final_w = round(final_h * aspect_ratio)

            # Resize with high quality
            pil_image = pil_image.resize((final_w, final_h), Image.Resampling.LANCZOS)

            # Ensure RGBA mode
            if pil_image.mode != 'RGBA':
                pil_image = pil_image.convert('RGBA')

            self.logger.debug(f"PIL image loaded: {final_w}x{final_h}")
            return pil_image

        except Exception as e:
            self.logger.error(f"Error loading PIL image: {e}")
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

    def show_centered_over(self, rect: tuple[int, int, int, int]) -> None:
        """
        Show the overlay centered over the given rectangle (main window)

        Args:
            rect: (x, y, width, height) of the main window
        """
        if self.overlay or (self.layered_overlay and self.layered_overlay.is_visible):
            self.logger.debug("Overlay already shown")
            return

        x, y, w, h = rect
        ow, oh = self.icon_size

        # Compute centered position
        ox = x + (w - ow) // 2
        oy = y + (h - oh) // 2

        # Try to use Windows layered overlay first
        if self.use_layered and self.layered_overlay:
            try:
                # Load icon as PIL Image for layered overlay
                pil_image = self._load_icon_as_pil()
                if pil_image:
                    self.layered_overlay.create(pil_image, ox, oy)
                    self.logger.info(f"LayeredOverlay shown centered at ({ox}, {oy}) over rect {rect}")
                    return
                else:
                    self.logger.warning("Failed to load PIL image for layered overlay, falling back")
            except Exception as e:
                self.logger.warning(f"LayeredOverlay failed, falling back to Tk overlay: {e}")

        # Fallback to Tk overlay with chroma-key transparency
        try:
            # Create overlay window with transparency support
            self.overlay = tk.Toplevel()
            self.overlay.overrideredirect(True)  # Remove window decorations
            self.overlay.attributes('-topmost', True)  # Always on top

            # Set background to transparent key
            self.overlay.configure(bg=TRANSPARENT_KEY)

            # Enable Windows transparency if available
            if platform.system() == 'Windows':
                try:
                    self.overlay.wm_attributes('-transparentcolor', TRANSPARENT_KEY)
                    self.logger.debug("Windows chroma-key transparency enabled")
                except Exception as e:
                    self.logger.warning(f"Windows transparency not available: {e}")

            # Create content with transparent background
            if self.icon_image:
                # Use scaled icon with transparent background
                self.overlay_label = tk.Label(
                    self.overlay,
                    image=self.icon_image,
                    bg=TRANSPARENT_KEY,
                    bd=0,
                    highlightthickness=0,
                    cursor="hand2"
                )
            else:
                # Text fallback - still use transparent background
                self.overlay_label = tk.Label(
                    self.overlay,
                    text="DS",
                    font=('Arial', 24, 'bold'),
                    bg=TRANSPARENT_KEY,
                    fg='darkblue',
                    cursor="hand2",
                    bd=0,
                    highlightthickness=0,
                    padx=10,
                    pady=10
                )

            self.overlay_label.pack()

            # Bind events
            self._bind_events()

            # Position and show
            self.overlay.geometry(f"+{ox}+{oy}")
            self.overlay.deiconify()

            self.logger.info(f"Tk overlay (fallback) shown centered at ({ox}, {oy}) over rect {rect}")

        except Exception as e:
            self.logger.error(f"Error showing centered overlay: {e}")
            if self.overlay:
                try:
                    self.overlay.destroy()
                except Exception:
                    pass
                self.overlay = None

    def hide(self) -> None:
        """Hide/destroy the overlay"""
        # Handle layered overlay
        if self.layered_overlay and self.layered_overlay.is_visible:
            try:
                self.layered_overlay.hide()
                self.logger.info("LayeredOverlay hidden")
            except Exception as e:
                self.logger.error(f"Error hiding layered overlay: {e}")

        # Handle Tk overlay
        if self.overlay:
            try:
                # Store current position for next time
                x = self.overlay.winfo_x()
                y = self.overlay.winfo_y()
                self.last_position = (x, y)
                self.logger.debug(f"Stored overlay position: ({x}, {y})")

                self.overlay.destroy()
                self.logger.info("Tk overlay hidden")
            except Exception as e:
                self.logger.error(f"Error hiding Tk overlay: {e}")
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
