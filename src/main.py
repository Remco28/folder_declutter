#!/usr/bin/env python3
"""
Desktop Sorter - Main Entry Point
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
    logger.info("Starting Desktop Sorter - Phase 4")

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

    root.title("Desktop Sorter")
    root.attributes('-topmost', True)

    # Set minimum window size
    root.minsize(320, 300)

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
        logger.info("Desktop Sorter shutting down")


if __name__ == "__main__":
    main()
