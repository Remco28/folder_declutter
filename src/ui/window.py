"""
MainWindow - Desktop Sorter main UI window
Contains 2x3 grid of section tiles, Recycle Bin, and Undo button
"""

import tkinter as tk
import logging
from .section import SectionTile


class MainWindow(tk.Frame):
    """Main application window with section grid and controls"""
    
    def __init__(self, parent, pass_through_controller=None):
        super().__init__(parent)
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        self.pass_through_controller = pass_through_controller
        
        # State tracking for sections (in-memory for Phase 2)
        self.sections = {}
        
        self._setup_ui()
        self._setup_keyboard_bindings()
        
        self.logger.info("MainWindow initialized")
    
    def _setup_ui(self):
        """Create the main UI layout"""
        # Main container with padding
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Section grid (2x3)
        self.grid_frame = tk.Frame(main_frame)
        self.grid_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create 6 section tiles in 2x3 grid
        self.tiles = []
        for row in range(3):
            for col in range(2):
                section_id = row * 2 + col
                tile = SectionTile(
                    self.grid_frame, 
                    section_id=section_id,
                    on_add_callback=self.on_add_section,
                    on_section_changed_callback=self.on_section_changed,
                    pass_through_controller=self.pass_through_controller
                )
                tile.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
                self.tiles.append(tile)
        
        # Configure grid weights for responsive layout
        for row in range(3):
            self.grid_frame.grid_rowconfigure(row, weight=1)
        for col in range(2):
            self.grid_frame.grid_columnconfigure(col, weight=1)
        
        # Bottom control area
        self._create_bottom_controls(main_frame)
    
    def _create_bottom_controls(self, parent):
        """Create bottom area with Recycle Bin and Undo button"""
        bottom_frame = tk.Frame(parent)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Recycle Bin area (centered)
        recycle_frame = tk.Frame(bottom_frame)
        recycle_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Recycle Bin placeholder
        self.recycle_bin_label = tk.Label(
            recycle_frame, 
            text="🗑️ Recycle Bin",
            font=('Arial', 10),
            relief=tk.RAISED,
            padx=10,
            pady=5
        )
        self.recycle_bin_label.pack(anchor='center')
        
        # Undo button (disabled)
        self.undo_button = tk.Button(
            bottom_frame,
            text="Undo",
            state='disabled',
            command=self.on_undo
        )
        self.undo_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Add tooltip to Undo button
        self._add_tooltip(self.undo_button, "Undo last action")
    
    def _setup_keyboard_bindings(self):
        """Setup keyboard shortcuts"""
        self.parent.bind_all('<Control-z>', lambda e: self.on_undo())
        self.parent.focus_set()  # Ensure window can receive key events
    
    def _add_tooltip(self, widget, text):
        """Add simple tooltip to widget"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(
                tooltip, 
                text=text, 
                background="lightyellow", 
                relief=tk.SOLID, 
                borderwidth=1,
                font=('Arial', 8)
            )
            label.pack()
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)
    
    def on_add_section(self, tile):
        """Handle adding a new section to a tile"""
        from .dialogs import prompt_select_folder, prompt_text
        import os.path
        
        self.logger.info(f"Adding section to tile {tile.section_id}")
        
        # Wrap dialog calls with pass-through disable
        if self.pass_through_controller:
            with self.pass_through_controller.temporarily_disable_while(lambda: None):
                # Prompt for folder selection
                folder_path = prompt_select_folder()
                if not folder_path:
                    return
                
                # Prompt for label with default
                default_label = os.path.basename(folder_path)
                label = prompt_text("Enter Label", default_label)
                if label is None:
                    return
                if not label:
                    label = default_label
        else:
            # Fallback for when controller is not available
            folder_path = prompt_select_folder()
            if not folder_path:
                return
            
            default_label = os.path.basename(folder_path)
            label = prompt_text("Enter Label", default_label)
            if label is None:
                return
            if not label:
                label = default_label
        
        # Update tile
        tile.set_section(label, folder_path)
        
        # Store in memory state
        section_data = {
            'id': tile.section_id,
            'label': label,
            'path': folder_path,
            'kind': 'folder'
        }
        self.sections[tile.section_id] = section_data
        
        # Notify of section change
        self.on_section_changed(tile.section_id, section_data)
    
    def on_section_changed(self, section_id, section_data):
        """Handle section state changes (placeholder for future persistence)"""
        self.logger.info(f"Section {section_id} changed: {section_data}")
    
    def on_undo(self):
        """Handle undo action (disabled in Phase 2)"""
        self.logger.info("Undo requested (not implemented in Phase 2)")
        # Button is disabled, but keyboard shortcut might still trigger this
        pass