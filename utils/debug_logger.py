import time
from datetime import datetime
from enum import Enum
import queue
import os
import cv2
import sys
import io
import signal
import atexit
import tkinter as tk

from tkinter import filedialog, messagebox
from interface.debug_logger_window import DebugLoggerWindow


def setup_debug_directory():
    try:
        appdata_dir = os.environ.get("LOCALAPPDATA")
        if appdata_dir and os.path.exists(appdata_dir):
            return os.path.join(appdata_dir, "DigTool", "debug")
        appdata_dir = os.environ.get("APPDATA")
        if appdata_dir and os.path.exists(appdata_dir):
            return os.path.join(appdata_dir, "DigTool", "debug")
        return os.path.join(os.getcwd(), "debug")
    except Exception:
        return os.path.join(os.getcwd(), "debug")


def ensure_debug_directory(debug_dir=None):
    if debug_dir is None:
        debug_dir = setup_debug_directory()
    try:
        os.makedirs(debug_dir, exist_ok=True)
        return debug_dir
    except Exception:
        fallback_dir = os.path.join(os.getcwd(), "debug")
        try:
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir
        except Exception:
            return fallback_dir


def get_debug_log_path(debug_dir=None):
    if debug_dir is None:
        debug_dir = ensure_debug_directory()
    else:
        debug_dir = ensure_debug_directory(debug_dir)
    return os.path.join(debug_dir, "click_log.txt")


def get_debug_info(debug_dir=None):
    if debug_dir is None:
        debug_dir = setup_debug_directory()
    debug_log_path = get_debug_log_path(debug_dir)
    return {
        "debug_directory": debug_dir,
        "debug_log_path": debug_log_path,
        "exists": os.path.exists(debug_dir),
    }


def save_debug_screenshot(screenshot, line_pos, sweet_spot_start, sweet_spot_end, zone_y2_cached, click_count, debug_dir, smoothed_zone_x, smoothed_zone_w):
    try:
        debug_img = screenshot.copy()
        height = debug_img.shape[0]
        if smoothed_zone_x is not None:
            cv2.rectangle(debug_img, (int(smoothed_zone_x), 0), (int(smoothed_zone_x + smoothed_zone_w), zone_y2_cached), (0, 255, 0), 3)
        if sweet_spot_start is not None and sweet_spot_end is not None:
            cv2.rectangle(debug_img, (int(sweet_spot_start), 0), (int(sweet_spot_end), zone_y2_cached), (0, 255, 255), 3)
        if line_pos != -1:
            cv2.line(debug_img, (line_pos, 0), (line_pos, height), (0, 0, 255), 2)
        filename = f"click_{click_count + 1:03d}_{int(time.time())}.jpg"
        filepath = os.path.join(debug_dir, filename)
        cv2.imwrite(filepath, debug_img)
        return filename
    except Exception:
        return None


def log_click_debug(click_count, line_pos, velocity, acceleration, sweet_spot_start, sweet_spot_end, prediction_used, confidence, filename, debug_log_path):
    try:
        timestamp = int(time.time() * 1000)
        log_entry = (f"{timestamp} - Click {click_count}: Line={line_pos}, Vel={velocity:.1f}, Acc={acceleration:.1f}, "
                    f"Sweet={sweet_spot_start:.1f}-{sweet_spot_end:.1f}, Pred={'Y' if prediction_used else 'N'}, "
                    f"Conf={confidence:.2f}, File={filename}")
        with open(debug_log_path, "a") as f:
            f.write(f"{log_entry}\n")
    except Exception:
        pass


class LogLevel(Enum):
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4


class ConsoleRedirector(io.TextIOBase):
    def __init__(self, logger_instance, log_level=LogLevel.INFO, stream_name="CONSOLE"):
        self.logger = logger_instance
        self.log_level = log_level
        self.stream_name = stream_name
        self.buffer = ""
        self._is_logging = False
        
    def write(self, text):
        if text and text.strip() and not self._is_logging:  
            clean_text = text.strip()
            if clean_text and not clean_text.startswith("[STDOUT]") and not clean_text.startswith("[STDERR]"):
                self._is_logging = True
                try:
                    self.logger._log(self.log_level, f"[{self.stream_name}] {clean_text}")
                finally:
                    self._is_logging = False
        return len(text)
    
    def flush(self):
        pass
    
    def writable(self):
        return True


class DebugLogger:
    def __init__(self):
        self.log_queue = queue.Queue(maxsize=1000)
        self.console_window = None
        self.console_text = None
        self.auto_scroll = True
        self.max_lines = 5000
        self.always_on_top = False
        self.save_to_file = False
        self.redirect_to_console = False
        self.logging_enabled = True
        self.log_file = None
        self.log_history = []
        self._last_update_time = 0
        self._update_interval = 0.1
        self._batch_size = 50
        self._file_buffer = []
        self._buffer_size = 100
        self.capture_console_output = False
        self.original_stdout = None
        self.original_stderr = None
        self.stdout_redirector = None
        self.stderr_redirector = None
        self.ui_window = None
        
        self.log_levels = {
            LogLevel.DEBUG: {"color": "#888888", "prefix": "[DEBUG]"},
            LogLevel.INFO: {"color": "#000000", "prefix": "[INFO]"},
            LogLevel.WARNING: {"color": "#FF8C00", "prefix": "[WARN]"},
            LogLevel.ERROR: {"color": "#FF0000", "prefix": "[ERROR]"},
        }
        
        self._setup_exit_handlers()

    def _setup_exit_handlers(self):
        atexit.register(self._save_latest_log)
        def signal_handler(signum, frame):
            try:
                self.error(f"Application terminated by signal {signum}")
                self._save_latest_log()
            except:
                pass
            sys.exit(1)
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            if hasattr(signal, 'SIGBREAK'):
                signal.signal(signal.SIGBREAK, signal_handler)
        except:
            pass

    def debug(self, message):
        self._log(LogLevel.DEBUG, message)

    def info(self, message):
        self._log(LogLevel.INFO, message)

    def warning(self, message):
        self._log(LogLevel.WARNING, message)

    def error(self, message):
        self._log(LogLevel.ERROR, message)

    def _log(self, level, message):
        if not self.logging_enabled and level not in [LogLevel.ERROR, LogLevel.WARNING]:
            return
        try:
            if self.log_queue.full():
                try:
                    self.log_queue.get_nowait()
                except queue.Empty:
                    pass
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_entry = {"timestamp": timestamp, "level": level, "message": str(message)}
            if len(self.log_history) > 10000:
                self.log_history = self.log_history[-5000:]
            self.log_history.append(log_entry)
            if self.redirect_to_console and not str(message).startswith("[STDOUT]") and not str(message).startswith("[STDERR]"):
                level_info = self.log_levels[level]
                formatted_message = f"{timestamp} {level_info['prefix']} {message}"
                print(formatted_message)
            self.log_queue.put_nowait(log_entry)
            if self.save_to_file and self.log_file:
                self._buffer_file_write(log_entry)
            current_time = time.time()
            if (self.console_window and self.console_text and current_time - self._last_update_time > self._update_interval):
                self._last_update_time = current_time
                self.console_window.after_idle(self._update_console)
        except:
            pass

    def set_logging_enabled(self, enabled):
        self.logging_enabled = enabled
        if enabled:
            self.info("Debug logging manually enabled")
        else:
            self.info("Debug logging manually disabled")

    def enable_console_capture(self):
        if not self.capture_console_output:
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            self.stdout_redirector = ConsoleRedirector(self, LogLevel.INFO, "STDOUT")
            self.stderr_redirector = ConsoleRedirector(self, LogLevel.ERROR, "STDERR")
            sys.stdout = self.stdout_redirector
            sys.stderr = self.stderr_redirector
            self.capture_console_output = True
            self.info("Console output capture enabled - all message streams will be logged")

    def disable_console_capture(self):
        if self.capture_console_output:
            if self.original_stdout:
                sys.stdout = self.original_stdout
            if self.original_stderr:
                sys.stderr = self.original_stderr
            self.capture_console_output = False
            self.original_stdout = None
            self.original_stderr = None
            self.stdout_redirector = None
            self.stderr_redirector = None
            self.info("Console output capture disabled - restored original streams")

    def show_console(self, dig_tool_instance=None):
        if DebugLoggerWindow is None:
            self.error("Debug logger window UI not available")
            return
        if self.ui_window and self.ui_window.window and self.ui_window.window.winfo_exists():
            self.ui_window.window.lift()
            self.ui_window.window.focus_force()
            return
        self.ui_window = DebugLoggerWindow(self)
        self.console_window = None
        self.console_text = None
        self.ui_window.show(dig_tool_instance)
        self.console_window = self.ui_window.window
        self.console_text = self.ui_window.console_text
        if self.console_text:
            self._populate_console_with_history_progressive()

    def _format_log_message(self, entry):
        level_info = self.log_levels[entry["level"]]
        return f"{entry['timestamp']} {level_info['prefix']} {entry['message']}\n"

    def _manage_console_state(self, enabled):
        if self.console_text:
            self.console_text.config(state="normal" if enabled else "disabled")

    def _add_text_with_tags(self, formatted_message, entry):
        self.console_text.insert(tk.END, formatted_message)
        start_index = f"{int(self.console_text.index('end-1c').split('.')[0])}.0"
        end_index = f"{int(self.console_text.index('end-1c').split('.')[0])}.end"
        self.console_text.tag_add(f"level_{entry['level'].name}", start_index, end_index)
        self.console_text.tag_config(f"level_{entry['level'].name}", foreground=self.log_levels[entry["level"]]["color"])

    def _cleanup_old_lines(self):
        line_count = int(self.console_text.index("end-1c").split(".")[0])
        if line_count > self.max_lines:
            lines_to_delete = line_count - int(self.max_lines * 0.8)
            for _ in range(lines_to_delete):
                try:
                    self.console_text.delete("1.0", "2.0")
                except tk.TclError:
                    break

    def _clear_console(self):
        if self.console_text:
            self.console_text.config(state="normal")
            self.console_text.delete("1.0", tk.END)
            self.console_text.config(state="disabled")
        self.log_history.clear()
        self._file_buffer.clear()
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break
        if hasattr(self, 'ui_window') and self.ui_window:
            self.ui_window._clear_search()

    def _toggle_auto_scroll(self):
        if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'auto_scroll_var'):
            self.auto_scroll = self.ui_window.auto_scroll_var.get()
        if self.auto_scroll and self.console_text:
            self.console_text.see(tk.END)

    def _toggle_always_on_top(self):
        if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'always_on_top_var'):
            self.always_on_top = self.ui_window.always_on_top_var.get()
        if self.console_window:
            self.console_window.attributes("-topmost", self.always_on_top)

    def _toggle_logging(self):
        if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'logging_enabled_var'):
            self.set_logging_enabled(self.ui_window.logging_enabled_var.get())

    def _toggle_console_capture(self):
        if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'console_capture_var'):
            if self.ui_window.console_capture_var.get():
                self.enable_console_capture()
            else:
                self.disable_console_capture()

    def _toggle_save_to_file(self):
        if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'save_to_file_var'):
            self.save_to_file = self.ui_window.save_to_file_var.get()
        if self.save_to_file and not self.log_file:
            self._choose_log_file()

    def _toggle_redirect_to_console(self):
        if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'redirect_to_console_var'):
            self.redirect_to_console = self.ui_window.redirect_to_console_var.get()

    def _choose_log_file(self):
        if self.console_window:
            filename = filedialog.asksaveasfilename(parent=self.console_window, title="Choose Log File", defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")])
            if filename:
                self.log_file = filename
                self.save_to_file = True
                if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'save_to_file_var'):
                    self.ui_window.save_to_file_var.set(True)

    def _export_logs(self):
        if not self.log_history:
            if self.console_window:
                messagebox.showinfo("Export Logs", "No logs to export.", parent=self.console_window)
            return
        if self.console_window:
            filename = filedialog.asksaveasfilename(parent=self.console_window, title="Export Logs", defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")])
            if filename:
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        for entry in self.log_history:
                            f.write(self._format_log_message(entry))
                    messagebox.showinfo("Export Logs", f"Logs exported to {filename}", parent=self.console_window)
                except Exception as e:
                    messagebox.showerror("Export Error", f"Failed to export logs: {e}", parent=self.console_window)

    def _write_log_to_file(self, entry, file_handle=None):
        formatted_message = self._format_log_message(entry)
        if file_handle:
            file_handle.write(formatted_message)
        elif self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(formatted_message)

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
                with open(self.log_file, "a", encoding="utf-8") as f:
                    for entry in self._file_buffer:
                        self._write_log_to_file(entry, f)
                self._file_buffer.clear()
        except:
            pass

    def _on_console_close(self):
        self._flush_file_buffer()
        if self.console_window and self.console_window.winfo_exists():
            self.console_window.destroy()
        self.console_window = None
        self.console_text = None
        if self.ui_window:
            self.ui_window = None

    def _update_max_lines(self, event=None):
        try:
            if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'max_lines_var'):
                new_max = int(self.ui_window.max_lines_var.get())
                if new_max > 0:
                    self.max_lines = new_max
        except ValueError:
            if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'max_lines_var'):
                self.ui_window.max_lines_var.set(str(self.max_lines))

    def _perform_search_operation(self, search_term=None, clear_only=False):
        if hasattr(self, 'ui_window') and self.ui_window:
            from interface.debug_logger_window.search_operations import SearchOperations
            search_ops = SearchOperations(self.ui_window)
            search_ops.perform_search_operation(search_term, clear_only)

    def _on_search_change(self, event=None):
        if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'search_var'):
            search_term = self.ui_window.search_var.get().strip()
            self._perform_search_operation(search_term if search_term else None, clear_only=not search_term)

    def _clear_search(self):
        if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'search_var'):
            self.ui_window.search_var.set("")
        self._perform_search_operation(clear_only=True)

    def cleanup(self):
        self._save_latest_log()
        self._flush_file_buffer()
        self.disable_console_capture() 
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break

    def _save_latest_log(self):
        try:
            debug_dir = setup_debug_directory()
            ensure_debug_directory(debug_dir)
            latest_log_path = os.path.join(debug_dir, "latest.log")
            with open(latest_log_path, "w", encoding="utf-8") as f:
                f.write("Dig Tool Debug Log - Latest Session\n")
                f.write("=====================================\n")
                f.write(f"Saved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n\n")
                for entry in self.log_history:
                    level_info = self.log_levels[entry["level"]]
                    formatted_line = f"{entry['timestamp']} {level_info['prefix']} {entry['message']}\n"
                    f.write(formatted_line)
                if not self.log_queue.empty():
                    f.write("\n--- Remaining Queue Messages ---\n")
                    temp_queue = []
                    while not self.log_queue.empty():
                        try:
                            entry = self.log_queue.get_nowait()
                            temp_queue.append(entry)
                            level_info = self.log_levels[entry["level"]]
                            formatted_line = f"{entry['timestamp']} {level_info['prefix']} {entry['message']}\n"
                            f.write(formatted_line)
                        except queue.Empty:
                            break
                    for entry in temp_queue:
                        try:
                            self.log_queue.put_nowait(entry)
                        except queue.Full:
                            break
        except Exception as e:
            try:
                print(f"Error saving latest.log: {e}")
            except:
                pass

    def _populate_console_with_history_progressive(self):
        if not self.console_text or not self.log_history:
            if self.auto_scroll and self.console_text:
                self.console_text.see(tk.END)
            return
        try:
            self.console_text.config(state="normal")
            self.console_text.delete("1.0", tk.END)
            recent_logs = (self.log_history[-self.max_lines :] if len(self.log_history) > self.max_lines else self.log_history)
            self._history_load_index = 0
            self._history_to_load = recent_logs
            self.console_text.update_idletasks()
            self._load_history_batch()
        except Exception as e:
            self.error(f"Error populating console history: {e}")

    def _load_history_batch(self):
        if not hasattr(self, "_history_to_load") or not self._history_to_load:
            return
        try:
            batch_size = 50
            start_idx = self._history_load_index
            end_idx = min(start_idx + batch_size, len(self._history_to_load))
            should_scroll_at_end = self.auto_scroll
            for i in range(start_idx, end_idx):
                entry = self._history_to_load[i]
                self._add_log_entry_fast(entry)
            self._history_load_index = end_idx
            if end_idx < len(self._history_to_load):
                if self.console_window and self.console_window.winfo_exists():
                    self.console_window.after(10, self._load_history_batch)
            else:
                if self.console_text:
                    self.console_text.config(state="disabled")
                    self.console_text.update_idletasks()
                if should_scroll_at_end and self.console_text:
                    self.console_text.see(tk.END)
                if hasattr(self, "_history_to_load"):
                    del self._history_to_load
                if hasattr(self, "_history_load_index"):
                    del self._history_load_index
        except Exception as e:
            self.error(f"Error in load history batch: {e}")
            if self.console_text:
                self.console_text.config(state="disabled")

    def _add_log_entry_fast(self, entry):
        if not self.console_text:
            return
        try:
            formatted_message = self._format_log_message(entry)
            self.console_text.config(state="normal")
            self._add_text_with_tags(formatted_message, entry)
        except Exception as e:
            self.error(f"Error in _add_log_entry_fast: {e}")

    def _add_log_entry(self, entry):
        if not self.console_text:
            return
        formatted_message = self._format_log_message(entry)
        self._manage_console_state(True)
        self._cleanup_old_lines()
        self._add_text_with_tags(formatted_message, entry)
        self._manage_console_state(False)
        if self.auto_scroll:
            self.console_text.see(tk.END)
        if hasattr(self, 'ui_window') and self.ui_window and hasattr(self.ui_window, 'search_var') and self.ui_window.search_var.get().strip():
            self._perform_search_operation(self.ui_window.search_var.get().strip())

    def _update_console(self):
        if not self.console_text:
            return
        try:
            processed = 0
            while not self.log_queue.empty() and processed < self._batch_size:
                entry = self.log_queue.get_nowait()
                self._add_log_entry(entry)
                processed += 1
            if processed > 0 and self.auto_scroll:
                self.console_text.see(tk.END)
        except queue.Empty:
            pass


logger = DebugLogger()


def enable_console_logging():
    logger.enable_console_capture()


def init_click_debug_log(debug_log_path=None, ensure_debug_dir_func=None):
    try:
        if debug_log_path is None:
            debug_log_path = get_debug_log_path()
        else:
            debug_dir = os.path.dirname(debug_log_path)
            ensure_debug_directory(debug_dir)
        with open(debug_log_path, "w") as f:
            f.write("Dig Tool Debug Log\n")
            f.write("==================\n")
            f.write(f"Session started at timestamp: {int(time.time())}\n")
            f.write("Format: Timestamp - Click#: Line=pos, Vel=velocity, Acc=acceleration, Sweet=start-end, Pred=Y/N, Conf=confidence, File=screenshot\n")
            f.write("-" * 120 + "\n")
        logger.info(f"Debug log initialized at: {debug_log_path}")
        return debug_log_path
    except Exception as e:
        logger.error(f"Error creating debug log: {e}")
        return None
