#!/usr/bin/env python3
"""
Kondor Decluttering Assistant - Main Entry Point
Phase 2: UI Scaffold with 2x3 grid and Undo button placeholder
"""

import logging
import os
import tkinter as tk
import platform
import ctypes
from .ui.window import MainWindow
from .services.win_integration import PassThroughController
from .services.dragdrop import DragDropBridge
from .config import ConfigManager

# Try to import tkinterdnd2 for proper root initialization
try:
    from tkinterdnd2 import TkinterDnD
    TKINTERDND2_AVAILABLE = True
except ImportError:
    TKINTERDND2_AVAILABLE = False


def setup_logging():
    """Initialize console logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main application entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Kondor Decluttering Assistant - Phase 4")

    # Make process DPI aware on Windows to avoid OS bitmap scaling (blurry overlays)
    if platform.system() == 'Windows':
        try:
            # Try Per-Monitor DPI awareness (Windows 8.1+)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            logger.info("DPI awareness set: Per-Monitor V2")
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                logger.info("DPI awareness set: System DPI Aware")
            except Exception as e:
                logger.warning(f"Failed to set DPI awareness: {e}")

    # Load configuration early
    config = ConfigManager.load()
    logger.info("Configuration loaded")

    # Create Tk root window with TkinterDnD support if available
    if TKINTERDND2_AVAILABLE:
        root = TkinterDnD.Tk()
        logger.info("Created TkinterDnD root window")
    else:
        root = tk.Tk()
        logger.info("Created standard Tk root window (TkinterDnD not available)")

    root.title("Kondor Decluttering Assistant")
    root.attributes('-topmost', True)
    try:
        root.configure(bg='#f4f6f8')
    except tk.TclError:
        pass

    # Set DPI-aware scaling for Tk and reasonable default geometry
    if platform.system() == 'Windows':
        try:
            # Compute Tk scaling from monitor DPI
            # Prefer GetDpiForWindow when available (Win10+)
            user32 = ctypes.windll.user32
            dpi = 96
            try:
                hwnd = root.winfo_id()
                # GetDpiForWindow returns DPI (96 = 100%)
                GetDpiForWindow = getattr(user32, 'GetDpiForWindow', None)
                if GetDpiForWindow:
                    dpi = GetDpiForWindow(hwnd)
                else:
                    # Fallback: use screen DC
                    import win32gui, win32con
                    hdc = win32gui.GetDC(0)
                    dpi = win32gui.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                    win32gui.ReleaseDC(0, hdc)
            except Exception:
                pass

            scaling = max(1.0, dpi / 72.0)
            try:
                root.tk.call('tk', 'scaling', scaling)
                logger.info(f"Tk scaling set to {scaling:.2f} (DPI={dpi})")
            except Exception as e:
                logger.warning(f"Failed to set Tk scaling: {e}")
        except Exception:
            pass

    # Set minimum and initial window size
    root.minsize(620, 420)
    try:
        # Centered reasonable default size
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w, h = 680, 560
        x = (sw - w) // 2
        y = (sh - h) // 3
        root.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        root.geometry("680x560")

    if platform.system() == 'Windows':
        try:
            user32 = ctypes.windll.user32
            GWL_STYLE = -16
            WS_MAXIMIZEBOX = 0x00010000
            hwnd = root.winfo_id()
            current_style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            if current_style & WS_MAXIMIZEBOX:
                new_style = current_style & ~WS_MAXIMIZEBOX
                user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
                root.update_idletasks()
        except Exception as e:
            logger.warning(f"Failed to adjust window styles: {e}")

    # Initialize Windows pass-through controller
    pass_through = PassThroughController()
    pass_through.attach(root)

    # Initialize drag-and-drop bridge
    dragdrop_bridge = DragDropBridge(root, pass_through_controller=pass_through)

    # Create and show main window with config, config manager, and drag-drop
    app = MainWindow(
        root,
        config=config,
        config_manager=ConfigManager,
        pass_through_controller=pass_through,
        dragdrop_bridge=dragdrop_bridge
    )
    app.pack(fill=tk.BOTH, expand=True)
    
    # Enable pass-through on Windows
    pass_through.enable()
    
    # Debug mode toggle (DS_DND_DEBUG=1)
    if os.environ.get('DS_DND_DEBUG') == '1':
        logger.info("Debug mode enabled - Ctrl+Alt+P toggles pass-through")
        def debug_toggle(event):
            pass_through.toggle()
            status = "enabled" if pass_through.is_enabled() else "disabled"
            logger.info(f"Debug toggle: pass-through {status}")
        
        root.bind_all('<Control-Alt-p>', debug_toggle)
        root.bind_all('<Control-Alt-P>', debug_toggle)
    
    logger.info("UI initialized, starting main loop")
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        # Clean shutdown
        if 'pass_through' in locals():
            pass_through.disable()
        if 'app' in locals():
            app.cleanup()
        logger.info("Kondor Decluttering Assistant shutting down")


if __name__ == "__main__":
    main()
