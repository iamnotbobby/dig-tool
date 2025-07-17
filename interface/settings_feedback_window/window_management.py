import tkinter as tk
import os
import sys


class WindowManagement:
    def __init__(self, main_window):
        self.main_window = main_window

    def _create_window(self):
        self.main_window.window = tk.Toplevel(self.main_window.parent)
        self.main_window.window.title(self.main_window.title)
        self.main_window.window.geometry("550x500")
        self.main_window.window.resizable(True, True)
        self.main_window.window.transient(self.main_window.parent)
        self.main_window.window.grab_set()
        self.main_window.window.protocol("WM_DELETE_WINDOW", self.main_window.close_window)
        self.main_window.window.wm_iconbitmap(
            os.path.join(sys._MEIPASS, "assets/icon.ico")
            if hasattr(sys, "_MEIPASS")
            else "assets/icon.ico"
        )
        if hasattr(self.main_window.parent, "attributes") and self.main_window.parent.attributes("-topmost"):
            self.main_window.window.attributes("-topmost", True)

    def _center_window(self):
        self.main_window.window.update_idletasks()
        
        if hasattr(self.main_window, 'dig_tool'):
            width = int(self.main_window.dig_tool.width * 1.22)
            height = int(self.main_window.dig_tool.base_height * 0.88)
        else:
            width = 550
            height = 500
            
        screen_width = self.main_window.window.winfo_screenwidth()
        screen_height = self.main_window.window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.main_window.window.geometry(f"{width}x{height}+{x}+{y}")

    def _is_valid(self):
        return (
            self.main_window.window is not None
            and self.main_window.text_area is not None
            and self.main_window.progress_var is not None
        )

    def _safe_update(self):
        try:
            if self.main_window.window and self.main_window.window.winfo_exists():
                self.main_window.window.update_idletasks()
        except Exception:
            pass

    def _safe_destroy(self):
        try:
            if self.main_window.window and self.main_window.window.winfo_exists():
                self.main_window.window.destroy()
        except Exception:
            pass
        finally:
            self.main_window.window = None
            self.main_window.text_area = None
            self.main_window.progress_var = None
            self.main_window.progress_bar = None
            self.main_window.close_button = None

    def close_window(self):
        if self.main_window._is_closed:
            return
        self.main_window._is_closed = True
        try:
            if self.main_window.window and self.main_window.window.winfo_exists():
                self.main_window.window.grab_release()
        except Exception:
            pass
        self._safe_destroy()
