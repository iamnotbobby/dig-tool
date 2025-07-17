import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import threading
import sys
from utils.debug_logger import logger
from utils.pattern_utils import (get_step_colors, format_step_text, validate_step_input, 
                                safe_schedule_ui_update, check_button_cooldown,
                                validate_pattern_data, is_single_pattern, clean_pattern_data, 
                                process_pattern_steps)

from .ui_components import UIComponents
from .pattern_operations import PatternOperations
from .recording_manager import RecordingManager
from .preview_manager import PreviewManager
from .pattern_display import PatternDisplay


class CustomPatternWindow:
    def __init__(self, parent, automation_manager):
        self.parent = parent
        self.automation_manager = automation_manager
        self.window = None
        self.pattern_listbox = None
        self.preview_text = None
        self.recording_frame = None
        self.record_button = None
        self.record_status = None
        self.recorded_name_entry = None
        self.save_recorded_button = None
        self.clear_button = None
        self.custom_keys_var = None

        self._preview_running = False
        self._preview_thread = None
        
        self._update_running = False
        self._last_button_click = 0
        self._button_cooldown = 0.5

        self.ui_components = UIComponents(self)
        self.pattern_operations = PatternOperations(self)
        self.recording_manager = RecordingManager(self)
        self.preview_manager = PreviewManager(self)
        self.pattern_display = PatternDisplay(self)

    def _check_button_cooldown(self):
        success, new_time = check_button_cooldown(self._last_button_click, self._button_cooldown)
        self._last_button_click = new_time
        return success

    def _validate_ui_state(self, *required_widgets):
        if not self.window:
            return False
        
        for widget_name in required_widgets:
            if not hasattr(self, widget_name) or not getattr(self, widget_name):
                return False
        
        return True

    def _safe_schedule_ui_update(self, delay, callback):
        safe_schedule_ui_update(self.window, delay, callback)

    def show_window(self):
        if self.window is not None:
            self.window.lift()
            return
            
        self.window = tk.Toplevel(self.parent)
        self.window.title("Custom Movement Patterns")
        self.window.geometry("900x750")
        self.window.resizable(True, True)
        self.window.minsize(800, 600)

        self.window.wm_iconbitmap(os.path.join(sys._MEIPASS, "assets/icon.ico") if hasattr(sys, '_MEIPASS') else "assets/icon.ico")

        self.window.protocol("WM_DELETE_WINDOW", self.close_window)

        self.create_ui()
        self.refresh_pattern_list()

    def create_ui(self):
        self.ui_components.create_ui()

    def switch_to_patterns_tab(self):
        if self.window and hasattr(self, 'notebook'):
            try:
                self.notebook.select(0)
            except tk.TclError:
                pass
        
    def switch_to_recording_tab(self):
        if self.window and hasattr(self, 'notebook'):
            try:
                self.notebook.select(1)
            except tk.TclError:
                pass

    def refresh_pattern_list(self):
        self.pattern_operations.refresh_pattern_list()

    def close_window(self):
        if self._preview_running:
            self._stop_preview()
        
        if self.window:
            try:
                self.window.destroy()
            except tk.TclError:
                pass
            self.window = None

    def _toggle_always_on_top(self):
        if self.window:
            always_on_top = self.always_on_top_var.get()
            self.window.wm_attributes('-topmost', always_on_top)
            logger.info(f"Always on top set to: {always_on_top}")

    def _safe_preview_pattern(self):
        self.preview_manager._safe_preview_pattern()

    def _safe_preview_recorded_pattern(self):
        self.preview_manager._safe_preview_recorded_pattern()

    def _stop_preview(self):
        self.preview_manager._stop_preview()

    def _safe_toggle_recording(self):
        self.recording_manager._safe_toggle_recording()

    def _safe_save_pattern(self):
        self.recording_manager._safe_save_pattern()

    def _clear_pattern(self):
        self.recording_manager._clear_pattern()

    def _safe_delete_pattern(self):
        self.pattern_operations._safe_delete_pattern()

    def _safe_import_patterns(self):
        self.pattern_operations._safe_import_patterns()

    def _safe_export_pattern(self, pattern_name):
        self.pattern_operations._safe_export_pattern(pattern_name)

    def _safe_add_manual_key(self):
        self.recording_manager._safe_add_manual_key()

    def _show_context_menu(self, event):
        self.pattern_operations._show_context_menu(event)

    def _on_pattern_select(self, event=None):
        self.pattern_operations._on_pattern_select(event)

    def _on_custom_keys_changed(self):
        self.recording_manager._on_custom_keys_changed()

    def _refresh_pattern_list_with_selection(self):
        if not self._validate_ui_state('pattern_listbox'):
            return
            
        try:
            current_pattern_name = getattr(self, '_current_pattern_name', None)
            if not current_pattern_name:
                return
             
            self.refresh_pattern_list()
            
            def restore_selection():
                try:
                    for i in range(self.pattern_listbox.size()):
                        item_text = self.pattern_listbox.get(i)
                        if item_text.startswith(current_pattern_name + " ("):
                            self.pattern_listbox.selection_clear(0, tk.END)
                            self.pattern_listbox.selection_set(i)
                            self.pattern_listbox.see(i)
                            self.window.after_idle(lambda: self._on_pattern_select(None))
                            return True
                    return False
                except Exception as e:
                    logger.debug(f"Error in restore_selection: {e}")
                    return False
            
            if not restore_selection():
                self.window.after(100, restore_selection)
                
        except Exception as e:
            logger.debug(f"Error refreshing pattern list with selection: {e}")

    def _ensure_pattern_selected(self, pattern_name):
        try:
            if not self._validate_ui_state('pattern_listbox'):
                return
                
            for i in range(self.pattern_listbox.size()):
                item_text = self.pattern_listbox.get(i)
                if item_text.startswith(pattern_name + " ("):
                    self.pattern_listbox.selection_clear(0, tk.END)
                    self.pattern_listbox.selection_set(i)
                    self.pattern_listbox.see(i)
                    return True
            return False
        except Exception as e:
            logger.debug(f"Error ensuring pattern selected: {e}")
            return False
