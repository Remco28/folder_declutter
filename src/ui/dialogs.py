"""
Dialogs - Simple dialog wrappers for folder selection and text input
Phase 2 stubs using tkinter built-in dialogs
"""

import tkinter as tk
from tkinter import filedialog, simpledialog
import logging


logger = logging.getLogger(__name__)


def prompt_select_folder(parent=None):
    """
    Prompt user to select a folder
    
    Returns:
        str|None: Selected folder path or None if cancelled
    """
    logger.debug("Prompting for folder selection")
    
    try:
        folder_path = filedialog.askdirectory(
            title="Select Folder",
            mustexist=True,
            parent=parent
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


def prompt_text(title, initial="", parent=None):
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
            initialvalue=initial,
            parent=parent
        )
        
        if result is not None:
            logger.debug(f"Text input provided for '{title}': '{result}'")
        else:
            logger.debug(f"Text input cancelled for '{title}'")
            
        return result
        
    except Exception as e:
        logger.error(f"Error in text input dialog '{title}': {e}")
        return None


def prompt_overwrite(target_path: str, parent=None):
    """
    Prompt user for overwrite decision when file exists

    Args:
        target_path (str): Path of existing file that would be overwritten
        parent: Parent window for dialog

    Returns:
        str|None: 'replace' to overwrite, 'skip' to skip, None to cancel batch
    """
    logger.debug(f"Prompting for overwrite decision: {target_path}")

    try:
        # Create custom dialog
        dialog = tk.Toplevel(parent)
        dialog.title("File Exists")
        dialog.resizable(False, False)
        dialog.grab_set()  # Make modal

        # Center dialog over parent
        if parent:
            parent.update_idletasks()
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 100
            dialog.geometry(f"400x200+{x}+{y}")
        else:
            dialog.geometry("400x200+400+300")

        # Dialog content
        frame = tk.Frame(dialog, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Icon and message
        icon_label = tk.Label(frame, text="⚠️", font=('Arial', 24))
        icon_label.pack(pady=(0, 10))

        message = tk.Label(frame,
                          text=f"A file with this name already exists:\n\n{target_path}\n\nWhat would you like to do?",
                          font=('Arial', 10),
                          justify=tk.CENTER,
                          wraplength=350)
        message.pack(pady=(0, 20))

        # Result variable
        result = [None]

        # Button frame
        button_frame = tk.Frame(frame)
        button_frame.pack()

        def on_replace():
            result[0] = 'replace'
            dialog.destroy()

        def on_skip():
            result[0] = 'skip'
            dialog.destroy()

        def on_cancel():
            result[0] = None
            dialog.destroy()

        # Buttons
        replace_btn = tk.Button(button_frame, text="Replace", command=on_replace, width=10)
        replace_btn.pack(side=tk.LEFT, padx=5)

        skip_btn = tk.Button(button_frame, text="Skip", command=on_skip, width=10)
        skip_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, width=10)
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # Keyboard shortcuts
        dialog.bind('<Return>', lambda e: on_replace())
        dialog.bind('<Escape>', lambda e: on_cancel())

        # Set focus and wait
        replace_btn.focus_set()
        dialog.wait_window()

        choice = result[0]
        if choice:
            logger.info(f"Overwrite choice for {target_path}: {choice}")
        else:
            logger.info(f"Overwrite cancelled for {target_path}")

        return choice

    except Exception as e:
        logger.error(f"Error in overwrite dialog: {e}")
        return None


def prompt_confirm_recycle(count: int, parent=None) -> bool:
    """
    Prompt user for confirmation before recycling files

    Args:
        count (int): Number of items to be recycled
        parent: Parent window for dialog

    Returns:
        bool: True to proceed with recycle, False to cancel
    """
    logger.debug(f"Prompting for recycle confirmation: {count} items")

    try:
        # Create custom dialog
        dialog = tk.Toplevel(parent)
        dialog.title("Confirm Recycle")
        dialog.resizable(False, False)
        dialog.grab_set()  # Make modal

        # Center dialog over parent
        if parent:
            parent.update_idletasks()
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 100
            dialog.geometry(f"400x200+{x}+{y}")
        else:
            dialog.geometry("400x200+400+300")

        # Dialog content
        frame = tk.Frame(dialog, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Icon and message
        icon_label = tk.Label(frame, text="🗑️", font=('Arial', 24))
        icon_label.pack(pady=(0, 10))

        item_text = "item" if count == 1 else "items"
        message = tk.Label(frame,
                          text=f"Are you sure you want to move {count} {item_text} to the Recycle Bin?\n\nThis action can be undone from the Recycle Bin.",
                          font=('Arial', 10),
                          justify=tk.CENTER,
                          wraplength=350)
        message.pack(pady=(0, 20))

        # Result variable
        result = [False]

        # Button frame
        button_frame = tk.Frame(frame)
        button_frame.pack()

        def on_recycle():
            result[0] = True
            dialog.destroy()

        def on_cancel():
            result[0] = False
            dialog.destroy()

        # Buttons
        recycle_btn = tk.Button(button_frame, text="Recycle", command=on_recycle, width=10)
        recycle_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, width=10)
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # Keyboard shortcuts
        dialog.bind('<Return>', lambda e: on_recycle())
        dialog.bind('<Escape>', lambda e: on_cancel())

        # Set focus and wait
        recycle_btn.focus_set()
        dialog.wait_window()

        choice = result[0]
        logger.info(f"Recycle confirmation for {count} items: {'proceed' if choice else 'cancelled'}")

        return choice

    except Exception as e:
        logger.error(f"Error in recycle confirmation dialog: {e}")
        return False


def prompt_invalid_target(label: str, path: str, parent=None):
    """
    Prompt user for action when dropping onto an invalid section

    Args:
        label (str): Section label
        path (str): Invalid path
        parent: Parent window for dialog

    Returns:
        str|None: 'reselect' to pick new folder, 'remove' to clear section, None to cancel
    """
    logger.debug(f"Prompting for invalid target action: {label} ({path})")

    try:
        # Create custom dialog
        dialog = tk.Toplevel(parent)
        dialog.title("Invalid Location")
        dialog.resizable(False, False)
        dialog.grab_set()  # Make modal

        # Center dialog over parent
        if parent:
            parent.update_idletasks()
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 100
            dialog.geometry(f"400x200+{x}+{y}")
        else:
            dialog.geometry("400x200+400+300")

        # Dialog content
        frame = tk.Frame(dialog, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Icon and message
        icon_label = tk.Label(frame, text="⚠️", font=('Arial', 24))
        icon_label.pack(pady=(0, 10))

        message = tk.Label(frame,
                          text=f"'{label}' is missing or inaccessible.\n\nWhat would you like to do?",
                          font=('Arial', 10),
                          justify=tk.CENTER,
                          wraplength=350)
        message.pack(pady=(0, 20))

        # Result variable
        result = [None]

        # Button frame
        button_frame = tk.Frame(frame)
        button_frame.pack()

        def on_reselect():
            result[0] = 'reselect'
            dialog.destroy()

        def on_remove():
            result[0] = 'remove'
            dialog.destroy()

        def on_cancel():
            result[0] = None
            dialog.destroy()

        # Buttons
        reselect_btn = tk.Button(button_frame, text="Reselect Folder…", command=on_reselect, width=15)
        reselect_btn.pack(side=tk.LEFT, padx=5)

        remove_btn = tk.Button(button_frame, text="Remove Location", command=on_remove, width=15)
        remove_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, width=10)
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # Keyboard shortcuts
        dialog.bind('<Escape>', lambda e: on_cancel())

        # Set focus and wait
        reselect_btn.focus_set()
        dialog.wait_window()

        choice = result[0]
        if choice:
            logger.info(f"Invalid target choice for {label}: {choice}")
        else:
            logger.info(f"Invalid target cancelled for {label}")

        return choice

    except Exception as e:
        logger.error(f"Error in invalid target dialog: {e}")
        return None
