import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import time
from datetime import datetime
from enum import Enum
import queue
import os
import cv2
import numpy as np


def save_debug_screenshot(screenshot, line_pos, sweet_spot_start, sweet_spot_end, zone_y2_cached, velocity,
                         acceleration, prediction_used, confidence, click_count, debug_dir, smoothed_zone_x, smoothed_zone_w):
    try:
        debug_img = screenshot.copy()
        height = debug_img.shape[0]

        if smoothed_zone_x is not None:
            cv2.rectangle(debug_img, (int(smoothed_zone_x), 0),
                          (int(smoothed_zone_x + smoothed_zone_w), zone_y2_cached), (0, 255, 0), 3)

        if sweet_spot_start is not None and sweet_spot_end is not None:
            cv2.rectangle(debug_img, (int(sweet_spot_start), 0), (int(sweet_spot_end), zone_y2_cached),
                          (0, 255, 255), 3)

        if line_pos != -1:
            cv2.line(debug_img, (line_pos, 0), (line_pos, height), (0, 0, 255), 2)

        filename = f"click_{click_count + 1:03d}_{int(time.time())}.jpg"
        filepath = os.path.join(debug_dir, filename)
        cv2.imwrite(filepath, debug_img)
        return filename
    except Exception:
        return None


def log_click_debug(click_count, line_pos, velocity, acceleration, sweet_spot_start, sweet_spot_end, 
                   prediction_used, confidence, filename, debug_log_path):
    try:
        log_entry = (
            f"Click {click_count}: Line={line_pos}, Vel={velocity:.1f}, Acc={acceleration:.1f}, "
            f"Sweet={sweet_spot_start}-{sweet_spot_end}, Pred={'Y' if prediction_used else 'N'}, "
            f"Conf={confidence:.2f}, File={filename}"
        )
        
        with open(debug_log_path, 'a') as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')} - {log_entry}\n")
    except Exception:
        pass


class LogLevel(Enum):
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4


class DebugLogger:
    def __init__(self):
        self.log_queue = queue.Queue(maxsize=1000)
        self.console_window = None
        self.console_text = None
        self.auto_scroll = True
        self.max_lines = 1000
        self.always_on_top = False
        self.save_to_file = False
        self.redirect_to_console = False
        self.log_file = None
        self.log_history = []
        self._last_update_time = 0
        self._update_interval = 0.1
        self._batch_size = 50
        self._file_buffer = []
        self._buffer_size = 100
        self.log_levels = {
            LogLevel.DEBUG: {"color": "#888888", "prefix": "[DEBUG]"},
            LogLevel.INFO: {"color": "#000000", "prefix": "[INFO]"},
            LogLevel.WARNING: {"color": "#FF8C00", "prefix": "[WARN]"},
            LogLevel.ERROR: {"color": "#FF0000", "prefix": "[ERROR]"}
        }
        
    def debug(self, message):
        self._log(LogLevel.DEBUG, message)
        
    def info(self, message):
        self._log(LogLevel.INFO, message)
        
    def warning(self, message):
        self._log(LogLevel.WARNING, message)
        
    def error(self, message):
        self._log(LogLevel.ERROR, message)
        
    def _log(self, level, message):
        try:
            if self.log_queue.full():
                try:
                    self.log_queue.get_nowait()
                except queue.Empty:
                    pass
            
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_entry = {
                "timestamp": timestamp,
                "level": level,
                "message": str(message)
            }
            
            if self.save_to_file:
                if len(self.log_history) > 5000:
                    self.log_history = self.log_history[-2500:]
                self.log_history.append(log_entry)
            
            if self.redirect_to_console:
                level_info = self.log_levels[level]
                formatted_message = f"{timestamp} {level_info['prefix']} {message}"
                print(formatted_message)
            
            self.log_queue.put_nowait(log_entry)
            
            if self.save_to_file and self.log_file:
                self._buffer_file_write(log_entry)
            
            current_time = time.time()
            if (self.console_window and self.console_text and 
                current_time - self._last_update_time > self._update_interval):
                self._last_update_time = current_time
                self.console_window.after_idle(self._update_console)
        except:
            pass
        if self.save_to_file and self.log_file:
            self._save_to_file(log_entry)
        
        if self.console_window and self.console_text:
            self.console_window.after_idle(self._update_console)
    
    def _buffer_file_write(self, entry):
        try:
            if self.log_file:
                self._file_buffer.append(entry)
                if len(self._file_buffer) >= self._buffer_size:
                    self._flush_file_buffer()
        except:
            pass
    
    def _flush_file_buffer(self):
        try:
            if self.log_file and self._file_buffer:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    for entry in self._file_buffer:
                        level_info = self.log_levels[entry["level"]]
                        formatted_message = f"{entry['timestamp']} {level_info['prefix']} {entry['message']}\n"
                        f.write(formatted_message)
                self._file_buffer.clear()
        except:
            pass
    
    def _save_to_file(self, entry):
        try:
            if self.log_file:
                level_info = self.log_levels[entry["level"]]
                formatted_message = f"{entry['timestamp']} {level_info['prefix']} {entry['message']}\n"
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(formatted_message)
        except:
            pass
    
    def _update_console(self):
        if not self.console_text:
            return
            
        try:
            processed = 0
            while not self.log_queue.empty() and processed < self._batch_size:
                entry = self.log_queue.get_nowait()
                self._add_log_entry(entry)
                processed += 1
        except queue.Empty:
            pass
    
    def _add_log_entry(self, entry):
        if not self.console_text:
            return
            
        level_info = self.log_levels[entry["level"]]
        formatted_message = f"{entry['timestamp']} {level_info['prefix']} {entry['message']}\n"
        
        line_count = int(self.console_text.index('end-1c').split('.')[0])
        if line_count > self.max_lines:
            self.console_text.delete('1.0', '2.0')
        
        self.console_text.insert(tk.END, formatted_message)
        
        start_index = f"{int(self.console_text.index('end-1c').split('.')[0])}.0"
        end_index = f"{int(self.console_text.index('end-1c').split('.')[0])}.end"
        self.console_text.tag_add(f"level_{entry['level'].name}", start_index, end_index)
        self.console_text.tag_config(f"level_{entry['level'].name}", foreground=level_info["color"])
        
        if self.auto_scroll:
            self.console_text.see(tk.END)
    
    def show_console(self):
        if self.console_window and self.console_window.winfo_exists():
            self.console_window.lift()
            return
            
        self.console_window = tk.Toplevel()
        self.console_window.title("Debug Console")
        self.console_window.geometry("800x600")
        self.console_window.attributes('-topmost', self.always_on_top)
        
        toolbar = ttk.Frame(self.console_window)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Clear", command=self._clear_console).pack(side=tk.LEFT, padx=5)
        
        self.auto_scroll_var = tk.BooleanVar(value=self.auto_scroll)
        ttk.Checkbutton(toolbar, text="Auto Scroll", variable=self.auto_scroll_var, 
                       command=self._toggle_auto_scroll).pack(side=tk.LEFT, padx=5)
        
        self.always_on_top_var = tk.BooleanVar(value=self.always_on_top)
        ttk.Checkbutton(toolbar, text="Always On Top", variable=self.always_on_top_var, 
                       command=self._toggle_always_on_top).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(toolbar, text="Max Lines:").pack(side=tk.LEFT, padx=(20, 5))
        self.max_lines_var = tk.StringVar(value=str(self.max_lines))
        max_lines_entry = ttk.Entry(toolbar, textvariable=self.max_lines_var, width=6)
        max_lines_entry.pack(side=tk.LEFT, padx=5)
        max_lines_entry.bind('<Return>', self._update_max_lines)
        
        options_frame = ttk.Frame(self.console_window)
        options_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.save_to_file_var = tk.BooleanVar(value=self.save_to_file)
        ttk.Checkbutton(options_frame, text="Save to File", variable=self.save_to_file_var, 
                       command=self._toggle_save_to_file).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(options_frame, text="Choose Log File", command=self._choose_log_file).pack(side=tk.LEFT, padx=5)
        
        self.redirect_to_console_var = tk.BooleanVar(value=self.redirect_to_console)
        ttk.Checkbutton(options_frame, text="Redirect to Console", variable=self.redirect_to_console_var, 
                       command=self._toggle_redirect_to_console).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(options_frame, text="Export Logs", command=self._export_logs).pack(side=tk.LEFT, padx=5)
        
        text_frame = ttk.Frame(self.console_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.console_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, 
                                                     font=("Consolas", 9), bg="white")
        self.console_text.pack(fill=tk.BOTH, expand=True)
        
        for level in LogLevel:
            level_info = self.log_levels[level]
            self.console_text.tag_config(f"level_{level.name}", foreground=level_info["color"])
        
        self.console_window.protocol("WM_DELETE_WINDOW", self._on_console_close)
        
        self._update_console()
    
    def _clear_console(self):
        if self.console_text:
            self.console_text.delete('1.0', tk.END)
    
    def _toggle_auto_scroll(self):
        self.auto_scroll = self.auto_scroll_var.get()
    
    def _toggle_always_on_top(self):
        self.always_on_top = self.always_on_top_var.get()
        if self.console_window:
            self.console_window.attributes('-topmost', self.always_on_top)
    
    def _toggle_save_to_file(self):
        self.save_to_file = self.save_to_file_var.get()
        if self.save_to_file and not self.log_file:
            self._choose_log_file()
    
    def _toggle_redirect_to_console(self):
        self.redirect_to_console = self.redirect_to_console_var.get()
    
    def _choose_log_file(self):
        if self.console_window:
            filename = filedialog.asksaveasfilename(
                parent=self.console_window,
                title="Choose Log File",
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                self.log_file = filename
                self.save_to_file = True
                if hasattr(self, 'save_to_file_var'):
                    self.save_to_file_var.set(True)
    
    def _export_logs(self):
        if not self.log_history:
            if self.console_window:
                messagebox.showinfo("Export Logs", "No logs to export.", parent=self.console_window)
            return
        
        if self.console_window:
            filename = filedialog.asksaveasfilename(
                parent=self.console_window,
                title="Export Logs",
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        for entry in self.log_history:
                            level_info = self.log_levels[entry["level"]]
                            formatted_message = f"{entry['timestamp']} {level_info['prefix']} {entry['message']}\n"
                            f.write(formatted_message)
                    messagebox.showinfo("Export Logs", f"Logs exported to {filename}", parent=self.console_window)
                except Exception as e:
                    messagebox.showerror("Export Error", f"Failed to export logs: {e}", parent=self.console_window)
    
    def _update_max_lines(self, event=None):
        try:
            self.max_lines = max(100, int(self.max_lines_var.get()))
        except ValueError:
            self.max_lines_var.set(str(self.max_lines))
    
    def _on_console_close(self):
        self._flush_file_buffer()
        self.console_window.destroy()
        self.console_window = None
        self.console_text = None
    
    def cleanup(self):
        self._flush_file_buffer()
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break


logger = DebugLogger()
