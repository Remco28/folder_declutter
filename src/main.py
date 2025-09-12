#!/usr/bin/env python3
"""
Desktop Sorter - Main Entry Point
Phase 2: UI Scaffold with 2x3 grid and Undo button placeholder
"""

import logging
import tkinter as tk
from ui.window import MainWindow


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
    logger.info("Starting Desktop Sorter - Phase 2")
    
    # Create Tk root window
    root = tk.Tk()
    root.title("Desktop Sorter")
    root.attributes('-topmost', True)
    
    # Set minimum window size
    root.minsize(320, 300)
    
    # Create and show main window
    app = MainWindow(root)
    app.pack(fill=tk.BOTH, expand=True)
    
    logger.info("UI initialized, starting main loop")
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        logger.info("Desktop Sorter shutting down")


if __name__ == "__main__":
    main()