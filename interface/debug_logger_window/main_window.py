import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import sys
from .search_operations import SearchOperations

class DebugLoggerWindow:
    def __init__(self, logger_instance):
        self.logger = logger_instance
        self.window = None
        self.console_text = None
        self.search_operations = None
        self.auto_scroll_var = None
        self.always_on_top_var = None
        self.logging_enabled_var = None
        self.console_capture_var = None
        self.save_to_file_var = None
        self.redirect_to_console_var = None
        self.max_lines_var = None
        self.search_var = None
        self.search_case_var = None
        self.search_results_label = None
        self.search_entry = None
        self.max_lines_entry = None
        self.context_menu = None

    def show(self, dig_tool_instance=None):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
        self._create_window(dig_tool_instance)
        self._setup_ui_components()
        self._setup_text_widget()
        self._setup_context_menu()
        self._setup_keyboard_shortcuts()
        self._configure_tags()
        self.search_operations = SearchOperations(self)

    def _create_window(self, dig_tool_instance=None):
        self.window = tk.Toplevel()
        self.window.title("Debug Console")
        if dig_tool_instance and hasattr(dig_tool_instance, 'width') and hasattr(dig_tool_instance, 'base_height'):
            console_width = int(dig_tool_instance.width * 1.6)
            console_height = int(dig_tool_instance.base_height * 1.09)
        else:
            console_width = 800
            console_height = 600
        self.window.geometry(f"{console_width}x{console_height}")
        self.window.attributes("-topmost", self.logger.always_on_top)
        self._set_window_icon()
        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _set_window_icon(self):
        try:
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                icon_path = os.path.join(meipass, "assets/icon.ico")
            else:
                icon_path = "assets/icon.ico"
            if os.path.exists(icon_path):
                self.window.wm_iconbitmap(icon_path)
        except Exception:
            pass

    def _setup_ui_components(self):
        self._create_main_toolbar()
        self._create_options_frame()
        self._create_search_frame()

    def _create_main_toolbar(self):
        main_toolbar = ttk.Frame(self.window)
        main_toolbar.pack(fill=tk.X, padx=5, pady=5)
        left_toolbar = ttk.Frame(main_toolbar)
        left_toolbar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        right_toolbar = ttk.Frame(main_toolbar)
        right_toolbar.pack(side=tk.RIGHT)
        ttk.Button(left_toolbar, text="Clear", command=self._clear_console).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(left_toolbar, text="Export Logs", command=self._export_logs).pack(side=tk.LEFT, padx=(0, 10))
        self.auto_scroll_var = tk.BooleanVar(value=self.logger.auto_scroll)
        ttk.Checkbutton(right_toolbar, text="Auto Scroll", variable=self.auto_scroll_var, command=self._toggle_auto_scroll).pack(side=tk.RIGHT, padx=(10, 0))
        self.always_on_top_var = tk.BooleanVar(value=self.logger.always_on_top)
        ttk.Checkbutton(right_toolbar, text="Always On Top", variable=self.always_on_top_var, command=self._toggle_always_on_top).pack(side=tk.RIGHT, padx=(10, 0))

    def _create_options_frame(self):
        options_frame = ttk.LabelFrame(self.window, text="Options", padding="5")
        options_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        left_options = ttk.Frame(options_frame)
        left_options.pack(side=tk.LEFT, fill=tk.X, expand=True)
        right_options = ttk.Frame(options_frame)
        right_options.pack(side=tk.RIGHT)
        
        self.logging_enabled_var = tk.BooleanVar(value=self.logger.logging_enabled)
        ttk.Checkbutton(left_options, text="Enable Logging", variable=self.logging_enabled_var, command=self._toggle_logging).pack(side=tk.LEFT, padx=(0, 15))
        self.console_capture_var = tk.BooleanVar(value=self.logger.capture_console_output)
        ttk.Checkbutton(left_options, text="Capture Console", variable=self.console_capture_var, command=self._toggle_console_capture).pack(side=tk.LEFT, padx=(0, 15))
        self.save_to_file_var = tk.BooleanVar(value=self.logger.save_to_file)
        ttk.Checkbutton(left_options, text="Save to File", variable=self.save_to_file_var, command=self._toggle_save_to_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(left_options, text="Choose File", command=self._choose_log_file).pack(side=tk.LEFT, padx=(0, 15))
        self.redirect_to_console_var = tk.BooleanVar(value=self.logger.redirect_to_console)
        ttk.Checkbutton(left_options, text="Redirect to Console", variable=self.redirect_to_console_var, command=self._toggle_redirect_to_console).pack(side=tk.LEFT)
        
        ttk.Label(right_options, text="Max Lines:").pack(side=tk.LEFT, padx=(10, 5))
        self.max_lines_var = tk.StringVar(value=str(self.logger.max_lines))
        self.max_lines_entry = ttk.Entry(right_options, textvariable=self.max_lines_var, width=8)
        self.max_lines_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.max_lines_entry.bind('<Return>', self._update_max_lines)
        self.max_lines_entry.bind('<FocusOut>', self._update_max_lines)

    def _create_search_frame(self):
        search_frame = ttk.LabelFrame(self.window, text="Search", padding="5")
        search_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        ttk.Label(search_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind('<KeyRelease>', self._on_search_change)
        
        ttk.Button(search_frame, text="Clear Filter", command=self._clear_search).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_case_var = tk.BooleanVar()
        ttk.Checkbutton(search_frame, text="Case Sensitive", variable=self.search_case_var, command=self._on_search_change).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_results_label = ttk.Label(search_frame, text="")
        self.search_results_label.pack(side=tk.RIGHT)

    def _setup_text_widget(self):
        text_frame = ttk.Frame(self.window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.console_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Consolas", 9), bg="white", state="disabled", selectbackground="#0078d4", selectforeground="white")
        self.console_text.pack(fill=tk.BOTH, expand=True)

    def _setup_context_menu(self):
        menu_items = [
            ("Copy", self._copy_selection, "Ctrl+C"),
            ("Select All", self._select_all, "Ctrl+A"),
            "separator",
            ("Find", self._focus_search, "Ctrl+F"),
            ("Clear Filter", self._clear_search, None),
            "separator",
            ("Clear", self._clear_console, "Ctrl+L"),
            ("Export Logs", self._export_logs, "Ctrl+S"),
            "separator",
            ("checkbutton", "Auto Scroll", self.auto_scroll_var, self._toggle_auto_scroll)
        ]
        
        self.context_menu = tk.Menu(self.window, tearoff=0)
        for item in menu_items:
            if item == "separator":
                self.context_menu.add_separator()
            elif item[0] == "checkbutton":
                self.context_menu.add_checkbutton(label=item[1], variable=item[2], command=item[3])
            else:
                label, command, accelerator = item
                kwargs = {"label": label, "command": command}
                if accelerator:
                    kwargs["accelerator"] = accelerator
                self.context_menu.add_command(**kwargs)
        
        def show_context_menu(event):
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            except:
                pass
            finally:
                self.context_menu.grab_release()
        
        self.console_text.bind("<Button-3>", show_context_menu)

    def _setup_keyboard_shortcuts(self):
        shortcuts = [
            ("<Control-c>", self._copy_selection),
            ("<Control-a>", self._select_all),
            ("<Control-l>", self._clear_console),
            ("<Control-s>", self._export_logs),
            ("<F5>", lambda: (self.auto_scroll_var.set(not self.auto_scroll_var.get()), self._toggle_auto_scroll())[1]),
            ("<Control-f>", self._focus_search)
        ]
        
        for key, command in shortcuts:
            self.window.bind(key, lambda event, cmd=command: (cmd(), "break")[1])

    def _configure_tags(self):
        for level in self.logger.log_levels:
            level_info = self.logger.log_levels[level]
            self.console_text.tag_config(f"level_{level.name}", foreground=level_info["color"])
            
        self.console_text.tag_config("search_highlight", background="#FFFF00", foreground="#000000")

    def _populate_console_with_history(self):
        self.logger._populate_console_with_history_progressive()

    def _clear_console(self):
        self.logger._clear_console()

    def _export_logs(self):
        self.logger._export_logs()

    def _toggle_auto_scroll(self):
        self.logger._toggle_auto_scroll()

    def _toggle_always_on_top(self):
        self.logger.always_on_top = self.always_on_top_var.get()
        if self.window:
            self.window.attributes("-topmost", self.logger.always_on_top)

    def _toggle_logging(self):
        self.logger.set_logging_enabled(self.logging_enabled_var.get())

    def _toggle_console_capture(self):
        if self.console_capture_var.get():
            self.logger.enable_console_capture()
        else:
            self.logger.disable_console_capture()

    def _toggle_save_to_file(self):
        self.logger.save_to_file = self.save_to_file_var.get()
        if self.logger.save_to_file and not self.logger.log_file:
            self._choose_log_file()

    def _toggle_redirect_to_console(self):
        self.logger.redirect_to_console = self.redirect_to_console_var.get()

    def _choose_log_file(self):
        if self.window:
            filename = filedialog.asksaveasfilename(parent=self.window, title="Choose Log File", defaultextension=".log", filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")])
            if filename:
                self.logger.log_file = filename
                self.logger.save_to_file = True
                if hasattr(self, "save_to_file_var"):
                    self.save_to_file_var.set(True)

    def _update_max_lines(self, event=None):
        try:
            new_max = int(self.max_lines_var.get())
            if new_max > 0:
                self.logger.max_lines = new_max
        except ValueError:
            self.max_lines_var.set(str(self.logger.max_lines))

    def _on_search_change(self, event=None):
        search_term = self.search_var.get().strip()
        if self.search_operations:
            self.search_operations.perform_search_operation(search_term if search_term else None, clear_only=not search_term)

    def _clear_search(self):
        self.search_var.set("")
        if self.search_operations:
            self.search_operations.perform_search_operation(clear_only=True)

    def _copy_selection(self):
        try:
            if self.console_text and self.console_text.tag_ranges(tk.SEL):
                selected_text = self.console_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.window.clipboard_clear()
                self.window.clipboard_append(selected_text)
                self.window.update()
        except tk.TclError:
            pass

    def _select_all(self):
        try:
            if self.console_text:
                self.console_text.tag_add(tk.SEL, "1.0", tk.END)
                self.console_text.mark_set(tk.INSERT, "1.0")
                self.console_text.see(tk.INSERT)
        except tk.TclError:
            pass

    def _focus_search(self):
        try:
            if hasattr(self, 'search_entry') and self.search_entry:
                self.search_entry.focus_set()
        except:
            pass

    def _on_window_close(self):
        self.logger._flush_file_buffer()
        if self.window and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
        self.console_text = None
        self.logger.console_window = None
        self.logger.console_text = None

    def destroy(self):
        if self.window:
            self.window.destroy()
        self.window = None
        self.console_text = None
