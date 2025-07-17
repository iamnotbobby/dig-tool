import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import sys

from .ui_components import UIComponents
from .progress_operations import ProgressOperations
from .window_management import WindowManagement


class SettingsFeedbackWindow:
    def __init__(self, parent, title="Settings Operation"):
        self.parent = parent
        self.window = None
        self.title = title
        self.progress_var = None
        self.progress_bar = None
        self.text_area = None
        self.close_button = None
        self._is_closed = False

        self.ui_components = UIComponents(self)
        self.progress_operations = ProgressOperations(self)
        self.window_management = WindowManagement(self)

    def show_window(self):
        if self.window is not None:
            self._safe_destroy()
        try:
            self._create_window()
            self._setup_ui()
            self._center_window()
            self._configure_tags()
        except Exception:
            self._safe_destroy()

    def _create_window(self):
        self.window_management._create_window()

    def _setup_ui(self):
        self.ui_components._setup_ui()

    def _center_window(self):
        self.window_management._center_window()

    def _configure_tags(self):
        self.ui_components._configure_tags()

    def update_progress(self, value, text=None):
        self.progress_operations.update_progress(value, text)

    def add_text(self, text, tag="info"):
        self.progress_operations.add_text(text, tag)

    def add_section(self, title):
        self.progress_operations.add_section(title)

    def add_summary_stats(self, loaded_count, failed_count, total_count):
        self.progress_operations.add_summary_stats(loaded_count, failed_count, total_count)

    def operation_complete(self, success=True):
        self.progress_operations.operation_complete(success)

    def _is_valid(self):
        return self.window_management._is_valid()

    def _safe_update(self):
        self.window_management._safe_update()

    def _safe_destroy(self):
        self.window_management._safe_destroy()

    def close_window(self):
        self.window_management.close_window()

    def show_error(self, title, message):
        self.progress_operations.show_error(title, message)

    def add_change_entry(self, item_name, old_value, new_value, status="success"):
        self.progress_operations.add_change_entry(item_name, old_value, new_value, status)
