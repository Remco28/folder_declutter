"""
SectionTile - Individual section tile component
Handles empty/defined states, tooltips, and context menus
"""

import tkinter as tk
from tkinter import messagebox, Menu
import logging
import os
import os.path
from typing import Dict, Optional

from . import tooltip


DEFAULT_THEME = {
    'tile_bg': '#ffffff',
    'tile_bg_hover': '#e6f0ff',
    'tile_fg': '#1f2933',
    'tile_border': '#d3d9e1',
    'tile_invalid_border': '#d14343',
    'font_family': 'Arial',
    'font_size': 11,
    'fonts': {
        'tile_plus': ('Arial', 26, 'bold'),
        'tile_label': ('Arial', 11),
        'tile_label_invalid': ('Arial', 10),
        'tile_subtle': ('Arial', 9)
    },
    'accent': '#4b91f1'
}


class SectionTile(tk.Frame):
    """Individual section tile with empty/defined states"""
    
    def __init__(
        self,
        parent,
        section_id,
        on_add_callback,
        on_section_changed_callback,
        pass_through_controller=None,
        theme: Optional[Dict] = None
    ):
        self.theme = DEFAULT_THEME.copy()
        supplied_theme = theme or {}
        # Merge nested font dictionaries safely
        base_fonts = self.theme.setdefault('fonts', {}).copy()
        supplied_fonts = supplied_theme.get('fonts', {})
        self.theme.update({k: v for k, v in supplied_theme.items() if k != 'fonts'})
        self.theme['fonts'] = {**base_fonts, **supplied_fonts}

        super().__init__(
            parent,
            relief=tk.FLAT,
            borderwidth=0,
            width=140,
            height=80,
            bg=self.theme['tile_bg'],
            highlightbackground=self.theme['tile_border'],
            highlightcolor=self.theme['tile_border'],
            highlightthickness=1
        )
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
        self._invalid_reason = None
        
        # UI elements
        self.display_label = None
        self.context_menu = None

        self._setup_ui()
        
        self.logger.debug(f"SectionTile {section_id} initialized")

    def _validate_path(self, path):
        """
        Validate a path and return validity status and reason

        Args:
            path: Path to validate

        Returns:
            tuple: (is_valid, reason) where reason is None if valid
        """
        if not path:
            return False, "No path configured"

        if not os.path.exists(path):
            return False, "Folder not found"

        if not os.access(path, os.W_OK):
            return False, "No write permission"

        return True, None
    
    def _setup_ui(self):
        """Initialize UI in empty state"""
        self._show_empty_state()
    
    def _show_empty_state(self):
        """Show tile in empty state with + button"""
        # Clear existing widgets
        for widget in self.winfo_children():
            widget.destroy()

        border_color = self.theme['tile_border']
        self.config(bg=self.theme['tile_bg'], highlightbackground=border_color, highlightcolor=border_color)

        # Plus button/label
        self.display_label = tk.Label(
            self,
            text="+",
            font=self.theme['fonts'].get('tile_plus', (self.theme['font_family'], 26, 'bold')),
            cursor="hand2",
            bg=self.theme['tile_bg'],
            fg=self.theme['accent']
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

        # Main container for label and subtitle
        container = tk.Frame(self, bg=self.theme['tile_bg'])
        container.pack(expand=True, fill=tk.BOTH)

        # Section label
        border_color = self.theme['tile_invalid_border'] if not self._is_valid else self.theme['tile_border']
        self.config(highlightbackground=border_color, highlightcolor=border_color)
        self.config(bg=self.theme['tile_bg'])
        label_key = 'tile_label_invalid' if not self._is_valid else 'tile_label'
        label_font = self.theme['fonts'].get(label_key, (self.theme['font_family'], self.theme['font_size']))
        self.display_label = tk.Label(
            container,
            text=self._label,
            font=label_font,
            wraplength=120,
            justify='center',
            relief=tk.FLAT,
            borderwidth=0,
            bg=self.theme['tile_bg'],
            fg=self.theme['tile_fg']
        )
        self.display_label.pack(expand=True, fill=tk.BOTH)

        # Add subtitle for invalid sections
        if not self._is_valid:
            subtle_font = self.theme['fonts'].get('tile_subtle', (self.theme['font_family'], max(self.theme['font_size'] - 2, 9)))
            subtitle = tk.Label(
                container,
                text="Missing or inaccessible",
                font=subtle_font,
                fg='#6b7280',
                bg=self.theme['tile_bg'],
                justify='center'
            )
            subtitle.pack(side=tk.BOTTOM, pady=(0, 2))

        # Add tooltip and context menu
        self._bind_tooltip()
        self._bind_context_menu()
    
    def _ensure_context_menu(self):
        """Ensure context menu exists and is valid, creating/recreating as needed"""
        if getattr(self, 'context_menu', None) is None:
            self.context_menu = Menu(self.winfo_toplevel(), tearoff=0)
            self._populate_context_menu(self.context_menu)
        elif not self.context_menu.winfo_exists():
            self.context_menu = Menu(self.winfo_toplevel(), tearoff=0)
            self._populate_context_menu(self.context_menu)
        return self.context_menu

    def _populate_context_menu(self, menu):
        """Populate context menu with items"""
        menu.delete(0, 'end')
        menu.add_command(label="Change Location...", command=self._change_location)
        menu.add_command(label="Rename Label...", command=self._rename_label)
        menu.add_separator()
        menu.add_command(label="Reset Section...", command=self._reset_section)
        menu.add_separator()
        menu.add_command(label="Remove Location", command=self._remove_location)
    
    def _bind_tooltip(self):
        """Bind tooltip events for defined state"""
        if self._path and self.display_label:
            tooltip.bind_tooltip(self.display_label, lambda: self._build_section_tooltip_text())
    
    def _unbind_tooltip(self):
        """Unbind tooltip events"""
        if self.display_label:
            tooltip.unbind_tooltip(self.display_label)
    
    def _bind_context_menu(self):
        """Bind right-click context menu for defined state"""
        if self.display_label:
            self.display_label.bind('<Button-3>', self._show_context_menu)
    
    def _unbind_context_menu(self):
        """Unbind context menu"""
        if self.display_label:
            self.display_label.unbind('<Button-3>')
    
    def _build_section_tooltip_text(self):
        """Build tooltip text for section display"""
        if not self._path:
            return ""

        tooltip_text = self._path
        if not self._is_valid and self._invalid_reason:
            tooltip_text += f"\n{self._invalid_reason}"

        return tooltip_text
    
    def _show_context_menu(self, event):
        """Show right-click context menu"""
        # Only show for defined tiles
        if not self._path:
            return

        menu = self._ensure_context_menu()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        except tk.TclError:
            # Recreate menu once and retry
            menu = self._ensure_context_menu()
            try:
                menu.tk_popup(event.x_root, event.y_root)
            except tk.TclError as e:
                self.logger.error(f"Context menu popup failed: {e}")
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass
    
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

    def _reset_section(self):
        """Handle Reset Section context menu item"""
        from .dialogs import prompt_select_folder, prompt_text
        import os.path

        self.logger.info(f"Starting reset for section {self.section_id}")

        root = self.winfo_toplevel()
        if self.pass_through_controller:
            with self.pass_through_controller.temporarily_disable_while(lambda: None):
                try:
                    root.attributes('-topmost', False)
                except Exception:
                    pass
                try:
                    # Step 1: Prompt for folder selection
                    new_path = prompt_select_folder(parent=root)
                    if not new_path:
                        self.logger.info(f"Section {self.section_id} reset cancelled at folder selection")
                        return

                    # Step 2: Prompt for label with folder basename as default
                    default_label = os.path.basename(new_path.rstrip(os.sep))
                    new_label = prompt_text("Enter Label", default_label, parent=root)
                    # Treat cancel (None) as abort; empty string defaults to folder basename
                    if new_label is None:
                        self.logger.info(f"Section {self.section_id} reset cancelled at label entry")
                        return

                    # If label is empty or whitespace, use folder basename
                    if not str(new_label).strip():
                        new_label = default_label
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
                # Step 1: Prompt for folder selection
                new_path = prompt_select_folder(parent=root)
                if not new_path:
                    self.logger.info(f"Section {self.section_id} reset cancelled at folder selection")
                    return

                # Step 2: Prompt for label with folder basename as default
                default_label = os.path.basename(new_path.rstrip(os.sep))
                new_label = prompt_text("Enter Label", default_label, parent=root)
                # Treat cancel (None) as abort; empty string defaults to folder basename
                if new_label is None:
                    self.logger.info(f"Section {self.section_id} reset cancelled at label entry")
                    return

                # If label is empty or whitespace, use folder basename
                if not str(new_label).strip():
                    new_label = default_label
            finally:
                try:
                    root.attributes('-topmost', True)
                    root.lift()
                    root.focus_force()
                except Exception:
                    pass

        # Apply the reset
        self.set_section(new_label, new_path)
        self.logger.info(f"Section {self.section_id} reset complete - new label: '{new_label}', new path: '{new_path}'")
    
    def set_section(self, label, path):
        """Set section to defined state with label and path"""
        self._label = label
        self._path = path
        self._is_valid, self._invalid_reason = self._validate_path(path)
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
            self._is_valid, self._invalid_reason = self._validate_path(new_path)
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
            accent = self.theme.get('accent', '#4b91f1')
            self.config(
                bg=self.theme.get('tile_bg_hover', self.theme['tile_bg']),
                highlightbackground=accent,
                highlightcolor=accent
            )
            self.logger.debug(f"Section {self.section_id} drag highlight enabled")
        else:
            border_color = self.theme['tile_invalid_border'] if not self._is_valid else self.theme['tile_border']
            self.config(
                bg=self.theme['tile_bg'],
                highlightbackground=border_color,
                highlightcolor=border_color
            )
            self.logger.debug(f"Section {self.section_id} drag highlight disabled")

    def is_valid(self):
        """
        Check if the section is valid (has a path that exists and is writable)

        Returns:
            bool: True if section is valid, False otherwise
        """
        return self._is_valid

    def get_invalid_reason(self):
        """
        Get the reason why the section is invalid

        Returns:
            str|None: Reason string if invalid, None if valid
        """
        return self._invalid_reason

    def revalidate(self):
        """
        Re-validate the current path and update display

        Returns:
            bool: True if section is valid after revalidation
        """
        if self._path:
            old_valid = self._is_valid
            self._is_valid, self._invalid_reason = self._validate_path(self._path)
            if old_valid != self._is_valid:
                self._show_defined_state()  # Refresh display
            return self._is_valid
        return False
