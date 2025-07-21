import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
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


def setup_debug_directory():
    try:
        # Try to get LOCALAPPDATA first
        appdata_dir = os.environ.get("LOCALAPPDATA")
        if appdata_dir and os.path.exists(appdata_dir):
            debug_dir = os.path.join(appdata_dir, "DigTool", "debug")
            return debug_dir

        # Fallback to APPDATA
        appdata_dir = os.environ.get("APPDATA")
        if appdata_dir and os.path.exists(appdata_dir):
            debug_dir = os.path.join(appdata_dir, "DigTool", "debug")
            return debug_dir

        # Final fallback to current directory
        debug_dir = os.path.join(os.getcwd(), "debug")
        logger.warning("Using current directory for debug storage as fallback") if 'logger' in globals() else None
        return debug_dir
    except Exception as e:
        if 'logger' in globals():
            logger.error(f"Error setting up debug directory: {e}")
        debug_dir = os.path.join(os.getcwd(), "debug")
        return debug_dir


def ensure_debug_directory(debug_dir=None):
    if debug_dir is None:
        debug_dir = setup_debug_directory()
    
    try:
        os.makedirs(debug_dir, exist_ok=True)
        if 'logger' in globals():
            logger.info(f"Debug directory ensured at: {debug_dir}")
        return debug_dir
    except Exception as e:
        if 'logger' in globals():
            logger.error(f"Error ensuring debug directory: {e}")
        # Fallback to current directory
        fallback_dir = os.path.join(os.getcwd(), "debug")
        try:
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir
        except Exception as fallback_error:
            if 'logger' in globals():
                logger.error(f"Fallback debug directory creation failed: {fallback_error}")
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


def save_debug_screenshot(
    screenshot,
    line_pos,
    sweet_spot_start,
    sweet_spot_end,
    zone_y2_cached,
    click_count,
    debug_dir,
    smoothed_zone_x,
    smoothed_zone_w,
):
    try:
        debug_img = screenshot.copy()
        height = debug_img.shape[0]
        if smoothed_zone_x is not None:
            cv2.rectangle(
                debug_img,
                (int(smoothed_zone_x), 0),
                (int(smoothed_zone_x + smoothed_zone_w), zone_y2_cached),
                (0, 255, 0),
                3,
            )
        if sweet_spot_start is not None and sweet_spot_end is not None:
            cv2.rectangle(
                debug_img,
                (int(sweet_spot_start), 0),
                (int(sweet_spot_end), zone_y2_cached),
                (0, 255, 255),
                3,
            )
        if line_pos != -1:
            cv2.line(debug_img, (line_pos, 0), (line_pos, height), (0, 0, 255), 2)
        filename = f"click_{click_count + 1:03d}_{int(time.time())}.jpg"
        filepath = os.path.join(debug_dir, filename)
        cv2.imwrite(filepath, debug_img)
        return filename
    except Exception:
        return None


def log_click_debug(
    click_count,
    line_pos,
    velocity,
    acceleration,
    sweet_spot_start,
    sweet_spot_end,
    prediction_used,
    confidence,
    filename,
    debug_log_path,
):
    try:
        timestamp = int(time.time() * 1000)
        log_entry = (
            f"{timestamp} - Click {click_count}: Line={line_pos}, Vel={velocity:.1f}, Acc={acceleration:.1f}, "
            f"Sweet={sweet_spot_start:.1f}-{sweet_spot_end:.1f}, Pred={'Y' if prediction_used else 'N'}, "
            f"Conf={confidence:.2f}, File={filename}"
        )
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
        
    def write(self, text):
        if text and text.strip():  
            clean_text = text.strip()
            if clean_text:
                self.logger._log(self.log_level, f"[{self.stream_name}] {clean_text}")
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
        self.max_lines = 1000
        self.always_on_top = False
        self.save_to_file = False
        self.redirect_to_console = False
        self.logging_enabled = False
        self.startup_timer = None
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
            log_entry = {
                "timestamp": timestamp,
                "level": level,
                "message": str(message),
            }

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
            if (
                self.console_window
                and self.console_text
                and current_time - self._last_update_time > self._update_interval
            ):
                self._last_update_time = current_time
                self.console_window.after_idle(self._update_console)
        except:
            pass
        if self.save_to_file and self.log_file:
            self._save_to_file(log_entry)
        if self.console_window and self.console_text:
            self.console_window.after_idle(self._update_console)

    def enable_logging_for_startup(self, duration_seconds=30):
        self.logging_enabled = True
        if hasattr(self, "startup_timer") and self.startup_timer:
            try:
                import threading

                if isinstance(self.startup_timer, threading.Timer):
                    self.startup_timer.cancel()
            except:
                pass

        import threading

        self.startup_timer = threading.Timer(
            duration_seconds, self._disable_startup_logging
        )
        self.startup_timer.start()

        self.info(f"Debug logging enabled for {duration_seconds} seconds")

    def _disable_startup_logging(self):
        self.logging_enabled = False
        self.info("Debug logging disabled (startup period ended)")

    def set_logging_enabled(self, enabled):
        self.logging_enabled = enabled
        if enabled:
            if hasattr(self, "startup_timer") and self.startup_timer:
                try:
                    self.startup_timer.cancel()
                except:
                    pass
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

    def show_console(self):
        if self.console_window and self.console_window.winfo_exists():
            self.console_window.lift()
            return
        self.console_window = tk.Toplevel()
        self.console_window.title("Debug Console")
        self.console_window.geometry("800x600")
        self.console_window.attributes("-topmost", self.always_on_top)

        try:
            import sys
            import os

            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                icon_path = os.path.join(meipass, "assets/icon.ico")
            else:
                icon_path = "assets/icon.ico"
            
            if os.path.exists(icon_path):
                self.console_window.wm_iconbitmap(icon_path)
        except Exception:
            pass
        toolbar = ttk.Frame(self.console_window)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(toolbar, text="Clear", command=self._clear_console).pack(
            side=tk.LEFT, padx=5
        )
        self.auto_scroll_var = tk.BooleanVar(value=self.auto_scroll)
        ttk.Checkbutton(
            toolbar,
            text="Auto Scroll",
            variable=self.auto_scroll_var,
            command=self._toggle_auto_scroll,
        ).pack(side=tk.LEFT, padx=5)
        self.always_on_top_var = tk.BooleanVar(value=self.always_on_top)
        ttk.Checkbutton(
            toolbar,
            text="Always On Top",
            variable=self.always_on_top_var,
            command=self._toggle_always_on_top,
        ).pack(side=tk.LEFT, padx=5)

        self.logging_enabled_var = tk.BooleanVar(value=self.logging_enabled)
        ttk.Checkbutton(
            toolbar,
            text="Enable Logging",
            variable=self.logging_enabled_var,
            command=self._toggle_logging,
        ).pack(side=tk.LEFT, padx=5)

        self.console_capture_var = tk.BooleanVar(value=self.capture_console_output)
        ttk.Checkbutton(
            toolbar,
            text="Capture Console",
            variable=self.console_capture_var,
            command=self._toggle_console_capture,
        ).pack(side=tk.LEFT, padx=5)

        options_frame = ttk.Frame(self.console_window)
        options_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.save_to_file_var = tk.BooleanVar(value=self.save_to_file)
        ttk.Checkbutton(
            options_frame,
            text="Save to File",
            variable=self.save_to_file_var,
            command=self._toggle_save_to_file,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            options_frame, text="Choose Log File", command=self._choose_log_file
        ).pack(side=tk.LEFT, padx=5)
        self.redirect_to_console_var = tk.BooleanVar(value=self.redirect_to_console)
        ttk.Checkbutton(
            options_frame,
            text="Redirect to Console",
            variable=self.redirect_to_console_var,
            command=self._toggle_redirect_to_console,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(options_frame, text="Export Logs", command=self._export_logs).pack(
            side=tk.LEFT, padx=5
        )
        text_frame = ttk.Frame(self.console_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.console_text = scrolledtext.ScrolledText(
            text_frame, wrap=tk.WORD, font=("Consolas", 9), bg="white"
        )
        self.console_text.pack(fill=tk.BOTH, expand=True)
        for level in LogLevel:
            level_info = self.log_levels[level]
            self.console_text.tag_config(
                f"level_{level.name}", foreground=level_info["color"]
            )
        self.console_window.protocol("WM_DELETE_WINDOW", self._on_console_close)

        self._populate_console_with_history_progressive()

    def _populate_console_with_history(self):
        if not self.console_text or not self.log_history:
            return

        try:
            self.console_text.delete("1.0", tk.END)

            recent_logs = (
                self.log_history[-self.max_lines :]
                if len(self.log_history) > self.max_lines
                else self.log_history
            )

            for entry in recent_logs:
                self._add_log_entry(entry)

            try:
                processed = 0
                while not self.log_queue.empty() and processed < self._batch_size:
                    entry = self.log_queue.get_nowait()
                    self._add_log_entry(entry)
                    processed += 1
            except queue.Empty:
                pass

            if self.auto_scroll:
                self.console_text.see(tk.END)
        except Exception as e:
            pass

    def _clear_console(self):
        if self.console_text:
            self.console_text.delete("1.0", tk.END)
        self.log_history.clear()
        self._file_buffer.clear()
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break

    def _toggle_auto_scroll(self):
        if hasattr(self, 'auto_scroll_var'):
            self.auto_scroll = self.auto_scroll_var.get()
        if self.auto_scroll and self.console_text:
            self.console_text.see(tk.END)

    def _toggle_always_on_top(self):
        self.always_on_top = self.always_on_top_var.get()
        if self.console_window:
            self.console_window.attributes("-topmost", self.always_on_top)

    def _toggle_logging(self):
        self.set_logging_enabled(self.logging_enabled_var.get())

    def _toggle_console_capture(self):
        if self.console_capture_var.get():
            self.enable_console_capture()
        else:
            self.disable_console_capture()

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
                filetypes=[
                    ("Log files", "*.log"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*"),
                ],
            )
            if filename:
                self.log_file = filename
                self.save_to_file = True
                if hasattr(self, "save_to_file_var"):
                    self.save_to_file_var.set(True)

    def _export_logs(self):
        if not self.log_history:
            if self.console_window:
                messagebox.showinfo(
                    "Export Logs", "No logs to export.", parent=self.console_window
                )
            return
        if self.console_window:
            filename = filedialog.asksaveasfilename(
                parent=self.console_window,
                title="Export Logs",
                defaultextension=".log",
                filetypes=[
                    ("Log files", "*.log"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*"),
                ],
            )
            if filename:
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        for entry in self.log_history:
                            level_info = self.log_levels[entry["level"]]
                            formatted_message = f"{entry['timestamp']} {level_info['prefix']} {entry['message']}\n"
                            f.write(formatted_message)
                    messagebox.showinfo(
                        "Export Logs",
                        f"Logs exported to {filename}",
                        parent=self.console_window,
                    )
                except Exception as e:
                    messagebox.showerror(
                        "Export Error",
                        f"Failed to export logs: {e}",
                        parent=self.console_window,
                    )

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
                formatted_message = (
                    f"{entry['timestamp']} {level_info['prefix']} {entry['message']}\n"
                )
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(formatted_message)
        except:
            pass

    def _on_console_close(self):
        self._flush_file_buffer()
        if self.console_window and self.console_window.winfo_exists():
            self.console_window.destroy()
        self.console_window = None
        self.console_text = None

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
            return

        try:
            self.console_text.delete("1.0", tk.END)

            recent_logs = (
                self.log_history[-self.max_lines :]
                if len(self.log_history) > self.max_lines
                else self.log_history
            )

            self._history_load_index = 0
            self._history_to_load = recent_logs

            self._load_history_batch()

        except Exception as e:
            pass

    def _load_history_batch(self):
        if not hasattr(self, "_history_to_load") or not self._history_to_load:
            return

        try:
            batch_size = 50
            start_idx = self._history_load_index
            end_idx = min(start_idx + batch_size, len(self._history_to_load))

            original_auto_scroll = self.auto_scroll
            self.auto_scroll = False

            for i in range(start_idx, end_idx):
                entry = self._history_to_load[i]
                self._add_log_entry_fast(entry)

            self._history_load_index = end_idx

            if end_idx < len(self._history_to_load):
                if self.console_window and self.console_window.winfo_exists():
                    self.console_window.after(10, self._load_history_batch)
            else:
                self.auto_scroll = original_auto_scroll
                if self.auto_scroll and self.console_text:
                    self.console_text.see(tk.END)
                if hasattr(self, "_history_to_load"):
                    del self._history_to_load
                if hasattr(self, "_history_load_index"):
                    del self._history_load_index

        except Exception:
            if "original_auto_scroll" in locals():
                self.auto_scroll = original_auto_scroll

    def _add_log_entry_fast(self, entry):
        if not self.console_text:
            return
        level_info = self.log_levels[entry["level"]]
        formatted_message = (
            f"{entry['timestamp']} {level_info['prefix']} {entry['message']}\n"
        )

        self.console_text.insert(tk.END, formatted_message)
        start_index = f"{int(self.console_text.index('end-1c').split('.')[0])}.0"
        end_index = f"{int(self.console_text.index('end-1c').split('.')[0])}.end"
        self.console_text.tag_add(
            f"level_{entry['level'].name}", start_index, end_index
        )
        self.console_text.tag_config(
            f"level_{entry['level'].name}", foreground=level_info["color"]
        )

    def _add_log_entry(self, entry):
        if not self.console_text:
            return
        level_info = self.log_levels[entry["level"]]
        formatted_message = (
            f"{entry['timestamp']} {level_info['prefix']} {entry['message']}\n"
        )

        line_count = int(self.console_text.index("end-1c").split(".")[0])
        if line_count > self.max_lines:
            lines_to_delete = line_count - int(self.max_lines * 0.8)
            for _ in range(lines_to_delete):
                try:
                    self.console_text.delete("1.0", "2.0")
                except tk.TclError:
                    break

        self.console_text.insert(tk.END, formatted_message)
        start_index = f"{int(self.console_text.index('end-1c').split('.')[0])}.0"
        end_index = f"{int(self.console_text.index('end-1c').split('.')[0])}.end"
        self.console_text.tag_add(
            f"level_{entry['level'].name}", start_index, end_index
        )
        self.console_text.tag_config(
            f"level_{entry['level'].name}", foreground=level_info["color"]
        )
        if self.auto_scroll:
            self.console_text.see(tk.END)

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
            f.write(
                "Format: Timestamp - Click#: Line=pos, Vel=velocity, Acc=acceleration, Sweet=start-end, Pred=Y/N, Conf=confidence, File=screenshot\n"
            )
            f.write("-" * 120 + "\n")
        
        logger.info(f"Debug log initialized at: {debug_log_path}")
        return debug_log_path
    except Exception as e:
        logger.error(f"Error creating debug log: {e}")
        return None
