import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import os

import sys


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
        self.window = tk.Toplevel(self.parent)
        self.window.title(self.title)
        self.window.geometry("550x500")
        self.window.resizable(True, True)
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)

        self.window.wm_iconbitmap(os.path.join(sys._MEIPASS, "assets/icon.ico") if hasattr(sys, '_MEIPASS') else "assets/icon.ico")

        if hasattr(self.parent, 'attributes') and self.parent.attributes('-topmost'):
            self.window.attributes('-topmost', True)

    def _setup_ui(self):
        main_frame = ttk.Frame(self.window, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._create_progress_section(main_frame)
        self._create_text_section(main_frame)
        self._create_button_section(main_frame)

    def _create_progress_section(self, parent):
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding="10")
        progress_frame.pack(fill='x', pady=(0, 10))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                            maximum=100, length=400)
        self.progress_bar.pack(fill='x')

    def _create_text_section(self, parent):
        text_frame = ttk.LabelFrame(parent, text="Operation Details", padding="10")
        text_frame.pack(fill='both', expand=True, pady=(0, 15))

        text_container = ttk.Frame(text_frame)
        text_container.pack(fill='both', expand=True)

        self.text_area = scrolledtext.ScrolledText(text_container, wrap=tk.WORD,
                                                   font=("Consolas", 9), height=20)
        self.text_area.pack(fill='both', expand=True)

    def _create_button_section(self, parent):
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', pady=(0, 10))

        self.close_button = ttk.Button(button_frame, text="Close",
                                       command=self.close_window, state='disabled')
        self.close_button.pack(side='right')

    def _center_window(self):
        self.window.update_idletasks()

        width = 550
        height = 500
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _configure_tags(self):
        if not self.text_area:
            return

        tag_configs = {
            'success': {'foreground': '#006400', 'font': ("Consolas", 9, 'bold')},
            'warning': {'foreground': '#FF8C00', 'font': ("Consolas", 9)},
            'error': {'foreground': '#DC143C', 'font': ("Consolas", 9, 'bold')},
            'info': {'foreground': '#4169E1', 'font': ("Consolas", 9)},
            'header': {'foreground': '#000000', 'font': ("Consolas", 10, 'bold')},
            'unchanged': {'foreground': '#666666', 'font': ("Consolas", 9)}
        }

        for tag, config in tag_configs.items():
            self.text_area.tag_configure(tag, **config)

    def update_progress(self, value, text=None):
        if self._is_closed or not self._is_valid():
            return

        try:
            self.progress_var.set(min(100, max(0, value)))
            if text:
                self.add_text(text, 'info')
            self._safe_update()
        except Exception:
            pass

    def add_text(self, text, tag='info'):
        if self._is_closed or not self._is_valid():
            return

        try:
            self.text_area.insert(tk.END, f"{text}\n", tag)
            self.text_area.see(tk.END)
            self._safe_update()
        except Exception:
            pass

    def add_section(self, title):
        if self._is_closed or not self._is_valid():
            return

        try:
            separator = "=" * 60
            self.text_area.insert(tk.END, f"\n{separator}\n", 'header')
            self.text_area.insert(tk.END, f"{title.upper()}\n", 'header')
            self.text_area.insert(tk.END, f"{separator}\n", 'header')
            self.text_area.see(tk.END)
            self._safe_update()
        except Exception:
            pass

    def add_summary_stats(self, loaded_count, failed_count, total_count):
        if self._is_closed or not self._is_valid():
            return

        try:
            self.add_section("OPERATION SUMMARY")

            self.add_text(f"✓ Successfully processed: {loaded_count}/{total_count}", 'success')

            if failed_count > 0:
                self.add_text(f"✗ Failed items: {failed_count}", 'error')
            else:
                self.add_text("✓ No failures detected", 'success')

        except Exception:
            pass

    def operation_complete(self, success=True):
        if self._is_closed or not self._is_valid():
            return

        try:
            self.progress_var.set(100)

            if self.close_button:
                self.close_button.config(state='normal')

            self._safe_update()

        except Exception:
            pass

    def _is_valid(self):
        return (self.window is not None and
                self.text_area is not None and
                self.progress_var is not None)

    def _safe_update(self):
        try:
            if self.window and self.window.winfo_exists():
                self.window.update_idletasks()
        except Exception:
            pass

    def _safe_destroy(self):
        try:
            if self.window and self.window.winfo_exists():
                self.window.destroy()
        except Exception:
            pass
        finally:
            self.window = None
            self.text_area = None
            self.progress_var = None
            self.progress_bar = None
            self.close_button = None

    def close_window(self):
        if self._is_closed:
            return

        self._is_closed = True

        try:
            if self.window and self.window.winfo_exists():
                self.window.grab_release()
        except Exception:
            pass

        self._safe_destroy()

    def show_error(self, title, message):
        if self._is_closed:
            return

        try:
            self.add_section(f"ERROR: {title}")
            self.add_text(message, 'error')
            self.operation_complete(success=False)
        except Exception:
            pass

    def add_change_entry(self, item_name, old_value, new_value, status='success'):
        if self._is_closed or not self._is_valid():
            return

        try:
            if old_value == new_value:
                self.add_text(f"─ {item_name}: {new_value} (unchanged)", 'unchanged')
            else:
                symbol = "✓" if status == 'success' else "✗"
                self.add_text(f"{symbol} {item_name}: {old_value} → {new_value}", status)
        except Exception:
            pass