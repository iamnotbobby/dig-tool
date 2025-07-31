import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from utils.debug_logger import logger


class UIComponents:
    def __init__(self, main_window):
        self.main_window = main_window
    
    def create_ui(self):
        style = ttk.Style()
        style.configure("Heading.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 12, "bold"))

        main_frame = ttk.Frame(self.main_window.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        title_label = ttk.Label(header_frame, text="Custom Movement Patterns", style="Heading.TLabel")
        title_label.pack(side=tk.LEFT)

        self.main_window.always_on_top_var = tk.BooleanVar(value=False)
        always_on_top_checkbox = ttk.Checkbutton(header_frame, text="Always on Top", 
                                                variable=self.main_window.always_on_top_var,
                                                command=self.main_window._toggle_always_on_top)
        always_on_top_checkbox.pack(side=tk.RIGHT)

        self.main_window.notebook = ttk.Notebook(main_frame)
        self.main_window.notebook.pack(fill=tk.BOTH, expand=True)

        self._create_patterns_tab()
        self._create_recording_tab()
        
        self.main_window.window.bind('<Control-1>', lambda e: self.main_window.notebook.select(0))
        self.main_window.window.bind('<Control-2>', lambda e: self.main_window.notebook.select(1))

    def _create_patterns_tab(self):
        patterns_frame = ttk.Frame(self.main_window.notebook)
        self.main_window.notebook.add(patterns_frame, text="Available Patterns")

        content_frame = ttk.Frame(patterns_frame, padding="15")
        content_frame.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        open_folder_button = ttk.Button(button_frame, text="Open Auto Walk Folder", 
                                       command=self._open_auto_walk_folder)
        open_folder_button.pack(side=tk.LEFT)

        paned_window = ttk.PanedWindow(content_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        left_pane = ttk.Frame(paned_window)
        paned_window.add(left_pane, weight=1)

        right_pane = ttk.Frame(paned_window)
        paned_window.add(right_pane, weight=1)

        self._create_pattern_list(left_pane)
        self._create_preview_section(right_pane)

    def _open_auto_walk_folder(self):
        try:
            import subprocess
            auto_walk_dir = self.main_window.automation_manager.dig_tool.settings_manager.get_auto_walk_directory()
            subprocess.run(['explorer', os.path.abspath(auto_walk_dir)], check=False)
            logger.info(f"Opened Auto Walk folder: {auto_walk_dir}")
        except Exception as e:
            logger.error(f"Error opening Auto Walk folder: {e}")
            messagebox.showerror("Error", f"Could not open Auto Walk folder: {e}")

    def _create_recording_tab(self):
        recording_frame = ttk.Frame(self.main_window.notebook)
        self.main_window.notebook.add(recording_frame, text="Record New Pattern")

        content_frame = ttk.Frame(recording_frame, padding="15")
        content_frame.pack(fill=tk.BOTH, expand=True)

        self._create_recording_section(content_frame)

    def _create_pattern_list(self, parent):
        list_container = ttk.Frame(parent, padding="10")
        list_container.pack(fill=tk.BOTH, expand=True)

        listbox_container = ttk.Frame(list_container)
        listbox_container.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        self.main_window.pattern_listbox = tk.Listbox(listbox_container, selectmode=tk.SINGLE,
                                          font=("Segoe UI", 11), activestyle='none')
        self.main_window.pattern_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.main_window.pattern_listbox.bind('<<ListboxSelect>>', self.main_window._on_pattern_select)
        self.main_window.pattern_listbox.bind('<Button-3>', self.main_window._show_context_menu)

        scrollbar = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL,
                                  command=self.main_window.pattern_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.main_window.pattern_listbox.configure(yscrollcommand=scrollbar.set)

        buttons_frame = ttk.Frame(list_container)
        buttons_frame.pack(fill=tk.X)
        
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

        self.main_window.preview_button = ttk.Button(buttons_frame, text="Preview Pattern",
                                        command=self.main_window._safe_preview_pattern)
        self.main_window.preview_button.grid(row=0, column=0, padx=(0, 5), pady=(0, 5), sticky="ew")
        
        self.main_window.stop_preview_button = ttk.Button(buttons_frame, text="Stop Preview",
                                             command=self.main_window._stop_preview, state=tk.DISABLED)
        self.main_window.stop_preview_button.grid(row=0, column=1, padx=(5, 0), pady=(0, 5), sticky="ew")
        
        ttk.Button(buttons_frame, text="Import Patterns",
                   command=self.main_window._safe_import_patterns).grid(row=1, column=0, padx=(0, 5), pady=(0, 5), sticky="ew")
        ttk.Button(buttons_frame, text="Delete Selected",
                   command=self.main_window._safe_delete_pattern).grid(row=1, column=1, padx=(5, 0), pady=(0, 5), sticky="ew")
        
        self.main_window.add_manual_key_button = ttk.Button(buttons_frame, text="+ Add Manual Key",
                                               command=self.main_window._safe_add_manual_key, state=tk.DISABLED)
        self.main_window.add_manual_key_button.grid(row=2, column=0, columnspan=2, padx=0, pady=(0, 0), sticky="ew")

    def _create_preview_section(self, parent):
        preview_container = ttk.Frame(parent, padding="10")
        preview_container.pack(fill=tk.BOTH, expand=True)

        self.main_window.pattern_info_frame = ttk.Frame(preview_container)
        self.main_window.pattern_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.main_window.pattern_info_label = tk.Label(self.main_window.pattern_info_frame, 
                                         text="Select a pattern to view details", 
                                         font=("Segoe UI", 11, "bold"),
                                         fg="gray")
        self.main_window.pattern_info_label.pack(anchor="w")

        preview_display_frame = ttk.Frame(preview_container)
        preview_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        self.main_window.preview_canvas = tk.Canvas(preview_display_frame, bg="white", highlightthickness=0)
        self.main_window.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        preview_scrollbar = ttk.Scrollbar(preview_display_frame, orient=tk.VERTICAL,
                                        command=self.main_window.preview_canvas.yview)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.main_window.preview_canvas.configure(yscrollcommand=preview_scrollbar.set)

        self.main_window.preview_pattern_frame = tk.Frame(self.main_window.preview_canvas, bg="#f8f9fa")
        self.main_window.preview_canvas_window = self.main_window.preview_canvas.create_window(0, 0, anchor="nw", window=self.main_window.preview_pattern_frame)

        self.main_window.preview_pattern_frame.bind('<Configure>', self.main_window.pattern_display._on_preview_canvas_resize)
        self.main_window.preview_canvas.bind('<Configure>', self.main_window.pattern_display._on_preview_canvas_resize)
        
        self.main_window.preview_empty_label = tk.Label(self.main_window.preview_pattern_frame, 
                                          text="Select a pattern to see preview", 
                                          font=("Segoe UI", 10, "italic"),
                                          fg="gray")
        self.main_window.preview_empty_label.pack(pady=50)

    def _create_recording_section(self, parent):
        controls_frame = ttk.LabelFrame(parent, text="Recording Controls", padding="15")
        controls_frame.pack(fill=tk.X, pady=(0, 15))

        controls_button_frame = ttk.Frame(controls_frame)
        controls_button_frame.pack(fill=tk.X, pady=(0, 10))

        self.main_window.record_button = ttk.Button(controls_button_frame, text="● Start",
                                        command=self.main_window._safe_toggle_recording)
        self.main_window.record_button.pack(side=tk.LEFT, padx=(0, 20), ipadx=15)

        self.main_window.clear_button = ttk.Button(controls_button_frame, text="✕ Clear",
                                       command=self.main_window._clear_pattern, state=tk.DISABLED)
        self.main_window.clear_button.pack(side=tk.LEFT, padx=(0, 20), ipadx=15)

        self.main_window.record_status = ttk.Label(controls_button_frame, text="Ready to record",
                                       font=("Segoe UI", 10))
        self.main_window.record_status.pack(side=tk.LEFT)

        custom_keys_frame = ttk.Frame(controls_frame)
        custom_keys_frame.pack(fill=tk.X, pady=(10, 0))

        self.main_window.custom_keys_var = tk.BooleanVar(value=False)
        self.main_window.custom_keys_checkbox = ttk.Checkbutton(custom_keys_frame, 
                                                   text="Allow custom keys (beyond WASD)",
                                                   variable=self.main_window.custom_keys_var,
                                                   command=self.main_window._on_custom_keys_changed)
        self.main_window.custom_keys_checkbox.pack(side=tk.LEFT, padx=(0, 15))

        pattern_display_frame = ttk.LabelFrame(parent, text="Recorded Pattern", padding="15")
        pattern_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        pattern_outer_frame = tk.Frame(pattern_display_frame, bg="#ffffff", relief="solid", borderwidth=1)
        pattern_outer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        pattern_container = tk.Frame(pattern_outer_frame, bg="#ffffff")
        pattern_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.main_window.recorded_pattern_canvas = tk.Canvas(pattern_container, height=120, 
                                               bg="#f8f9fa", relief="flat", borderwidth=0,
                                               highlightthickness=0)
        
        self.main_window.recorded_scrollbar_h = ttk.Scrollbar(pattern_container, orient="horizontal", 
                                                command=self.main_window.recorded_pattern_canvas.xview)
        self.main_window.recorded_scrollbar_v = ttk.Scrollbar(pattern_container, orient="vertical", 
                                                command=self.main_window.recorded_pattern_canvas.yview)
        
        self.main_window.recorded_pattern_canvas.configure(xscrollcommand=self.main_window.recorded_scrollbar_h.set,
                                             yscrollcommand=self.main_window.recorded_scrollbar_v.set)

        self.main_window.recorded_pattern_frame = tk.Frame(self.main_window.recorded_pattern_canvas, bg="#f8f9fa")
        self.main_window.recorded_canvas_window = self.main_window.recorded_pattern_canvas.create_window((0, 0), 
                                                                               window=self.main_window.recorded_pattern_frame, 
                                                                               anchor="nw")

        self.main_window.recorded_pattern_canvas.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_window.recorded_scrollbar_h.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self.main_window.recorded_scrollbar_v.grid(row=0, column=1, sticky="ns", padx=(2, 0))
        pattern_container.grid_rowconfigure(0, weight=1)
        pattern_container.grid_columnconfigure(0, weight=1)

        self.main_window.recorded_pattern_canvas.bind('<Configure>', self.main_window.pattern_display._on_recorded_canvas_resize)
        
        def on_mouse_wheel(event):
            if event.delta > 0:
                self.main_window.recorded_pattern_canvas.yview_scroll(-1, "units")
            else:
                self.main_window.recorded_pattern_canvas.yview_scroll(1, "units")
        
        self.main_window.recorded_pattern_canvas.bind("<MouseWheel>", on_mouse_wheel)
        self.main_window.recorded_pattern_frame.bind("<MouseWheel>", on_mouse_wheel)

        self.main_window._previous_pattern_length = 0
        self.main_window._last_displayed_length = 0
        self.main_window._current_pattern = []
        self.main_window._current_pattern_name = None
        self.main_window._current_pattern_type = None
        self.main_window._has_unsaved_changes = False
        self.main_window.pattern_display._show_empty_pattern_state()

        save_frame = ttk.LabelFrame(parent, text="Save Recorded Pattern", padding="15")
        save_frame.pack(fill=tk.X, pady=(0, 0))

        save_container = ttk.Frame(save_frame)
        save_container.pack(fill=tk.X)

        name_label = ttk.Label(save_container, text="Pattern Name:")
        name_label.pack(side=tk.LEFT, padx=(0, 10))

        self.main_window.recorded_name_entry = ttk.Entry(save_container, width=25, font=("Segoe UI", 10))
        self.main_window.recorded_name_entry.pack(side=tk.LEFT, padx=(0, 15))

        self.main_window.save_recorded_button = ttk.Button(save_container, text="Save Pattern",
                                              command=self.main_window._safe_save_pattern, state=tk.DISABLED)
        self.main_window.save_recorded_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.main_window.unsaved_changes_label = ttk.Label(save_container, text="", font=("Segoe UI", 9), foreground="orange")
        self.main_window.unsaved_changes_label.pack(side=tk.LEFT, padx=(10, 0))
        self.main_window.save_recorded_button.pack(side=tk.LEFT, padx=(0, 10))
        
        preview_container = ttk.Frame(save_container)
        preview_container.pack(side=tk.LEFT)
        
        self.main_window.preview_recorded_button = ttk.Button(preview_container, text="Preview Pattern",
                                                 command=self.main_window._safe_preview_recorded_pattern, state=tk.DISABLED)
        self.main_window.preview_recorded_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.main_window.stop_recorded_preview_button = ttk.Button(preview_container, text="Stop Preview",
                                                      command=self.main_window._stop_preview, state=tk.DISABLED)
        self.main_window.stop_recorded_preview_button.pack(side=tk.LEFT)
