#!/usr/bin/env python3
"""
Desktop Sorter - Main Entry Point
Phase 2: UI Scaffold with 2x3 grid and Undo button placeholder
"""

import logging
import os
import tkinter as tk
from .ui.window import MainWindow
from .services.win_integration import PassThroughController


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
    logger.info("Starting Desktop Sorter - Phase 3")
    
    # Create Tk root window
    root = tk.Tk()
    root.title("Desktop Sorter")
    root.attributes('-topmost', True)
    
    # Set minimum window size
    root.minsize(320, 300)
    
    # Initialize Windows pass-through controller
    pass_through = PassThroughController()
    pass_through.attach(root)
    
    # Create and show main window
    app = MainWindow(root, pass_through_controller=pass_through)
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
        logger.info("Desktop Sorter shutting down")


if __name__ == "__main__":
    main()