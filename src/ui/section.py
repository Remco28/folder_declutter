"""
SectionTile - Individual section tile component
Handles empty/defined states, tooltips, and context menus
"""

import tkinter as tk
from tkinter import messagebox, Menu
import logging
import os.path


class SectionTile(tk.Frame):
    """Individual section tile with empty/defined states"""
    
    def __init__(self, parent, section_id, on_add_callback, on_section_changed_callback, pass_through_controller=None):
        super().__init__(parent, relief=tk.RAISED, borderwidth=2, width=140, height=80)
        self.section_id = section_id
        self.on_add_callback = on_add_callback
        self.on_section_changed_callback = on_section_changed_callback
        self.pass_through_controller = pass_through_controller
        self.logger = logging.getLogger(__name__)
        
        # Prevent frame from shrinking
        self.pack_propagate(False)
        self.grid_propagate(False)
        
        # Section state
        self._label = None
        self._path = None
        self._is_valid = True
        
        # UI elements
        self.display_label = None
        self.tooltip = None
        self.context_menu = None
        
        self._setup_ui()
        self._setup_context_menu()
        
        self.logger.debug(f"SectionTile {section_id} initialized")
    
    def _setup_ui(self):
        """Initialize UI in empty state"""
        self._show_empty_state()
    
    def _show_empty_state(self):
        """Show tile in empty state with + button"""
        # Clear existing widgets
        for widget in self.winfo_children():
            widget.destroy()
        
        # Plus button/label
        self.display_label = tk.Label(
            self,
            text="+",
            font=('Arial', 24, 'bold'),
            cursor="hand2"
        )
        self.display_label.pack(expand=True, fill=tk.BOTH)
        
        # Bind click event
        self.display_label.bind('<Button-1>', self._on_click_add)
        
        # Remove any existing tooltips and context menu
        self._unbind_tooltip()
        self._unbind_context_menu()
    
    def _show_defined_state(self):
        """Show tile in defined state with label"""
        # Clear existing widgets
        for widget in self.winfo_children():
            widget.destroy()
        
        # Section label
        border_color = 'red' if not self._is_valid else None
        self.display_label = tk.Label(
            self,
            text=self._label,
            font=('Arial', 10),
            wraplength=120,
            justify='center',
            relief=tk.SOLID if border_color else tk.FLAT,
            borderwidth=2 if border_color else 0,
            highlightbackground=border_color if border_color else None,
            highlightthickness=2 if border_color else 0
        )
        self.display_label.pack(expand=True, fill=tk.BOTH)
        
        # Add tooltip and context menu
        self._bind_tooltip()
        self._bind_context_menu()
    
    def _setup_context_menu(self):
        """Create context menu for defined tiles"""
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Change Location...", command=self._change_location)
        self.context_menu.add_command(label="Rename Label...", command=self._rename_label)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Remove Location", command=self._remove_location)
    
    def _bind_tooltip(self):
        """Bind tooltip events for defined state"""
        if self._path and self.display_label:
            self.display_label.bind('<Enter>', self._show_tooltip)
            self.display_label.bind('<Leave>', self._hide_tooltip)
            # Also bind focus out on the main window
            self.winfo_toplevel().bind('<FocusOut>', lambda e: self._hide_tooltip(None))
    
    def _unbind_tooltip(self):
        """Unbind tooltip events"""
        if self.display_label:
            self.display_label.unbind('<Enter>')
            self.display_label.unbind('<Leave>')
    
    def _bind_context_menu(self):
        """Bind right-click context menu for defined state"""
        if self.display_label:
            self.display_label.bind('<Button-3>', self._show_context_menu)
    
    def _unbind_context_menu(self):
        """Unbind context menu"""
        if self.display_label:
            self.display_label.unbind('<Button-3>')
    
    def _show_tooltip(self, event):
        """Show tooltip with full path"""
        if not self._path:
            return
        
        # Prevent duplicate tooltips
        if self.tooltip:
            return
        
        # Create tooltip window
        self.tooltip = tk.Toplevel()
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
        
        label = tk.Label(
            self.tooltip,
            text=self._path,
            background="lightyellow",
            relief=tk.SOLID,
            borderwidth=1,
            font=('Arial', 8),
            justify='left'
        )
        label.pack()
        
        # Bind focus out to destroy tooltip
        self.tooltip.bind('<FocusOut>', lambda e: self._hide_tooltip(None))
    
    def _hide_tooltip(self, event):
        """Hide tooltip"""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
    
    def _show_context_menu(self, event):
        """Show right-click context menu"""
        # Only show for defined tiles
        if self._path and self.context_menu:
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
    def _on_click_add(self, event):
        """Handle click on empty tile"""
        self.on_add_callback(self)
    
    def _change_location(self):
        """Handle Change Location context menu item"""
        from .dialogs import prompt_select_folder
        
        root = self.winfo_toplevel()
        if self.pass_through_controller:
            with self.pass_through_controller.temporarily_disable_while(lambda: None):
                try:
                    root.attributes('-topmost', False)
                except Exception:
                    pass
                try:
                    new_path = prompt_select_folder(parent=root)
                finally:
                    try:
                        root.attributes('-topmost', True)
                        root.lift()
                        root.focus_force()
                    except Exception:
                        pass
        else:
            try:
                root.attributes('-topmost', False)
            except Exception:
                pass
            try:
                new_path = prompt_select_folder(parent=root)
            finally:
                try:
                    root.attributes('-topmost', True)
                    root.lift()
                    root.focus_force()
                except Exception:
                    pass
            
        if new_path and new_path != self._path:
            self.update_path(new_path)
            self.logger.info(f"Section {self.section_id} location changed to: {new_path}")
    
    def _rename_label(self):
        """Handle Rename Label context menu item"""
        from .dialogs import prompt_text
        
        root = self.winfo_toplevel()
        if self.pass_through_controller:
            with self.pass_through_controller.temporarily_disable_while(lambda: None):
                try:
                    root.attributes('-topmost', False)
                except Exception:
                    pass
                try:
                    new_label = prompt_text("Rename Label", self._label, parent=root)
                finally:
                    try:
                        root.attributes('-topmost', True)
                        root.lift()
                        root.focus_force()
                    except Exception:
                        pass
        else:
            try:
                root.attributes('-topmost', False)
            except Exception:
                pass
            try:
                new_label = prompt_text("Rename Label", self._label, parent=root)
            finally:
                try:
                    root.attributes('-topmost', True)
                    root.lift()
                    root.focus_force()
                except Exception:
                    pass
            
        if new_label and new_label != self._label:
            self.update_label(new_label)
            self.logger.info(f"Section {self.section_id} renamed to: {new_label}")
    
    def _remove_location(self):
        """Handle Remove Location context menu item"""
        root = self.winfo_toplevel()
        if self.pass_through_controller:
            with self.pass_through_controller.temporarily_disable_while(lambda: None):
                try:
                    root.attributes('-topmost', False)
                except Exception:
                    pass
                try:
                    result = messagebox.askyesno(
                        "Remove Location",
                        f"Remove '{self._label}' from this section?",
                        parent=root
                    )
                finally:
                    try:
                        root.attributes('-topmost', True)
                        root.lift()
                        root.focus_force()
                    except Exception:
                        pass
        else:
            try:
                root.attributes('-topmost', False)
            except Exception:
                pass
            try:
                result = messagebox.askyesno(
                    "Remove Location",
                    f"Remove '{self._label}' from this section?",
                    parent=root
                )
            finally:
                try:
                    root.attributes('-topmost', True)
                    root.lift()
                    root.focus_force()
                except Exception:
                    pass
            
        if result:
            self.clear_section()
            self.logger.info(f"Section {self.section_id} location removed")
    
    def set_section(self, label, path):
        """Set section to defined state with label and path"""
        self._label = label
        self._path = path
        self._is_valid = os.path.exists(path) if path else False
        self._show_defined_state()
        
        # Notify parent of change
        section_data = {
            'id': self.section_id,
            'label': label,
            'path': path,
            'kind': 'folder'
        }
        self.on_section_changed_callback(self.section_id, section_data)
    
    def clear_section(self):
        """Clear section to empty state"""
        self._label = None
        self._path = None
        self._is_valid = True
        self._show_empty_state()
        
        # Notify parent of change
        self.on_section_changed_callback(self.section_id, None)
    
    def update_label(self, new_label):
        """Update section label"""
        if self._path:  # Only if section is defined
            old_label = self._label
            self._label = new_label
            self._show_defined_state()
            
            # Notify parent of change
            section_data = {
                'id': self.section_id,
                'label': new_label,
                'path': self._path,
                'kind': 'folder'
            }
            self.on_section_changed_callback(self.section_id, section_data)
    
    def update_path(self, new_path):
        """Update section path"""
        if self._label:  # Only if section is defined
            old_path = self._path
            self._path = new_path
            self._is_valid = os.path.exists(new_path) if new_path else False
            self._show_defined_state()
            
            # Notify parent of change
            section_data = {
                'id': self.section_id,
                'label': self._label,
                'path': new_path,
                'kind': 'folder'
            }
            self.on_section_changed_callback(self.section_id, section_data)

    def set_drag_highlight(self, on: bool):
        """
        Set drag-and-drop highlight state

        Args:
            on: True to enable highlight, False to disable
        """
        if on:
            # Enable drag highlight - change relief and add visual emphasis
            self.config(relief=tk.SOLID, borderwidth=3)
            # Store original background to restore later
            if not hasattr(self, '_original_bg'):
                self._original_bg = self.cget('bg')
            # Set highlight background color
            self.config(bg='lightblue')
            self.logger.debug(f"Section {self.section_id} drag highlight enabled")
        else:
            # Disable drag highlight - restore original appearance
            self.config(relief=tk.RAISED, borderwidth=2)
            # Restore original background if it was stored
            if hasattr(self, '_original_bg'):
                self.config(bg=self._original_bg)
                delattr(self, '_original_bg')
            self.logger.debug(f"Section {self.section_id} drag highlight disabled")
