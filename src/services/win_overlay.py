"""
Windows Layered Overlay - Native Windows overlay with per-pixel alpha
Uses WS_EX_LAYERED and UpdateLayeredWindow for perfect transparency
"""

import logging
import time
import platform
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

# Only import on Windows
if platform.system() == 'Windows':
    try:
        import win32gui
        import win32con
        import win32api
        from PIL import Image
        WINDOWS_AVAILABLE = True
    except ImportError:
        WINDOWS_AVAILABLE = False
else:
    WINDOWS_AVAILABLE = False


class LayeredOverlay:
    """Windows layered overlay window with per-pixel alpha"""

    def __init__(self, on_restore: Callable[[], None], logger=None):
        """
        Initialize layered overlay

        Args:
            on_restore: Callback when overlay is clicked to restore
            logger: Optional logger instance
        """
        if not WINDOWS_AVAILABLE:
            raise RuntimeError("LayeredOverlay requires Windows with pywin32 and Pillow")

        self.on_restore = on_restore
        self.logger = logger or logging.getLogger(__name__)

        # Window state
        self.hwnd = None
        self.width = 0
        self.height = 0
        self.is_visible = False

        # Mouse handling state
        self.mouse_down = False
        self.mouse_start_time = 0
        self.mouse_start_pos = (0, 0)
        self.mouse_start_screen = (0, 0)
        self.window_start_pos = (0, 0)
        self.total_movement = 0

        # GDI resources
        self.hdc_screen = None
        self.hdc_mem = None
        self.hbitmap = None
        self.old_bitmap = None

        self.logger.debug("LayeredOverlay initialized")

    def create(self, image: 'Image.Image', x: int, y: int) -> None:
        """
        Create and show the layered window with given image at position

        Args:
            image: PIL Image with RGBA data
            x, y: Position to place window
        """
        if self.hwnd:
            self.destroy()

        try:
            self.width, self.height = image.size

            # Register window class
            wc = win32gui.WNDCLASS()
            wc.hInstance = win32gui.GetModuleHandle(None)
            wc.lpszClassName = "LayeredOverlayClass"
            wc.lpfnWndProc = self._window_proc
            wc.hbrBackground = None
            wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)

            try:
                win32gui.RegisterClass(wc)
            except Exception:
                # Class might already be registered
                pass

            # Create layered window
            self.hwnd = win32gui.CreateWindowEx(
                win32con.WS_EX_LAYERED | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_TOPMOST,
                "LayeredOverlayClass",
                "LayeredOverlay",
                win32con.WS_POPUP,
                x, y, self.width, self.height,
                0, 0, win32gui.GetModuleHandle(None), None
            )

            if not self.hwnd:
                raise RuntimeError("Failed to create layered window")

            # Prepare ARGB bitmap
            self._create_argb_bitmap(image)

            # Update layered window with per-pixel alpha
            self._update_layered_window(x, y)

            # Show window
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            self.is_visible = True

            self.logger.info(f"LayeredOverlay created at ({x}, {y}) size {self.width}x{self.height}")

        except Exception as e:
            self.logger.error(f"Error creating layered overlay: {e}")
            self.destroy()
            raise

    def _create_argb_bitmap(self, image: 'Image.Image') -> None:
        """Create ARGB bitmap from PIL image"""
        try:
            # Convert to RGBA if needed
            if image.mode != 'RGBA':
                image = image.convert('RGBA')

            # Get screen DC
            self.hdc_screen = win32gui.GetDC(0)

            # Create memory DC compatible with screen
            self.hdc_mem = win32gui.CreateCompatibleDC(self.hdc_screen)

            # For layered windows, we need to use a different approach
            # Create a 32-bit bitmap and manually set the pixel data
            import ctypes
            from ctypes import wintypes

            # Create BITMAPINFO structure for 32-bit ARGB
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ('biSize', wintypes.DWORD),
                    ('biWidth', wintypes.LONG),
                    ('biHeight', wintypes.LONG),
                    ('biPlanes', wintypes.WORD),
                    ('biBitCount', wintypes.WORD),
                    ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD),
                    ('biXPelsPerMeter', wintypes.LONG),
                    ('biYPelsPerMeter', wintypes.LONG),
                    ('biClrUsed', wintypes.DWORD),
                    ('biClrImportant', wintypes.DWORD),
                ]

            class BITMAPINFO(ctypes.Structure):
                _fields_ = [
                    ('bmiHeader', BITMAPINFOHEADER),
                    ('bmiColors', wintypes.DWORD * 3),
                ]

            # Fill bitmap info
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = self.width
            bmi.bmiHeader.biHeight = -self.height  # Top-down bitmap
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = 0  # BI_RGB

            # Get image data as premultiplied BGRA for Windows layered windows
            r, g, b, a = image.split()
            try:
                from PIL import ImageChops
                rp = ImageChops.multiply(r, a)  # r * a / 255
                gp = ImageChops.multiply(g, a)
                bp = ImageChops.multiply(b, a)
            except Exception:
                # Fallback: no premultiply (may cause slight edge halos)
                rp, gp, bp = r, g, b

            # Reorder to BGRA by placing B in R slot, etc., then get raw bytes
            bgra_image = Image.merge('RGBA', (bp, gp, rp, a))
            bgra_data = bgra_image.tobytes()

            # Create DIB section using ctypes
            gdi32 = ctypes.windll.gdi32
            bits_ptr = ctypes.POINTER(ctypes.c_ubyte)()

            self.hbitmap = gdi32.CreateDIBSection(
                self.hdc_screen,
                ctypes.byref(bmi),
                0,  # DIB_RGB_COLORS
                ctypes.byref(bits_ptr),
                None,
                0
            )

            if not self.hbitmap:
                raise RuntimeError("Failed to create DIB section")

            # Copy image data to bitmap
            if bits_ptr:
                memmove = ctypes.cdll.msvcrt.memmove
                memmove(bits_ptr, bgra_data, len(bgra_data))

            # Select bitmap into memory DC
            self.old_bitmap = win32gui.SelectObject(self.hdc_mem, self.hbitmap)

            self.logger.debug(f"ARGB bitmap created: {self.width}x{self.height}")

        except Exception as e:
            self.logger.error(f"Error creating ARGB bitmap: {e}")
            self._cleanup_gdi_resources()
            raise

    def _update_layered_window(self, x: int, y: int) -> None:
        """Update layered window position and content"""
        try:
            # BLENDFUNCTION for per-pixel alpha
            blend = win32gui.BLENDFUNCTION(
                win32con.AC_SRC_OVER,  # BlendOp
                0,                     # BlendFlags
                255,                   # SourceConstantAlpha
                win32con.AC_SRC_ALPHA  # AlphaFormat - use per-pixel alpha
            )

            # Update the layered window
            result = win32gui.UpdateLayeredWindow(
                self.hwnd,              # Window handle
                self.hdc_screen,        # Destination DC
                (x, y),                 # Window position
                (self.width, self.height),  # Window size
                self.hdc_mem,           # Source DC
                (0, 0),                 # Source position
                0,                      # Color key (not used with per-pixel alpha)
                blend,                  # Blend function
                win32con.ULW_ALPHA      # Use alpha blending
            )

            if not result:
                raise RuntimeError("UpdateLayeredWindow failed")

            self.logger.debug(f"Layered window updated at ({x}, {y})")

        except Exception as e:
            self.logger.error(f"Error updating layered window: {e}")
            raise

    def move(self, x: int, y: int) -> None:
        """Move the layered window to new position"""
        if not self.hwnd or not self.is_visible:
            return

        try:
            self._update_layered_window(x, y)
            # Ensure the position is applied at the OS level as well
            try:
                import win32con
                win32gui.SetWindowPos(
                    self.hwnd,
                    win32con.HWND_TOPMOST,
                    x, y, 0, 0,
                    win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
                )
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Error moving overlay: {e}")

    def show(self) -> None:
        """Show the layered window"""
        if self.hwnd and not self.is_visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            self.is_visible = True
            self.logger.debug("LayeredOverlay shown")

    def hide(self) -> None:
        """Hide the layered window"""
        if self.hwnd and self.is_visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
            self.is_visible = False
            self.logger.debug("LayeredOverlay hidden")

    def destroy(self) -> None:
        """Destroy the layered window and cleanup resources"""
        try:
            if self.hwnd:
                if self.is_visible:
                    win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
                win32gui.DestroyWindow(self.hwnd)
                self.hwnd = None
                self.is_visible = False

            self._cleanup_gdi_resources()
            self.logger.debug("LayeredOverlay destroyed")

        except Exception as e:
            self.logger.error(f"Error destroying overlay: {e}")

    def _cleanup_gdi_resources(self) -> None:
        """Clean up GDI resources"""
        try:
            if self.old_bitmap and self.hdc_mem:
                win32gui.SelectObject(self.hdc_mem, self.old_bitmap)
                self.old_bitmap = None

            if self.hbitmap:
                win32gui.DeleteObject(self.hbitmap)
                self.hbitmap = None

            if self.hdc_mem:
                win32gui.DeleteDC(self.hdc_mem)
                self.hdc_mem = None

            if self.hdc_screen:
                win32gui.ReleaseDC(0, self.hdc_screen)
                self.hdc_screen = None

        except Exception as e:
            self.logger.error(f"Error cleaning up GDI resources: {e}")

    def _window_proc(self, hwnd, msg, wparam, lparam):
        """Window procedure for handling mouse events"""
        try:
            if msg == win32con.WM_LBUTTONDOWN:
                self._on_mouse_down(lparam)
                return 0
            elif msg == win32con.WM_MOUSEMOVE:
                self._on_mouse_move(lparam)
                return 0
            elif msg == win32con.WM_LBUTTONUP:
                self._on_mouse_up(lparam)
                return 0
            elif msg == win32con.WM_DESTROY:
                self.is_visible = False
                return 0

        except Exception as e:
            self.logger.error(f"Error in window proc: {e}")

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _on_mouse_down(self, lparam):
        """Handle mouse button down"""
        x = lparam & 0xFFFF
        y = (lparam >> 16) & 0xFFFF

        self.mouse_down = True
        self.mouse_start_time = time.time()
        self.mouse_start_pos = (x, y)
        try:
            self.mouse_start_screen = win32gui.GetCursorPos()
        except Exception:
            self.mouse_start_screen = (0, 0)
        self.total_movement = 0

        # Get current window position
        rect = win32gui.GetWindowRect(self.hwnd)
        self.window_start_pos = (rect[0], rect[1])

        # Capture mouse
        win32gui.SetCapture(self.hwnd)

        self.logger.debug(f"Mouse down at ({x}, {y})")

    def _on_mouse_move(self, lparam):
        """Handle mouse move"""
        if not self.mouse_down:
            return

        # Use screen coordinates for robust drag irrespective of client origin shifts
        try:
            cur_x, cur_y = win32gui.GetCursorPos()
        except Exception:
            # Fallback to client coords if needed
            x = lparam & 0xFFFF
            y = (lparam >> 16) & 0xFFFF
            cur_x = self.window_start_pos[0] + x
            cur_y = self.window_start_pos[1] + y

        # Calculate movement from start (screen space)
        dx = cur_x - self.mouse_start_screen[0]
        dy = cur_y - self.mouse_start_screen[1]
        movement = abs(dx) + abs(dy)  # Manhattan distance

        self.total_movement = max(self.total_movement, movement)

        # If movement > 1 pixel, treat as drag
        if movement > 1:
            new_x = self.window_start_pos[0] + dx
            new_y = self.window_start_pos[1] + dy
            self.move(new_x, new_y)

    def _on_mouse_up(self, lparam):
        """Handle mouse button up"""
        if not self.mouse_down:
            return

        # Release mouse capture
        win32gui.ReleaseCapture()

        # Calculate timing and movement
        duration = time.time() - self.mouse_start_time
        try:
            end_x, end_y = win32gui.GetCursorPos()
        except Exception:
            end_x, end_y = self.mouse_start_screen
        total = abs(end_x - self.mouse_start_screen[0]) + abs(end_y - self.mouse_start_screen[1])

        self.logger.debug(f"Mouse up: duration={duration:.3f}s, movement={self.total_movement}px")

        # Quick click restore: ≤ 200ms and ≤ 2px movement
        if duration <= 0.2 and total <= 2:
            self.logger.info("Quick click detected - triggering restore")
            # The callback should be thread-safe or handle threading internally
            try:
                self.on_restore()
            except Exception as e:
                self.logger.error(f"Error triggering restore: {e}")

        self.mouse_down = False

    def __del__(self):
        """Destructor - ensure cleanup"""
        try:
            self.destroy()
        except Exception:
            pass
