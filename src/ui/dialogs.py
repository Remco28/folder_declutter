"""
Dialogs - Simple dialog wrappers for folder selection and text input
Phase 2 stubs using tkinter built-in dialogs
"""

import tkinter as tk
from tkinter import filedialog, simpledialog
import logging


logger = logging.getLogger(__name__)


def prompt_select_folder():
    """
    Prompt user to select a folder
    
    Returns:
        str|None: Selected folder path or None if cancelled
    """
    logger.debug("Prompting for folder selection")
    
    try:
        folder_path = filedialog.askdirectory(
            title="Select Folder",
            mustexist=True
        )
        
        if folder_path:
            logger.info(f"Folder selected: {folder_path}")
            return folder_path
        else:
            logger.debug("Folder selection cancelled")
            return None
            
    except Exception as e:
        logger.error(f"Error in folder selection dialog: {e}")
        return None


def prompt_text(title, initial=""):
    """
    Prompt user for text input
    
    Args:
        title (str): Dialog title
        initial (str): Initial text value
    
    Returns:
        str|None: User input or None if cancelled
    """
    logger.debug(f"Prompting for text input: {title}")
    
    try:
        result = simpledialog.askstring(
            title=title,
            prompt="Enter text:",
            initialvalue=initial
        )
        
        if result is not None:
            logger.debug(f"Text input provided for '{title}': '{result}'")
        else:
            logger.debug(f"Text input cancelled for '{title}'")
            
        return result
        
    except Exception as e:
        logger.error(f"Error in text input dialog '{title}': {e}")
        return None