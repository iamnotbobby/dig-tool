import tkinter as tk
from tkinter import ttk, scrolledtext


class UIComponents:
    def __init__(self, main_window):
        self.main_window = main_window

    def _setup_ui(self):
        main_frame = ttk.Frame(self.main_window.window, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        self._create_progress_section(main_frame)
        self._create_text_section(main_frame)
        self._create_button_section(main_frame)

    def _create_progress_section(self, parent):
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding="10")
        progress_frame.pack(fill="x", pady=(0, 10))
        self.main_window.progress_var = tk.DoubleVar()
        self.main_window.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.main_window.progress_var, maximum=100, length=400
        )
        self.main_window.progress_bar.pack(fill="x")

    def _create_text_section(self, parent):
        text_frame = ttk.LabelFrame(parent, text="Operation Details", padding="10")
        text_frame.pack(fill="both", expand=True, pady=(0, 15))
        text_container = ttk.Frame(text_frame)
        text_container.pack(fill="both", expand=True)
        self.main_window.text_area = scrolledtext.ScrolledText(
            text_container, wrap=tk.WORD, font=("Consolas", 9), height=20
        )
        self.main_window.text_area.pack(fill="both", expand=True)

    def _create_button_section(self, parent):
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=(0, 10))
        self.main_window.close_button = ttk.Button(
            button_frame, text="Close", command=self.main_window.close_window, state="disabled"
        )
        self.main_window.close_button.pack(side="right")

    def _configure_tags(self):
        if not self.main_window.text_area:
            return
        tag_configs = {
            "success": {"foreground": "#006400", "font": ("Consolas", 9, "bold")},
            "warning": {"foreground": "#FF8C00", "font": ("Consolas", 9)},
            "error": {"foreground": "#DC143C", "font": ("Consolas", 9, "bold")},
            "info": {"foreground": "#4169E1", "font": ("Consolas", 9)},
            "header": {"foreground": "#000000", "font": ("Consolas", 10, "bold")},
            "unchanged": {"foreground": "#666666", "font": ("Consolas", 9)},
        }
        for tag, config in tag_configs.items():
            self.main_window.text_area.tag_configure(tag, **config)
