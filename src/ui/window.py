"""
MainWindow - Kondor Decluttering Assistant main UI window
Contains 2x3 grid of section tiles, Recycle Bin, and Undo button
"""

import tkinter as tk
import logging
import os
from .section import SectionTile
from .mini_overlay import MiniOverlay
from ..file_handler.file_operations import FileOperations
from ..services.undo import UndoService
from ..services.recycle_bin import RecycleBinService
from .dialogs import prompt_confirm_recycle, prompt_invalid_target, prompt_select_folder


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
        self.recycle_bin_service = RecycleBinService(self.parent, logger=self.logger)

        # Initialize mini overlay for minimize-to-overlay functionality
        try:
            self._mini_overlay = MiniOverlay(self.parent, self._on_overlay_restore, logger=self.logger)
        except Exception as e:
            self.logger.warning(f"Failed to initialize mini overlay: {e}")
            self._mini_overlay = None

        self._setup_ui()
        self._setup_keyboard_bindings()
        self._setup_dragdrop()
        self._setup_minimize_handling()
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
                # Validate path and log detailed reason if invalid
                if not os.path.exists(path):
                    self.logger.warning(f"Section {section_id} '{label}' has invalid path: {path} (Folder not found)")
                elif not os.access(path, os.W_OK):
                    self.logger.warning(f"Section {section_id} '{label}' has invalid path: {path} (No write permission)")

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

    def _setup_minimize_handling(self):
        """Setup minimize-to-overlay functionality"""
        if not self._mini_overlay:
            self.logger.info("Mini overlay not available - minimize handling disabled")
            return

        try:
            # Bind to minimize/unmap events
            self.parent.bind('<Unmap>', self._on_window_minimize)
            self.logger.info("Minimize-to-overlay handling setup complete")
        except Exception as e:
            self.logger.error(f"Error setting up minimize handling: {e}")

    def _on_window_minimize(self, event):
        """Handle window minimize event - show overlay"""
        if not self._mini_overlay:
            return

        try:
            # Check if this is actually a minimize (iconify) event
            if self.parent.state() == 'iconic':
                self.logger.info("Window minimized - showing mini overlay")

                # Compute main window geometry before withdrawing
                x = self.parent.winfo_x()
                y = self.parent.winfo_y()
                w = self.parent.winfo_width()
                h = self.parent.winfo_height()

                # Hide the main window completely
                self.parent.withdraw()

                # Show the overlay centered over the main window position
                self._mini_overlay.show_centered_over((x, y, w, h))

        except Exception as e:
            self.logger.error(f"Error handling window minimize: {e}")

    def _on_overlay_restore(self):
        """Handle restore request from overlay - restore main window"""
        try:
            self.logger.info("Overlay restore requested - restoring main window")

            # Hide the overlay first
            if self._mini_overlay:
                self._mini_overlay.hide()

            # Restore and focus the main window
            self.parent.deiconify()
            self.parent.lift()
            self.parent.focus_force()

        except Exception as e:
            self.logger.error(f"Error restoring from overlay: {e}")

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

        # Handle Recycle Bin drops
        if section_id is None:
            self._handle_recycle_bin_drop(paths)
            return

        # Validate section exists and has path
        if section_id not in self.sections:
            self.logger.warning(f"Cannot drop to undefined section {section_id}")
            return

        section_data = self.sections[section_id]
        target_dir = section_data.get('path')

        if not target_dir:
            self.logger.warning(f"Cannot drop to section {section_id} - no target path configured")
            # Route to invalid section recovery flow
            tile = self.tiles[section_id]
            self._handle_invalid_section_drop(section_id, paths, tile)
            return

        # Check if section is valid - revalidate at drop time
        tile = self.tiles[section_id]
        if not tile.revalidate():
            # Section is invalid - show recovery dialog
            self.logger.warning(f"Drop to invalid section {section_id}: {tile.get_invalid_reason()}")
            self._handle_invalid_section_drop(section_id, paths, tile)
            return

        # Build move request
        move_request = {
            'sources': paths,
            'target_dir': target_dir,
            'options': {}
        }

        # Start file operation
        self.logger.info(f"Starting move operation: {len(paths)} items to {target_dir}")

        self.file_operations.move_many(move_request, self._on_move_done)

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

        # Update in-memory state to keep runtime consistent
        if section_data is None:
            # Section cleared
            if section_id in self.sections:
                del self.sections[section_id]
        else:
            self.sections[section_id] = section_data

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

    def _handle_recycle_bin_drop(self, paths):
        """
        Handle dropping files/folders onto the Recycle Bin

        Args:
            paths: List of absolute file/folder paths to recycle
        """
        if not self.recycle_bin_service.is_available():
            self.logger.warning(f"Recycle bin operations not available - ignoring {len(paths)} items")
            return

        # Check if confirmation is needed
        should_confirm = len(paths) >= 5 or os.getenv('DS_CONFIRM_RECYCLE') == '1'

        if should_confirm:
            self.logger.info(f"Requesting confirmation for recycling {len(paths)} items")

            # Temporarily disable pass-through and topmost for dialog
            if self.pass_through_controller:
                with self.pass_through_controller.temporarily_disable_while(lambda: None):
                    try:
                        self.parent.attributes('-topmost', False)
                    except Exception:
                        pass
                    try:
                        if not prompt_confirm_recycle(len(paths), parent=self.parent):
                            self.logger.info("Recycle operation cancelled by user")
                            return
                    finally:
                        try:
                            self.parent.attributes('-topmost', True)
                        except Exception:
                            pass
            else:
                if not prompt_confirm_recycle(len(paths), parent=self.parent):
                    self.logger.info("Recycle operation cancelled by user")
                    return

        # Start recycle operation
        self.logger.info(f"Starting recycle operation: {len(paths)} items")

        def on_recycle_done(results):
            """Handle completion of recycle operation"""
            # Count results
            ok_count = sum(1 for r in results if r.get('status') == 'ok')
            error_count = len(results) - ok_count

            # Log summary
            self.logger.info(f"Recycle completed: {ok_count} moved to recycle bin, {error_count} errors")

            # Log individual errors
            for result in results:
                if result.get('status') == 'error':
                    self.logger.error(f"Failed to recycle {result.get('path', '')}: {result.get('error', 'Unknown error')}")

            # Note: Do not push to undo stack for recycle bin operations
            # Users can restore from Windows Recycle Bin if needed

        self.recycle_bin_service.delete_many(paths, on_recycle_done)

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

    def _handle_invalid_section_drop(self, section_id, paths, tile):
        """
        Handle dropping files onto an invalid section with recovery dialog

        Args:
            section_id: The section ID that is invalid
            paths: List of paths that were dropped
            tile: The SectionTile instance
        """
        section_data = self.sections[section_id]
        label = section_data.get('label', f'Section {section_id}')
        current_path = section_data.get('path', '')

        # Show recovery dialog
        if self.pass_through_controller:
            with self.pass_through_controller.temporarily_disable_while(lambda: None):
                try:
                    self.parent.attributes('-topmost', False)
                except Exception:
                    pass
                try:
                    choice = prompt_invalid_target(label, current_path, parent=self.parent)
                finally:
                    try:
                        self.parent.attributes('-topmost', True)
                        self.parent.lift()
                        self.parent.focus_force()
                    except Exception:
                        pass
        else:
            try:
                self.parent.attributes('-topmost', False)
            except Exception:
                pass
            try:
                choice = prompt_invalid_target(label, current_path, parent=self.parent)
            finally:
                try:
                    self.parent.attributes('-topmost', True)
                    self.parent.lift()
                    self.parent.focus_force()
                except Exception:
                    pass

        if choice == 'reselect':
            # Let user pick a new folder
            if self.pass_through_controller:
                with self.pass_through_controller.temporarily_disable_while(lambda: None):
                    try:
                        self.parent.attributes('-topmost', False)
                    except Exception:
                        pass
                    try:
                        new_path = prompt_select_folder(parent=self.parent)
                    finally:
                        try:
                            self.parent.attributes('-topmost', True)
                            self.parent.lift()
                            self.parent.focus_force()
                        except Exception:
                            pass
            else:
                try:
                    self.parent.attributes('-topmost', False)
                except Exception:
                    pass
                try:
                    new_path = prompt_select_folder(parent=self.parent)
                finally:
                    try:
                        self.parent.attributes('-topmost', True)
                        self.parent.lift()
                        self.parent.focus_force()
                    except Exception:
                        pass

            if new_path:
                # Update the section with new path
                tile.update_path(new_path)
                self.logger.info(f"Section {section_id} path updated to: {new_path}")

                # Now proceed with the original drop to the new path
                updated_section_data = self.sections[section_id]
                target_dir = updated_section_data.get('path')

                if target_dir and tile.is_valid():
                    move_request = {
                        'sources': paths,
                        'target_dir': target_dir,
                        'options': {}
                    }

                    self.file_operations.move_many(move_request, self._on_move_done)
                    self.logger.info(f"Proceeding with move after path reselect: {len(paths)} items to {target_dir}")
                else:
                    self.logger.warning(f"Section {section_id} still invalid after reselect")

        elif choice == 'remove':
            # Clear the section
            tile.clear_section()
            self.logger.info(f"Section {section_id} cleared by user")

        # If choice is None (cancel), do nothing

    def _on_move_done(self, batch_result, undo_actions):
        """
        Handle completion of move operation - reusable handler

        Args:
            batch_result: Result from file operations
            undo_actions: List of undo actions to add to stack
        """
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

    def cleanup(self):
        """Clean up resources on shutdown"""
        if hasattr(self, 'file_operations'):
            self.file_operations.shutdown()
        if hasattr(self, 'undo_service'):
            self.undo_service.shutdown()
        if hasattr(self, 'recycle_bin_service'):
            self.recycle_bin_service.shutdown()
        if hasattr(self, '_mini_overlay') and self._mini_overlay:
            self._mini_overlay.hide()
        self.logger.info("MainWindow cleanup completed")
