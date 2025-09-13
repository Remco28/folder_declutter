"""
MainWindow - Desktop Sorter main UI window
Contains 2x3 grid of section tiles, Recycle Bin, and Undo button
"""

import tkinter as tk
import logging
from .section import SectionTile


class MainWindow(tk.Frame):
    """Main application window with section grid and controls"""
    
    def __init__(self, parent, config=None, config_manager=None, pass_through_controller=None):
        super().__init__(parent)
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        self.pass_through_controller = pass_through_controller
        self.config = config or {}
        self.config_manager = config_manager

        # State tracking for sections (now persistent via config)
        self.sections = {}
        
        self._setup_ui()
        self._setup_keyboard_bindings()
        self._load_sections_from_config()

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

    def _load_sections_from_config(self):
        """Load and restore sections from configuration"""
        if not self.config or 'sections' not in self.config:
            self.logger.info("No config sections to load")
            return

        import os.path

        for section in self.config['sections']:
            section_id = section.get('id')
            label = section.get('label')
            path = section.get('path')

            # Validate section_id is valid
            if not isinstance(section_id, int) or not (0 <= section_id < 6):
                continue

            # Only load sections that have both label and path
            if label and path:
                # Validate path exists and log warning if invalid
                if not os.path.exists(path):
                    self.logger.warning(f"Section {section_id} has invalid path: {path}")

                # Set the section on the corresponding tile
                if section_id < len(self.tiles):
                    self.tiles[section_id].set_section(label, path)

                    # Update in-memory state
                    self.sections[section_id] = {
                        'id': section_id,
                        'label': label,
                        'path': path,
                        'kind': section.get('kind', 'folder')
                    }

                    self.logger.debug(f"Loaded section {section_id}: {label} -> {path}")

        self.logger.info(f"Loaded {len([s for s in self.sections.values()])} sections from config")

    def on_add_section(self, tile):
        """Handle adding a new section to a tile"""
        from .dialogs import prompt_select_folder, prompt_text
        import os.path
        
        self.logger.info(f"Adding section to tile {tile.section_id}")
        
        # Wrap dialog calls with pass-through disable
        root = self.parent
        if self.pass_through_controller:
            with self.pass_through_controller.temporarily_disable_while(lambda: None):
                # Temporarily drop topmost so dialogs appear above
                try:
                    root.attributes('-topmost', False)
                except Exception:
                    pass
                try:
                    # Prompt for folder selection
                    folder_path = prompt_select_folder(parent=root)
                    if not folder_path:
                        return
                    
                    # Prompt for label with default
                    default_label = os.path.basename(folder_path)
                    label = prompt_text("Enter Label", default_label, parent=root)
                    if label is None:
                        return
                    if not label:
                        label = default_label
                finally:
                    try:
                        root.attributes('-topmost', True)
                        root.lift()
                        root.focus_force()
                    except Exception:
                        pass
        else:
            # Fallback for when controller is not available
            try:
                root.attributes('-topmost', False)
            except Exception:
                pass
            try:
                folder_path = prompt_select_folder(parent=root)
                if not folder_path:
                    return
                
                default_label = os.path.basename(folder_path)
                label = prompt_text("Enter Label", default_label, parent=root)
                if label is None:
                    return
                if not label:
                    label = default_label
            finally:
                try:
                    root.attributes('-topmost', True)
                    root.lift()
                    root.focus_force()
                except Exception:
                    pass
        
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
        """Handle section state changes and persist to config"""
        self.logger.info(f"Section {section_id} changed: {section_data}")

        # Persist to config if config manager is available
        if self.config_manager and self.config is not None:
            if section_data is None:
                # Clear section
                self.config_manager.clear_section(self.config, section_id)
            else:
                # Update section
                self.config_manager.update_section(
                    self.config,
                    section_id,
                    label=section_data.get('label'),
                    path=section_data.get('path')
                )

            # Save config
            self.config_manager.save(self.config)
            self.logger.debug(f"Section {section_id} persisted to config")
    
    def on_undo(self):
        """Handle undo action (disabled in Phase 2)"""
        self.logger.info("Undo requested (not implemented in Phase 2)")
        # Button is disabled, but keyboard shortcut might still trigger this
        pass
