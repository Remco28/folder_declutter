"""
MainWindow - Desktop Sorter main UI window
Contains 2x3 grid of section tiles, Recycle Bin, and Undo button
"""

import tkinter as tk
import logging
from .section import SectionTile
from ..file_handler.file_operations import FileOperations
from ..services.undo import UndoService


class MainWindow(tk.Frame):
    """Main application window with section grid and controls"""
    
    def __init__(self, parent, config=None, config_manager=None, pass_through_controller=None, dragdrop_bridge=None):
        super().__init__(parent)
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        self.pass_through_controller = pass_through_controller
        self.dragdrop_bridge = dragdrop_bridge
        self.config = config or {}
        self.config_manager = config_manager

        # State tracking for sections (now persistent via config)
        self.sections = {}
        # State tracking for drops (debugging)
        self.last_drop = None

        # Initialize file operations and undo service
        self.file_operations = FileOperations(self.parent, logger=self.logger)
        self.undo_service = UndoService(self.parent, logger=self.logger)
        
        self._setup_ui()
        self._setup_keyboard_bindings()
        self._setup_dragdrop()
        self._load_sections_from_config()
        self._update_undo_button()

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

    def _setup_dragdrop(self):
        """Setup drag-and-drop integration"""
        if not self.dragdrop_bridge or not self.dragdrop_bridge.is_available():
            self.logger.info("Drag-and-drop not available or disabled")
            return

        # Register each section tile as a drop target
        for tile in self.tiles:
            self._register_tile_drop_target(tile)

        # Register recycle bin as drop target
        self._register_recycle_bin_drop_target()

        self.logger.info("Drag-and-drop integration setup complete")

        # Bind to toplevel window leave events to handle drag cancellation
        self.parent.bind('<Leave>', self._on_window_leave)

    def _register_tile_drop_target(self, tile):
        """Register a section tile as a drop target"""
        section_id = tile.section_id

        def on_enter(event):
            tile.set_drag_highlight(True)
            self.dragdrop_bridge._start_drag_sequence()
            self.logger.debug(f"Drag enter on tile {section_id}")

        def on_leave(event):
            tile.set_drag_highlight(False)
            # Don't restore pass-through here - only on final drop or window leave
            self.logger.debug(f"Drag leave on tile {section_id}")

        def on_drop(event):
            tile.set_drag_highlight(False)
            paths = self.dragdrop_bridge.parse_drop_data(event.data)
            self.on_drop(section_id, paths)
            self.dragdrop_bridge._end_drag_sequence()
            self.logger.debug(f"Drop on tile {section_id}: {len(paths)} items")

        self.dragdrop_bridge.register_widget(tile, on_enter, on_leave, on_drop)

    def _register_recycle_bin_drop_target(self):
        """Register recycle bin label as a drop target"""
        def on_enter(event):
            self.recycle_bin_label.config(relief=tk.SUNKEN)
            self.dragdrop_bridge._start_drag_sequence()
            self.logger.debug("Drag enter on recycle bin")

        def on_leave(event):
            self.recycle_bin_label.config(relief=tk.RAISED)
            # Don't restore pass-through here - only on final drop or window leave
            self.logger.debug("Drag leave on recycle bin")

        def on_drop(event):
            self.recycle_bin_label.config(relief=tk.RAISED)
            paths = self.dragdrop_bridge.parse_drop_data(event.data)
            self.on_drop(None, paths)  # None indicates recycle bin
            self.dragdrop_bridge._end_drag_sequence()
            self.logger.debug(f"Drop on recycle bin: {len(paths)} items")

        self.dragdrop_bridge.register_widget(self.recycle_bin_label, on_enter, on_leave, on_drop)

    def _on_window_leave(self, event):
        """Handle mouse leaving the toplevel window during drag operations"""
        # Only trigger if the event is from the toplevel window itself
        if event.widget is self.parent:
            if self.dragdrop_bridge and hasattr(self.dragdrop_bridge, '_drag_in_progress'):
                if self.dragdrop_bridge._drag_in_progress:
                    # End drag sequence if drag was in progress
                    self.dragdrop_bridge._end_drag_sequence()
                    self.logger.debug("Drag sequence ended due to toplevel window leave")

    def on_drop(self, section_id, paths):
        """
        Handle drop events from drag-and-drop

        Args:
            section_id: Target section ID (0-5) or None for recycle bin
            paths: List of absolute file/folder paths
        """
        target_name = f"section {section_id}" if section_id is not None else "Recycle Bin"
        self.logger.info(f"Drop to {target_name}: {len(paths)} items")

        # Store for debugging
        self.last_drop = {
            'section_id': section_id,
            'paths': paths,
            'target_name': target_name
        }

        # Handle Recycle Bin drops (Phase 7 will implement)
        if section_id is None:
            self.logger.warning(f"Recycle Bin drops not implemented yet - ignoring {len(paths)} items")
            return

        # Validate section exists and has path
        if section_id not in self.sections:
            self.logger.warning(f"Cannot drop to undefined section {section_id}")
            return

        section_data = self.sections[section_id]
        target_dir = section_data.get('path')

        if not target_dir:
            self.logger.warning(f"Cannot drop to section {section_id} - no target path configured")
            return

        # Build move request
        move_request = {
            'sources': paths,
            'target_dir': target_dir,
            'options': {}
        }

        # Start file operation
        self.logger.info(f"Starting move operation: {len(paths)} items to {target_dir}")

        def on_move_done(batch_result, undo_actions):
            """Handle completion of move operation"""
            items = batch_result.get('items', [])

            # Count results
            ok_count = sum(1 for item in items if item.get('status') == 'ok')
            skip_count = sum(1 for item in items if item.get('status') == 'skipped')
            error_count = sum(1 for item in items if item.get('status') == 'error')

            # Log summary
            self.logger.info(f"Move completed: {ok_count} moved, {skip_count} skipped, {error_count} errors")

            # Push undo actions if there were successful operations
            if undo_actions:
                self.undo_service.push_batch(undo_actions)
                self._update_undo_button()
                self.logger.info(f"Added {len(undo_actions)} actions to undo stack")

            # Log errors
            for item in items:
                if item.get('status') == 'error':
                    self.logger.error(f"Failed to move {item.get('src', '')}: {item.get('error', 'Unknown error')}")

        self.file_operations.move_many(move_request, on_move_done)

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
        """Handle undo action"""
        if not self.undo_service.can_undo():
            self.logger.info("Undo requested but no actions available")
            return

        self.logger.info("Starting undo operation")

        def on_undo_done(success_count, failure_count):
            """Handle completion of undo operation"""
            self.logger.info(f"Undo completed: {success_count} successful, {failure_count} failed")
            self._update_undo_button()

        self.undo_service.undo_last(on_undo_done)

    def _update_undo_button(self):
        """Update undo button state based on undo service"""
        if self.undo_service.can_undo():
            self.undo_button.config(state='normal')
            batch_count = self.undo_service.get_stack_depth()
            tooltip_text = f"Undo last action ({batch_count} batch{'es' if batch_count != 1 else ''} available)"
        else:
            self.undo_button.config(state='disabled')
            tooltip_text = "Undo last action"

        # Update tooltip if it exists
        if hasattr(self.undo_button, 'tooltip_text'):
            self.undo_button.tooltip_text = tooltip_text

    def cleanup(self):
        """Clean up resources on shutdown"""
        if hasattr(self, 'file_operations'):
            self.file_operations.shutdown()
        if hasattr(self, 'undo_service'):
            self.undo_service.shutdown()
        self.logger.info("MainWindow cleanup completed")
