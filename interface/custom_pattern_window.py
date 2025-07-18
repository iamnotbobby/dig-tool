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
        style = ttk.Style()
        style.configure("Heading.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 12, "bold"))

        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        title_label = ttk.Label(header_frame, text="Custom Movement Patterns", style="Heading.TLabel")
        title_label.pack(side=tk.LEFT)

        self.always_on_top_var = tk.BooleanVar(value=False)
        always_on_top_checkbox = ttk.Checkbutton(header_frame, text="Always on Top", 
                                                variable=self.always_on_top_var,
                                                command=self._toggle_always_on_top)
        always_on_top_checkbox.pack(side=tk.RIGHT)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._create_patterns_tab()
        self._create_recording_tab()
        
        self.window.bind('<Control-1>', lambda e: self.notebook.select(0))
        self.window.bind('<Control-2>', lambda e: self.notebook.select(1))

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

    def _create_patterns_tab(self):
        patterns_frame = ttk.Frame(self.notebook)
        self.notebook.add(patterns_frame, text="Available Patterns")

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
            auto_walk_dir = self.automation_manager.dig_tool.settings_manager.get_auto_walk_directory()
            subprocess.run(['explorer', os.path.abspath(auto_walk_dir)], check=False)
            logger.info(f"Opened Auto Walk folder: {auto_walk_dir}")
        except Exception as e:
            logger.error(f"Error opening Auto Walk folder: {e}")
            messagebox.showerror("Error", f"Could not open Auto Walk folder: {e}")

    def _get_auto_walk_patterns_info(self):
        try:
            auto_walk_dir = self.automation_manager.dig_tool.settings_manager.get_auto_walk_directory()
            patterns_file = os.path.join(auto_walk_dir, "custom_patterns.json")
            
            if os.path.exists(patterns_file):
                with open(patterns_file, 'r') as f:
                    patterns = json.load(f)
                return {
                    'file_exists': True,
                    'file_path': patterns_file,
                    'pattern_count': len(patterns),
                    'patterns': patterns
                }
            else:
                return {
                    'file_exists': False,
                    'file_path': patterns_file,
                    'pattern_count': 0,
                    'patterns': {}
                }
        except Exception as e:
            logger.error(f"Error reading Auto Walk patterns: {e}")
            return {
                'file_exists': False,
                'file_path': 'Error',
                'pattern_count': 0,
                'patterns': {},
                'error': str(e)
            }

    def _create_recording_tab(self):
        recording_frame = ttk.Frame(self.notebook)
        self.notebook.add(recording_frame, text="Record New Pattern")

        content_frame = ttk.Frame(recording_frame, padding="15")
        content_frame.pack(fill=tk.BOTH, expand=True)

        self._create_recording_section(content_frame)

    def _create_pattern_list(self, parent):
        list_container = ttk.Frame(parent, padding="10")
        list_container.pack(fill=tk.BOTH, expand=True)

        listbox_container = ttk.Frame(list_container)
        listbox_container.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        self.pattern_listbox = tk.Listbox(listbox_container, selectmode=tk.SINGLE,
                                          font=("Segoe UI", 11), activestyle='none')
        self.pattern_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.pattern_listbox.bind('<<ListboxSelect>>', self._on_pattern_select)
        self.pattern_listbox.bind('<Button-3>', self._show_context_menu)

        scrollbar = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL,
                                  command=self.pattern_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pattern_listbox.configure(yscrollcommand=scrollbar.set)

        buttons_frame = ttk.Frame(list_container)
        buttons_frame.pack(fill=tk.X)
        
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

        self.preview_button = ttk.Button(buttons_frame, text="Preview Pattern",
                                        command=self._safe_preview_pattern)
        self.preview_button.grid(row=0, column=0, padx=(0, 5), pady=(0, 5), sticky="ew")
        
        self.stop_preview_button = ttk.Button(buttons_frame, text="Stop Preview",
                                             command=self._stop_preview, state=tk.DISABLED)
        self.stop_preview_button.grid(row=0, column=1, padx=(5, 0), pady=(0, 5), sticky="ew")
        
        ttk.Button(buttons_frame, text="Import Patterns",
                   command=self._safe_import_patterns).grid(row=1, column=0, padx=(0, 5), pady=(0, 5), sticky="ew")
        ttk.Button(buttons_frame, text="Delete Selected",
                   command=self._safe_delete_pattern).grid(row=1, column=1, padx=(5, 0), pady=(0, 5), sticky="ew")
        
        self.add_manual_key_button = ttk.Button(buttons_frame, text="+ Add Manual Key",
                                               command=self._safe_add_manual_key, state=tk.DISABLED)
        self.add_manual_key_button.grid(row=2, column=0, columnspan=2, padx=0, pady=(0, 0), sticky="ew")

    def _create_preview_section(self, parent):
        preview_container = ttk.Frame(parent, padding="10")
        preview_container.pack(fill=tk.BOTH, expand=True)

        self.pattern_info_frame = ttk.Frame(preview_container)
        self.pattern_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.pattern_info_label = tk.Label(self.pattern_info_frame, 
                                         text="Select a pattern to view details", 
                                         font=("Segoe UI", 11, "bold"),
                                         fg="gray")
        self.pattern_info_label.pack(anchor="w")

        preview_display_frame = ttk.Frame(preview_container)
        preview_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        self.preview_canvas = tk.Canvas(preview_display_frame, bg="white", highlightthickness=0)
        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        preview_scrollbar = ttk.Scrollbar(preview_display_frame, orient=tk.VERTICAL,
                                        command=self.preview_canvas.yview)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_canvas.configure(yscrollcommand=preview_scrollbar.set)

        self.preview_pattern_frame = tk.Frame(self.preview_canvas, bg="#f8f9fa")
        self.preview_canvas_window = self.preview_canvas.create_window(0, 0, anchor="nw", window=self.preview_pattern_frame)

        self.preview_pattern_frame.bind('<Configure>', self._on_preview_canvas_resize)
        self.preview_canvas.bind('<Configure>', self._on_preview_canvas_resize)
        
        self.preview_empty_label = tk.Label(self.preview_pattern_frame, 
                                          text="Select a pattern to see preview", 
                                          font=("Segoe UI", 10, "italic"),
                                          fg="gray")
        self.preview_empty_label.pack(pady=50)

    def _create_recording_section(self, parent):
        controls_frame = ttk.LabelFrame(parent, text="Recording Controls", padding="15")
        controls_frame.pack(fill=tk.X, pady=(0, 15))

        controls_button_frame = ttk.Frame(controls_frame)
        controls_button_frame.pack(fill=tk.X, pady=(0, 10))

        self.record_button = ttk.Button(controls_button_frame, text="● Start",
                                        command=self._safe_toggle_recording)
        self.record_button.pack(side=tk.LEFT, padx=(0, 20), ipadx=15)

        self.clear_button = ttk.Button(controls_button_frame, text="✕ Clear",
                                       command=self._clear_pattern, state=tk.DISABLED)
        self.clear_button.pack(side=tk.LEFT, padx=(0, 20), ipadx=15)

        self.record_status = ttk.Label(controls_button_frame, text="Ready to record",
                                       font=("Segoe UI", 10))
        self.record_status.pack(side=tk.LEFT)

        custom_keys_frame = ttk.Frame(controls_frame)
        custom_keys_frame.pack(fill=tk.X, pady=(10, 0))

        self.custom_keys_var = tk.BooleanVar(value=False)
        self.custom_keys_checkbox = ttk.Checkbutton(custom_keys_frame, 
                                                   text="Allow custom keys (beyond WASD)",
                                                   variable=self.custom_keys_var,
                                                   command=self._on_custom_keys_changed)
        self.custom_keys_checkbox.pack(side=tk.LEFT, padx=(0, 15))

        pattern_display_frame = ttk.LabelFrame(parent, text="Recorded Pattern", padding="15")
        pattern_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        pattern_outer_frame = tk.Frame(pattern_display_frame, bg="#ffffff", relief="solid", borderwidth=1)
        pattern_outer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        pattern_container = tk.Frame(pattern_outer_frame, bg="#ffffff")
        pattern_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.recorded_pattern_canvas = tk.Canvas(pattern_container, height=120, 
                                               bg="#f8f9fa", relief="flat", borderwidth=0,
                                               highlightthickness=0)
        
        self.recorded_scrollbar_h = ttk.Scrollbar(pattern_container, orient="horizontal", 
                                                command=self.recorded_pattern_canvas.xview)
        self.recorded_scrollbar_v = ttk.Scrollbar(pattern_container, orient="vertical", 
                                                command=self.recorded_pattern_canvas.yview)
        
        self.recorded_pattern_canvas.configure(xscrollcommand=self.recorded_scrollbar_h.set,
                                             yscrollcommand=self.recorded_scrollbar_v.set)

        self.recorded_pattern_frame = tk.Frame(self.recorded_pattern_canvas, bg="#f8f9fa")
        self.recorded_canvas_window = self.recorded_pattern_canvas.create_window((0, 0), 
                                                                               window=self.recorded_pattern_frame, 
                                                                               anchor="nw")

        self.recorded_pattern_canvas.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.recorded_scrollbar_h.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self.recorded_scrollbar_v.grid(row=0, column=1, sticky="ns", padx=(2, 0))
        pattern_container.grid_rowconfigure(0, weight=1)
        pattern_container.grid_columnconfigure(0, weight=1)

        self.recorded_pattern_canvas.bind('<Configure>', self._on_recorded_canvas_resize)
        
        def on_mouse_wheel(event):
            if event.delta > 0:
                self.recorded_pattern_canvas.yview_scroll(-1, "units")
            else:
                self.recorded_pattern_canvas.yview_scroll(1, "units")
        
        self.recorded_pattern_canvas.bind("<MouseWheel>", on_mouse_wheel)
        self.recorded_pattern_frame.bind("<MouseWheel>", on_mouse_wheel)

        self._previous_pattern_length = 0
        self._last_displayed_length = 0
        self._current_pattern = []
        self._current_pattern_name = None
        self._current_pattern_type = None
        self._has_unsaved_changes = False
        self._show_empty_pattern_state()

        save_frame = ttk.LabelFrame(parent, text="Save Recorded Pattern", padding="15")
        save_frame.pack(fill=tk.X, pady=(0, 0))

        save_container = ttk.Frame(save_frame)
        save_container.pack(fill=tk.X)

        name_label = ttk.Label(save_container, text="Pattern Name:")
        name_label.pack(side=tk.LEFT, padx=(0, 10))

        self.recorded_name_entry = ttk.Entry(save_container, width=25, font=("Segoe UI", 10))
        self.recorded_name_entry.pack(side=tk.LEFT, padx=(0, 15))

        self.save_recorded_button = ttk.Button(save_container, text="Save Pattern",
                                              command=self._safe_save_pattern, state=tk.DISABLED)
        self.save_recorded_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.unsaved_changes_label = ttk.Label(save_container, text="", font=("Segoe UI", 9), foreground="orange")
        self.unsaved_changes_label.pack(side=tk.LEFT, padx=(10, 0))
        self.save_recorded_button.pack(side=tk.LEFT, padx=(0, 10))
        
        preview_container = ttk.Frame(save_container)
        preview_container.pack(side=tk.LEFT)
        
        self.preview_recorded_button = ttk.Button(preview_container, text="Preview Pattern",
                                                 command=self._safe_preview_recorded_pattern, state=tk.DISABLED)
        self.preview_recorded_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_recorded_preview_button = ttk.Button(preview_container, text="Stop Preview",
                                                      command=self._stop_preview, state=tk.DISABLED)
        self.stop_recorded_preview_button.pack(side=tk.LEFT)

    def _on_recorded_canvas_resize(self, event):
        if event.widget == self.recorded_pattern_canvas:
            canvas_width = self.recorded_pattern_canvas.winfo_width()
            if canvas_width > 1:
                self.recorded_pattern_canvas.itemconfig(self.recorded_canvas_window, width=canvas_width)

    def _on_preview_canvas_resize(self, event):
        if event.widget == self.preview_canvas:
            canvas_width = self.preview_canvas.winfo_width()
            if canvas_width > 1:
                self.preview_canvas.itemconfig(self.preview_canvas_window, width=canvas_width)
        elif event.widget == self.preview_pattern_frame:
            self._update_preview_canvas_scroll_region()

    def _update_preview_canvas_scroll_region(self):
        try:
            self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
        except Exception:
            pass

    def _show_preview_pattern_blocks(self, pattern, force_refresh=False):
        try:
            for widget in self.preview_pattern_frame.winfo_children():
                widget.destroy()
            
            if not pattern:
                self.preview_empty_label = tk.Label(self.preview_pattern_frame, 
                                                  text="No pattern data available", 
                                                  font=("Segoe UI", 10, "italic"),
                                                  fg="gray", bg="#f8f9fa")
                self.preview_empty_label.pack(pady=50)
                self._update_preview_canvas_scroll_region()
                return
            
            self.preview_pattern_frame.update_idletasks()
            frame_width = self.preview_pattern_frame.winfo_width()
            if frame_width < 100:
                frame_width = 600
            
            blocks_per_row = 6
            for i, step in enumerate(pattern):
                row = i // blocks_per_row
                col = i % blocks_per_row
                block = self._create_pattern_block(step, i, self.preview_pattern_frame, animate=False, preview=True, pattern_type=getattr(self, '_current_pattern_type', 'custom'))
                if block:
                    block.grid(row=row, column=col, padx=5, pady=8, sticky="nsew")
            
            for c in range(blocks_per_row):
                self.preview_pattern_frame.grid_columnconfigure(c, weight=1, minsize=60)
            for r in range((len(pattern) + blocks_per_row - 1) // blocks_per_row):
                self.preview_pattern_frame.grid_rowconfigure(r, weight=0, minsize=60)
            
            self._update_preview_canvas_scroll_region()
            
            if force_refresh:
                self.preview_pattern_frame.update()
                self.preview_pattern_canvas.update()
            
        except Exception as e:
            for widget in self.preview_pattern_frame.winfo_children():
                widget.destroy()
            error_label = tk.Label(self.preview_pattern_frame, 
                                 text=f"Error displaying pattern: {str(e)}", 
                                 font=("Segoe UI", 10, "italic"),
                                 fg="red", bg="#f8f9fa")
            error_label.pack(pady=50)
            self._update_preview_canvas_scroll_region()

    def _create_pattern_block(self, step, index, parent, animate=False, preview=False, pattern_type='custom'):
        if isinstance(step, dict):
            key = step.get('key', '')
            duration = step.get('duration', None)
            click_enabled = step.get('click', True)
        else:
            key = str(step)
            duration = None
            click_enabled = True

        formatted_step = format_step_text(key)
        step_number = f"#{index+1}"
        is_combination = '+' in key
        text_length = len(formatted_step)

        if preview:
            if is_combination:
                step_width = max(95, text_length * 8 + 25)
            elif text_length > 4:
                step_width = max(85, text_length * 9 + 20)
            elif text_length > 2:
                step_width = 75
            else:
                step_width = 70
            step_height = 80
            main_font = ("Segoe UI", 11, "bold")
            number_font = ("Segoe UI", 7, "bold")
            duration_font = ("Segoe UI", 7)
        else:
            if is_combination:
                step_width = max(95, text_length * 8 + 25)
                main_font = ("Segoe UI", 7, "bold")
                duration_font = ("Segoe UI", 6)
            elif text_length > 4:
                step_width = max(85, text_length * 9 + 20)
                main_font = ("Segoe UI", 8, "bold")
                duration_font = ("Segoe UI", 6)
            elif text_length > 2:
                step_width = 75
                main_font = ("Segoe UI", 9, "bold")
                duration_font = ("Segoe UI", 6)
            else:
                step_width = 70
                main_font = ("Segoe UI", 10, "bold")
                duration_font = ("Segoe UI", 6)
            step_height = 75
            number_font = ("Segoe UI", 7)

        if preview:
            bg, border_color, hover_bg, text_shadow = get_step_colors(key)
        else:
            bg, fg, border_color, hover_bg = get_step_colors(key)

        if preview:
            f = tk.Frame(parent, bg=bg, width=step_width, height=step_height, relief="solid", bd=2, highlightbackground=border_color, highlightthickness=1)
            f.pack_propagate(False)
            inner_frame = tk.Frame(f, bg=bg, highlightbackground=text_shadow, highlightthickness=1, relief="raised", bd=1)
            inner_frame.pack(fill="both", expand=True, padx=1, pady=1)
            number_label = tk.Label(inner_frame, text=step_number, font=number_font, bg=bg, fg="#333333", justify="center")
            number_label.pack(pady=(3, 0))
            key_label = tk.Label(inner_frame, text=formatted_step, font=main_font, bg=bg, fg="#000000", justify="center")
            key_label.pack()
        else:
            f = tk.Frame(parent, width=step_width, height=step_height, bg=bg, relief="solid", borderwidth=1, highlightbackground=border_color, highlightthickness=1)
            f.pack_propagate(False)
            key_label = tk.Label(f, text=formatted_step, font=main_font, bg=bg, fg=fg, justify="center")
            key_label.pack(pady=(5, 0))
            number_label = tk.Label(f, text=step_number, font=number_font, bg=bg, fg=fg, justify="center")
            number_label.pack()

        info_parts = []
        if preview and pattern_type == 'built-in':
            info_text = "(default)"
            info_color = "#777777"
        else:
            if duration is not None:
                info_parts.append(f"{duration}ms")
            else:
                info_parts.append("default")
            if not click_enabled:
                info_parts.append("no-click")
            info_text = " | ".join(info_parts)
            if not click_enabled:
                info_color = "#cc0000"
            elif duration is not None:
                info_color = "#555555"
            else:
                info_color = "#777777" if preview else "#999999"

        if preview:
            info_label = tk.Label(inner_frame, text=info_text, font=duration_font, bg=bg, fg=info_color, justify="center")
            info_label.pack(pady=(0, 2))
        else:
            info_label = tk.Label(f, text=info_text, font=duration_font, bg=bg, fg=info_color, justify="center")
            info_label.pack(pady=(0, 2))

        if preview:
            if pattern_type == 'custom':
                def on_click(e):
                    self._edit_step_dialog(index, step, is_preview=True)
                def on_right_click(e):
                    self._show_preview_step_context_menu(e, index, step)
            else:
                def on_click(e):
                    self._show_pattern_info_dialog(step)
                def on_right_click(e):
                    pass
            def on_enter(e):
                f.config(bg=hover_bg, highlightbackground=text_shadow)
                inner_frame.config(bg=hover_bg)
                for child in inner_frame.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(bg=hover_bg)
            def on_leave(e):
                f.config(bg=bg, highlightbackground=border_color)
                inner_frame.config(bg=bg)
                for child in inner_frame.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(bg=bg)
            f.bind("<Button-1>", on_click)
            f.bind("<Button-3>", on_right_click)
            f.bind("<Enter>", on_enter)
            f.bind("<Leave>", on_leave)
            for child in [inner_frame] + list(inner_frame.winfo_children()):
                child.bind("<Button-1>", on_click)
                child.bind("<Button-3>", on_right_click)
                child.bind("<Enter>", on_enter)
                child.bind("<Leave>", on_leave)
        else:
            def on_click(e):
                current_pattern_name = getattr(self, '_current_pattern_name', None)
                if current_pattern_name:
                    self._pre_edit_pattern_name = current_pattern_name
                    self._pre_edit_pattern = self._current_pattern.copy() if hasattr(self, '_current_pattern') else []
                    self._show_preview_pattern_blocks(self._current_pattern)
                self._edit_step_dialog(index, step)
            def on_right_click(e):
                self._show_step_context_menu(e, index, step)
            def on_enter(e):
                f.config(bg=hover_bg)
                for child in f.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(bg=hover_bg)
            def on_leave(e):
                f.config(bg=bg)
                for child in f.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(bg=bg)
            f.bind("<Button-1>", on_click)
            f.bind("<Button-3>", on_right_click)
            f.bind("<Enter>", on_enter)
            f.bind("<Leave>", on_leave)
            for child in f.winfo_children():
                child.bind("<Button-1>", on_click)
                child.bind("<Button-3>", on_right_click)
                child.bind("<Enter>", on_enter)
                child.bind("<Leave>", on_leave)

        if animate:
            f.config(width=int(step_width * 0.7), height=int(step_height * 0.7))
            self._animate_block_entrance(f, step_width, step_height)
        return f



    def _edit_step_dialog(self, index, current_step, is_preview=False):
        current_pattern_name = getattr(self, '_current_pattern_name', None)
        current_pattern = getattr(self, '_current_pattern', [])
        
        if is_preview and getattr(self, '_current_pattern_type', 'custom') != 'custom':
            return
        
        dialog = tk.Toplevel(self.window)
        dialog.title(f"Edit Step #{index+1}")
        dialog.geometry("450x600")
        dialog.resizable(False, False)
        dialog.transient(self.window)
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (600 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        def restore_display():
            if current_pattern_name and current_pattern:
                self._ensure_pattern_selected(current_pattern_name)
                if is_preview:
                    self._show_preview_pattern_blocks(current_pattern)
                else:
                    self._show_preview_pattern_blocks(current_pattern)
                self.window.update_idletasks()
        
        restore_display()
        
        def delayed_grab():
            try:
                dialog.grab_set()
            except:
                pass
        
        self.window.after(50, delayed_grab)
        
        self.window.after(100, lambda: restore_display() if current_pattern_name and current_pattern else None)
        
        def on_dialog_close():
            self._restore_pattern_selection_and_preview()
            dialog.destroy()
            
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        main_frame = ttk.Frame(dialog, padding="25")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(main_frame, text=f"Editing Step #{index+1}", font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 25))
        
        if isinstance(current_step, dict):
            current_key = current_step.get('key', '')
            current_duration = current_step.get('duration', None)
            current_click_enabled = current_step.get('click', True)
        else:
            current_key = str(current_step)
            current_duration = None
            current_click_enabled = True
        
        key_frame = ttk.LabelFrame(main_frame, text="Key/Combination", padding="15")
        key_frame.pack(fill=tk.X, pady=(0, 20))
        
        key_entry = ttk.Entry(key_frame, font=("Segoe UI", 12))
        key_entry.pack(fill=tk.X, pady=(5, 10))
        key_entry.insert(0, current_key)
        key_entry.focus()
        
        examples_label = ttk.Label(key_frame, text="Examples: w, a+d, shift+w, ctrl+space", 
                                  font=("Segoe UI", 9), foreground="#666666")
        examples_label.pack()
        
        duration_frame = ttk.LabelFrame(main_frame, text="Key Duration (ms)", padding="15")
        duration_frame.pack(fill=tk.X, pady=(0, 20))
        
        duration_entry = ttk.Entry(duration_frame, font=("Segoe UI", 12))
        duration_entry.pack(fill=tk.X, pady=(5, 10))
        if current_duration is not None:
            duration_entry.insert(0, str(current_duration))
        
        duration_help = ttk.Label(duration_frame, text="Leave empty to use default Key Duration setting", 
                                 font=("Segoe UI", 9), foreground="#666666")
        duration_help.pack()
        
        click_frame = ttk.LabelFrame(main_frame, text="Click Behavior", padding="15")
        click_frame.pack(fill=tk.X, pady=(0, 25))
        
        click_enabled_var = tk.BooleanVar(value=current_click_enabled)
        click_checkbox = ttk.Checkbutton(click_frame, text="Enable clicking for this step", 
                                        variable=click_enabled_var, 
                                        onvalue=True, offvalue=False)
        click_checkbox.pack(anchor="w", pady=(5, 10))
        
        click_help = ttk.Label(click_frame, text="When disabled, this step will only move without clicking", 
                              font=("Segoe UI", 9), foreground="#666666")
        click_help.pack(anchor="w")
        
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(15, 10))
        
        def save_changes():
            new_key = key_entry.get().strip().upper()
            duration_text = duration_entry.get().strip()
            
            if not new_key or not validate_step_input(new_key):
                tk.messagebox.showerror("Invalid Input", "Please enter a valid key (W, A, S, D, or combinations like W+A)")
                return
            
            new_duration = None
            if duration_text:
                try:
                    new_duration = int(duration_text)
                    if new_duration <= 0:
                        tk.messagebox.showerror("Invalid Duration", "Duration must be a positive number")
                        return
                except ValueError:
                    tk.messagebox.showerror("Invalid Duration", "Duration must be a number")
                    return
            
            new_step = {'key': new_key, 'duration': new_duration, 'click': click_enabled_var.get()}
            
            if is_preview:
                self._current_pattern[index] = new_step
                success, message = self.automation_manager.save_pattern(self._current_pattern_name, self._current_pattern)
                if success:
                    self._show_preview_pattern_blocks(self._current_pattern)
                    safe_schedule_ui_update(self.window, lambda: self._ensure_pattern_selected(self._current_pattern_name), 10)
                    dialog.destroy()
                else:
                    tk.messagebox.showerror("Error", f"Failed to save pattern: {message}")
            else:
                self._update_step_with_selection_restore(index, new_step)
                dialog.destroy()
        
        def delete_step():
            if is_preview and len(self._current_pattern) <= 1:
                tk.messagebox.showwarning("Cannot Delete", "Cannot delete the last step. Pattern must have at least one step.")
                return
            
            if tk.messagebox.askyesno("Confirm Delete", f"Delete step #{index+1}?"):
                if is_preview:
                    self._current_pattern.pop(index)
                    success, message = self.automation_manager.save_pattern(self._current_pattern_name, self._current_pattern)
                    if success:
                        self._show_preview_pattern_blocks(self._current_pattern)
                        safe_schedule_ui_update(self.window, lambda: self._ensure_pattern_selected(self._current_pattern_name), 10)
                        dialog.destroy()
                    else:
                        tk.messagebox.showerror("Error", f"Failed to save pattern: {message}")
                else:
                    self._delete_step_with_selection_restore(index)
                    dialog.destroy()
        
        def cancel_edit():
            self._restore_pattern_selection_and_preview()
            dialog.destroy()
        
        button_container = ttk.Frame(buttons_frame)
        button_container.pack(anchor=tk.CENTER, pady=(10, 0))
        
        save_btn = ttk.Button(button_container, text="Save Changes", command=save_changes, width=15)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        delete_btn = ttk.Button(button_container, text="Delete Step", command=delete_step, width=15)
        delete_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = ttk.Button(button_container, text="Cancel", command=cancel_edit, width=12)
        cancel_btn.pack(side=tk.LEFT)
        
        dialog.bind('<Return>', lambda e: save_changes())
        dialog.bind('<Escape>', lambda e: cancel_edit())
        
        dialog.update_idletasks()

    def _show_step_context_menu(self, event, index, step):
        context_menu = tk.Menu(self.window, tearoff=0)
        context_menu.add_command(label="Edit Step", command=lambda: self._edit_step_dialog(index, step))
        context_menu.add_command(label="Delete Step", command=lambda: self._delete_step(index))
        context_menu.add_separator()
        context_menu.add_command(label="Insert Before", command=lambda: self._insert_step_dialog(index))
        context_menu.add_command(label="Insert After", command=lambda: self._insert_step_dialog(index + 1))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()



    def _update_step(self, index, new_step):
        pattern = self._current_pattern
        if 0 <= index < len(pattern):
            pattern[index] = new_step
            self.automation_manager.recorded_pattern = pattern.copy()
            self._unsaved_changes = True
            self.window.after_idle(lambda: self._refresh_pattern_display(pattern))

    def _delete_step(self, index):
        pattern = self._current_pattern
        if 0 <= index < len(pattern):
            pattern.pop(index)
            self.automation_manager.recorded_pattern = pattern.copy()
            self._unsaved_changes = True
            self.window.after_idle(lambda: self._refresh_pattern_display(pattern))

    def _save_pattern_silently(self):
        try:
            if not hasattr(self, '_current_pattern_name') or not self._current_pattern_name:
                return
            
            if not hasattr(self, '_current_pattern') or not self._current_pattern:
                return
            
            success, message = self.automation_manager.save_pattern(self._current_pattern_name, self._current_pattern)
            if not success:
                logger.debug(f"Failed to save pattern silently: {message}")
            
        except Exception as e:
            logger.debug(f"Error saving pattern silently: {e}")

    def _refresh_pattern_display(self, pattern):
        try:
            self._current_pattern = pattern.copy()
            
            self._previous_pattern_length = len(pattern)
            
            if pattern:
                self._display_recorded_pattern_blocks(pattern, is_recording=False)
                if hasattr(self, 'save_recorded_button') and self.save_recorded_button:
                    self.save_recorded_button.config(state=tk.NORMAL)
                if hasattr(self, 'preview_recorded_button') and self.preview_recorded_button:
                    self.preview_recorded_button.config(state=tk.NORMAL)
                if hasattr(self, 'clear_button') and self.clear_button:
                    self.clear_button.config(state=tk.NORMAL)
            else:
                self._show_empty_pattern_state()
                if hasattr(self, 'save_recorded_button') and self.save_recorded_button:
                    self.save_recorded_button.config(state=tk.DISABLED)
                if hasattr(self, 'preview_recorded_button') and self.preview_recorded_button:
                    self.preview_recorded_button.config(state=tk.DISABLED)
                if hasattr(self, 'clear_button') and self.clear_button:
                    self.clear_button.config(state=tk.DISABLED)
        except Exception as e:
            pass

    def _insert_step_dialog(self, index):
        dialog = tk.Toplevel(self.window)
        dialog.title("Insert Step")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="25")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(main_frame, text=f"Insert Step at Position {index+1}", font=("Segoe UI", 12, "bold"))
        title_label.pack(pady=(0, 20))
        
        input_frame = ttk.LabelFrame(main_frame, text="Key/Combination", padding="15")
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        entry = ttk.Entry(input_frame, font=("Segoe UI", 12))
        entry.pack(fill=tk.X, pady=(5, 10))
        entry.focus()
        
        examples_label = ttk.Label(input_frame, text="Examples: w, a+d, shift+w, ctrl+space", 
                                  font=("Segoe UI", 9), foreground="#666666")
        examples_label.pack()
        
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(15, 10))
        
        def insert_step():
            new_step_key = entry.get().strip().upper()
            if new_step_key and validate_step_input(new_step_key):
                new_step = {'key': new_step_key, 'duration': None}
                self._insert_step(index, new_step)
                dialog.destroy()
            else:
                tk.messagebox.showerror("Invalid Input", "Please enter a valid key or combination (e.g., W, SHIFT+W, CTRL+SPACE)")
        button_container = ttk.Frame(buttons_frame)
        button_container.pack(anchor=tk.CENTER)
        
        ttk.Button(button_container, text="Insert Step", command=insert_step, width=15).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_container, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT)
        
        dialog.bind('<Return>', lambda e: insert_step())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
        
        dialog.update_idletasks()

    def _insert_step(self, index, new_step):
        pattern = self._current_pattern
        pattern.insert(index, new_step)
        self.automation_manager.recorded_pattern = pattern.copy()
        self._unsaved_changes = True
        self.window.after_idle(lambda: self._refresh_pattern_display(pattern))

    def _animate_block_entrance(self, frame, target_width, target_height):
        try:
            if not frame.winfo_exists():
                return
        except tk.TclError:
            return
            
        try:
            current_width = frame.winfo_reqwidth()
            current_height = frame.winfo_reqheight()
        except tk.TclError:
            return
        
        if current_width < target_width or current_height < target_height:
            width_step = max(1, (target_width - current_width) // 3)
            height_step = max(1, (target_height - current_height) // 3)
            
            new_width = min(current_width + width_step, target_width)
            new_height = min(current_height + height_step, target_height)
            
            try:
                frame.config(width=new_width, height=new_height)
            except tk.TclError:
                return
            
            if new_width < target_width or new_height < target_height:
                try:
                    if self.window.winfo_exists():
                        self.window.after(30, lambda: self._animate_block_entrance(frame, target_width, target_height))
                except tk.TclError:
                    return

    def _display_recorded_pattern_blocks(self, pattern, is_recording=False):
        if not pattern:
            if self.recorded_pattern_frame.winfo_children():
                for widget in self.recorded_pattern_frame.winfo_children():
                    widget.destroy()
            self._show_empty_pattern_state()
            self._previous_pattern_length = 0
            return

        canvas_width = max(self.recorded_pattern_canvas.winfo_width() - 20, 400)
        
        fixed_avg_width = 90  
        blocks_per_row = max(2, canvas_width // fixed_avg_width)
        
        if not hasattr(self, '_current_blocks_per_row'):
            self._current_blocks_per_row = blocks_per_row
        elif not is_recording or len(pattern) == 0:
            self._current_blocks_per_row = blocks_per_row
        else:
            blocks_per_row = self._current_blocks_per_row
        
        previous_length = getattr(self, '_previous_pattern_length', 0)
        current_length = len(pattern)
        
        if is_recording and current_length > previous_length and previous_length > 0:
            for idx in range(previous_length, current_length):
                step = pattern[idx]
                row = idx // blocks_per_row
                col = idx % blocks_per_row
                
                block = self._create_pattern_block(step, idx, self.recorded_pattern_frame, animate=True)
                block.grid(row=row, column=col, padx=5, pady=8, sticky="nsew")
                block.update_idletasks()
        else:
            for widget in self.recorded_pattern_frame.winfo_children():
                widget.destroy()
                
            for idx, step in enumerate(pattern):
                row = idx // blocks_per_row
                col = idx % blocks_per_row
                
                block = self._create_pattern_block(step, idx, self.recorded_pattern_frame, animate=False)
                block.grid(row=row, column=col, padx=5, pady=8, sticky="nsew")
                block.update_idletasks()
        
        total_rows = (len(pattern) + blocks_per_row - 1) // blocks_per_row
        for c in range(blocks_per_row):
            self.recorded_pattern_frame.grid_columnconfigure(c, weight=1, minsize=85)
        for r in range(total_rows):
            self.recorded_pattern_frame.grid_rowconfigure(r, weight=0, minsize=60)

        self._previous_pattern_length = len(pattern)
        
        self.recorded_pattern_frame.update_idletasks()
        self._update_recorded_canvas_scroll_region()
        
        if is_recording:
            safe_schedule_ui_update(self.window, self._auto_scroll_to_latest, 10)
        else:
            safe_schedule_ui_update(self.window, lambda: self.recorded_pattern_canvas.yview_moveto(0.0), 10)

    def _update_recorded_canvas_scroll_region(self):
        self.recorded_pattern_frame.update_idletasks()

        canvas_width = max(self.recorded_pattern_canvas.winfo_width(), 400)
        if canvas_width > 1:
            self.recorded_pattern_canvas.itemconfig(self.recorded_canvas_window, width=canvas_width)
        
        self.recorded_pattern_frame.update_idletasks()
   
        frame_width = self.recorded_pattern_frame.winfo_reqwidth()
        frame_height = self.recorded_pattern_frame.winfo_reqheight()
        
        if frame_width > 0 and frame_height > 0:
            self.recorded_pattern_canvas.configure(scrollregion=(0, 0, frame_width + 20, frame_height + 20))
        else:
            self.recorded_pattern_canvas.configure(scrollregion=(0, 0, 0, 0))

    def _show_empty_pattern_state(self):

        for widget in self.recorded_pattern_frame.winfo_children():
            widget.destroy()
        
        empty_label = tk.Label(self.recorded_pattern_frame, 
                             text="No recorded steps yet\nStart recording to add pattern steps", 
                             font=("Segoe UI", 11),
                             fg="gray",
                             bg="#f8f9fa",
                             justify=tk.CENTER)
        empty_label.pack(expand=True, pady=20)
    
        self.recorded_pattern_frame.update_idletasks()
        self.recorded_pattern_canvas.configure(scrollregion=(0, 0, 0, 0))

    def _safe_export_pattern(self, pattern_name):
        if not self._check_button_cooldown():
            return

        try:
            pattern_info = self.automation_manager.get_pattern_list()
            if pattern_name not in pattern_info:
                messagebox.showerror("Error", "Pattern not found.")
                return

            pattern_data = {
                pattern_name: pattern_info[pattern_name]['pattern']
            }

            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                title=f"Export Pattern: {pattern_name}"
            )

            if filepath:
                threading.Thread(target=self._export_pattern, args=(pattern_name, pattern_data, filepath), daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export pattern: {str(e)}")

    def _export_pattern(self, pattern_name, pattern_data, filepath):
        try:
            if not filepath.lower().endswith('.json'):
                filepath += '.json'

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(pattern_data, f, indent=2, ensure_ascii=False)
            
            success_msg = f"Pattern '{pattern_name}' exported successfully!"
            self._safe_schedule_ui_update(0, lambda msg=success_msg: messagebox.showinfo("Success", msg))

        except Exception as e:
            error_msg = f"Failed to export pattern: {str(e)}"
            self._safe_schedule_ui_update(0, lambda msg=error_msg: messagebox.showerror("Error", msg))

    def _safe_import_patterns(self):
        if not self._check_button_cooldown():
            return

        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Import Pattern(s)"
        )

        if not filepath:
            return

        threading.Thread(target=self._import_patterns, args=(filepath,), daemon=True).start()

    def _import_patterns(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if is_single_pattern(data):
                logger.debug(f"Importing single pattern with metadata format: {data.get('name', 'unknown')}")
                self._import_single_pattern(data)
            else:
                logger.debug(f"Importing multiple patterns format with {len(data)} patterns")
                self._import_multiple_patterns(data)

        except json.JSONDecodeError:
            self._safe_schedule_ui_update(0, lambda: messagebox.showerror("Error", "Invalid JSON file format."))
        except Exception as e:
            error_msg = f"Failed to import patterns: {str(e)}"
            self._safe_schedule_ui_update(0, lambda msg=error_msg: messagebox.showerror("Error", msg))



    def _import_single_pattern(self, pattern_data):
        try:
        
            clean_data = clean_pattern_data(pattern_data)
            
        
            if not self._validate_pattern_data(clean_data):
                return

            pattern_name = clean_data['name'].strip()
            raw_pattern = clean_data['pattern']
            
            success, result = process_pattern_steps(raw_pattern)
            if not success:
                self._safe_schedule_ui_update(0, lambda: messagebox.showerror("Error", result))
                return
            
            pattern = result

            existing_patterns = self.automation_manager.get_pattern_list()
            if pattern_name in existing_patterns:
                def ask_overwrite():
                    if self.window and self.window.winfo_exists():
                        return messagebox.askyesno("Pattern Exists",
                                                   f"Pattern '{pattern_name}' already exists. Overwrite it?")
                    return False

                if not ask_overwrite():
                    return

        
            success, message = self.automation_manager.save_pattern(pattern_name, pattern)

            def show_result():
                try:
                    if not self.window or not self.window.winfo_exists():
                        return
                    
                    if success:
                        messagebox.showinfo("Success", f"Pattern '{pattern_name}' imported successfully!")
                        self.refresh_pattern_list()
                    else:
                        messagebox.showerror("Error", f"Failed to import pattern: {message}")
                except Exception:
                    pass

            if self.window and self.window.winfo_exists():
                self.window.after(100, show_result)

        except Exception as e:
            def show_error():
                try:
                    if self.window and self.window.winfo_exists():
                        messagebox.showerror("Error", f"Failed to import pattern: {str(e)}")
                except Exception:
                    pass
            
            self._safe_schedule_ui_update(100, show_error)

    def _import_multiple_patterns(self, patterns_data):
        try:
            if not isinstance(patterns_data, dict):
                self._safe_schedule_ui_update(0, lambda: messagebox.showerror("Error", "Invalid patterns file format."))
                return

            loaded_count = 0
            errors = []

            for pattern_name, pattern in patterns_data.items():
                try:
                    if isinstance(pattern, list):
                        success, result = process_pattern_steps(pattern)
                        if not success:
                            errors.append(f"{pattern_name}: {result}")
                            continue
                        
                        cleaned_pattern = result
                        
                        existing_patterns = self.automation_manager.get_pattern_list()
                        if pattern_name in existing_patterns:
                            errors.append(f"{pattern_name}: Pattern already exists (skipped)")
                            continue
                        
                        if cleaned_pattern:  
                            success, message = self.automation_manager.save_pattern(pattern_name, cleaned_pattern)
                            if success:
                                loaded_count += 1
                            else:
                                errors.append(f"{pattern_name}: {message}")
                    elif isinstance(pattern, dict) and "pattern" in pattern:
                        if not self._validate_pattern_data(pattern, lambda msg: errors.append(f"{pattern_name}: {msg}")):
                            continue
                            
                        raw_pattern = pattern['pattern']
                        success, result = process_pattern_steps(raw_pattern)
                        if not success:
                            errors.append(f"{pattern_name}: {result}")
                            continue
                        
                        cleaned_pattern = result
                        
                        existing_patterns = self.automation_manager.get_pattern_list()
                        if pattern_name in existing_patterns:
                            errors.append(f"{pattern_name}: Pattern already exists (skipped)")
                            continue
                        
                        if cleaned_pattern:
                            success, message = self.automation_manager.save_pattern(pattern_name, cleaned_pattern)
                            if success:
                                loaded_count += 1
                            else:
                                errors.append(f"{pattern_name}: {message}")
                    else:
                        errors.append(f"{pattern_name}: Invalid pattern format")
                except Exception as e:
                    errors.append(f"{pattern_name}: {str(e)}")

            self._safe_schedule_ui_update(0, lambda: self._show_import_results(loaded_count, errors))

        except Exception as e:
            error_msg = f"Failed to import patterns: {str(e)}"
            self._safe_schedule_ui_update(0, lambda: messagebox.showerror("Error", error_msg))

    def _show_import_results(self, loaded_count, errors):
        try:
            if loaded_count > 0:
                self.refresh_pattern_list()

            if errors:
                error_message = f"Imported {loaded_count} patterns successfully.\n\nErrors:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    error_message += f"\n... and {len(errors) - 10} more errors"
                messagebox.showwarning("Import Complete with Errors", error_message)
            else:
                messagebox.showinfo("Success", f"Successfully imported {loaded_count} patterns!")

        except Exception:
            pass

    def _validate_pattern_data(self, pattern_data):
        def show_error(message):
            self._safe_schedule_ui_update(0, lambda: messagebox.showerror("Error", message))
        
        return validate_pattern_data(pattern_data, show_error)

    def refresh_pattern_list(self):
        if not self._validate_ui_state('pattern_listbox'):
            return
            
        try:
            self.pattern_listbox.winfo_exists()
        except tk.TclError:
            return
            
        try:
            current_selection = None
            selection = self.pattern_listbox.curselection()
            if selection:
                current_selection = self.pattern_listbox.get(selection[0])

            self.pattern_listbox.delete(0, tk.END)
            pattern_info = self.automation_manager.get_pattern_list()

            for name, info in sorted(pattern_info.items()):
                pattern_type = info['type']
                length = info['length']
                display_text = f"{name} ({pattern_type}, {length} moves)"
                self.pattern_listbox.insert(tk.END, display_text)

                if current_selection == display_text:
                    self.pattern_listbox.selection_set(tk.END)

            if not self.pattern_listbox.curselection() and self.pattern_listbox.size() > 0:
                self.pattern_listbox.selection_set(0)
                self._on_pattern_select(None)

        except tk.TclError:
            return
        except Exception:
            pass

    def _on_pattern_select(self, event=None):
        if not self._validate_ui_state('pattern_listbox'):
            return
            
        try:
            self.pattern_listbox.winfo_exists()
        except tk.TclError:
            return
            
        try:
            selection = self.pattern_listbox.curselection()
            if not selection:
             
                if hasattr(self, 'preview_pattern_button'):
                    self.preview_pattern_button.config(state=tk.DISABLED)
                if hasattr(self, 'add_manual_key_button'):
                    self.add_manual_key_button.config(state=tk.DISABLED)
                if hasattr(self, 'pattern_info_label'):
                    self.pattern_info_label.config(text="Select a pattern to view details", fg="gray")
                self._show_preview_pattern_blocks([])
                return

            selected_text = self.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]

            pattern_info = self.automation_manager.get_pattern_list()
            if pattern_name not in pattern_info:
                if hasattr(self, 'preview_pattern_button'):
                    self.preview_pattern_button.config(state=tk.DISABLED)
                if hasattr(self, 'add_manual_key_button'):
                    self.add_manual_key_button.config(state=tk.DISABLED)
                return

            info = pattern_info[pattern_name]
            pattern = info['pattern']
            pattern_type = info['type']

        
            self._current_pattern_name = pattern_name
            self._current_pattern_type = pattern_type
            
      
            if pattern:
                converted_pattern = []
                for step in pattern:
                    if isinstance(step, dict):
                   
                        if 'click' not in step:
                            step['click'] = True  
                        converted_pattern.append(step)
                    elif isinstance(step, str):
                  
                        converted_pattern.append({'key': step, 'duration': None, 'click': True})
                    else:
                      
                        converted_pattern.append({'key': str(step), 'duration': None, 'click': True})
                self._current_pattern = converted_pattern
            else:
                self._current_pattern = []

           
            if hasattr(self, 'preview_pattern_button'):
                self.preview_pattern_button.config(state=tk.NORMAL)
            
       
            if hasattr(self, 'add_manual_key_button'):
                if pattern_type == 'custom':
                    self.add_manual_key_button.config(state=tk.NORMAL)
                else:
                    self.add_manual_key_button.config(state=tk.DISABLED)

        
            if hasattr(self, 'pattern_info_label'):
                info_text = f"📁 {pattern_name} • {pattern_type.title()} • {len(pattern)} moves"
                if pattern_type == 'custom':
                    info_text += " (Editable)"
                self.pattern_info_label.config(text=info_text, fg="black")

        
            self._show_preview_pattern_blocks(pattern)

        except Exception:
        
            if hasattr(self, 'preview_pattern_button'):
                self.preview_pattern_button.config(state=tk.DISABLED)
            if hasattr(self, 'add_manual_key_button'):
                self.add_manual_key_button.config(state=tk.DISABLED)
            pass

    def _safe_delete_pattern(self):
        if not self._check_button_cooldown():
            return

     
        if not self._validate_ui_state('pattern_listbox'):
            return
            
        try:
            self.pattern_listbox.winfo_exists()
        except tk.TclError:
        
            return

        try:
            selection = self.pattern_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a pattern to delete.")
                return

            selected_text = self.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]

            if messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete the pattern '{pattern_name}'?"):
                success, message = self.automation_manager.delete_custom_pattern(pattern_name)

                if success:
                    messagebox.showinfo("Success", message)
                    self.refresh_pattern_list()
                    self._clear_preview()
                else:
                    messagebox.showerror("Error", message)

        except tk.TclError:
         
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete pattern: {str(e)}")

    def _clear_preview(self):
     
        if not self._validate_ui_state('preview_pattern_frame'):
            return
            
        try:
         
            if hasattr(self, 'pattern_info_label'):
                self.pattern_info_label.config(text="Select a pattern to view details", fg="gray")
            
         
            self._show_preview_pattern_blocks([])
        except tk.TclError:
           
            pass
        except Exception:
            pass

    def _safe_toggle_recording(self):
        if not self._check_button_cooldown():
            return

        try:
            if not self.automation_manager.is_recording:
                self._start_recording()
            else:
                self._stop_recording()
        except Exception as e:
            messagebox.showerror("Error", f"Recording error: {str(e)}")

    def _start_recording(self):
      
        allow_custom_keys = False
        if hasattr(self, 'custom_keys_var') and self.custom_keys_var:
            try:
                allow_custom_keys = self.custom_keys_var.get()
            except:
                allow_custom_keys = False
                
  
        click_enabled = True
                
        self.automation_manager.start_recording_pattern(allow_custom_keys=allow_custom_keys, 
                                                       click_enabled=click_enabled)
        
        if hasattr(self, 'record_button') and self.record_button:
            self.record_button.config(text="⏹ Stop")
        if hasattr(self, 'record_status') and self.record_status:
      
            if allow_custom_keys:
                self.record_status.config(text="● Recording... Use any keys to move & click", foreground="red")
            else:
                self.record_status.config(text="● Recording... Use WASD to move & click", foreground="red")
        self._update_running = True
        self._update_recorded_display()

    def _stop_recording(self):
        self._update_running = False
        recorded_pattern = self.automation_manager.stop_recording_pattern()
        if hasattr(self, 'record_button') and self.record_button:
            self.record_button.config(text="● Start")
        if hasattr(self, 'record_status') and self.record_status:
            self.record_status.config(text="✓ Recording stopped", foreground="green")

        if recorded_pattern:
      
            self._current_pattern = recorded_pattern.copy()
         
            self.automation_manager.recorded_pattern = recorded_pattern.copy()
            
            if hasattr(self, 'save_recorded_button') and self.save_recorded_button:
                self.save_recorded_button.config(state=tk.NORMAL)
            if hasattr(self, 'preview_recorded_button') and self.preview_recorded_button:
                self.preview_recorded_button.config(state=tk.NORMAL)
            if hasattr(self, 'clear_button') and self.clear_button:
                self.clear_button.config(state=tk.NORMAL)
            self._display_recorded_pattern_blocks(recorded_pattern, is_recording=False)
        
            if hasattr(self, 'record_status') and self.record_status:
                self.record_status.config(text="✓ Pattern ready to save!", foreground="blue")
        else:
            messagebox.showinfo("Info", "No movements were recorded.")

    def _clear_pattern(self):
        if not self._check_button_cooldown():
            return
        
        try:
         
            self.automation_manager.recorded_pattern = []
        
            self._current_pattern = []
            
        
            self._show_empty_pattern_state()
            
      
            if hasattr(self, 'save_recorded_button') and self.save_recorded_button:
                self.save_recorded_button.config(state=tk.DISABLED)
            
         
            if hasattr(self, 'preview_recorded_button') and self.preview_recorded_button:
                self.preview_recorded_button.config(state=tk.DISABLED)
            
         
            if hasattr(self, 'clear_button') and self.clear_button:
                self.clear_button.config(state=tk.DISABLED)
            
         
            if hasattr(self, 'recorded_name_entry') and self.recorded_name_entry:
                self.recorded_name_entry.delete(0, tk.END)
            
       
            self._previous_pattern_length = 0
            self._last_displayed_length = 0
            
      
            if hasattr(self, 'record_status') and self.record_status:
                self.record_status.config(text="✕ Pattern cleared - Ready to record", foreground="black")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear pattern: {str(e)}")

    def _update_recorded_display(self):
        if not self._update_running or not self.automation_manager.is_recording:
            return

        pattern = self.automation_manager.recorded_pattern
        move_count = len(pattern)
        
   
        self._current_pattern = pattern.copy()
        
   
        current_length = len(pattern)
        if current_length != getattr(self, '_last_displayed_length', 0):
         
            if pattern:
                self._display_recorded_pattern_blocks(pattern, is_recording=True)
            else:
                self._show_empty_pattern_state()
            
            self._last_displayed_length = current_length
        
       
        if hasattr(self, 'record_status') and self.record_status:
            self.record_status.config(text=f"● Recording... {move_count} moves", foreground="red")

        if self._update_running:
        
            self.window.after(200, self._update_recorded_display)

    def _auto_scroll_to_latest(self):
      
        self.recorded_pattern_canvas.update_idletasks()
        self.recorded_pattern_canvas.yview_moveto(1.0)

    def _display_recorded_pattern(self, pattern):
        self._display_recorded_pattern_blocks(pattern)

    def _safe_save_pattern(self):
        if not self._check_button_cooldown():
            return

     
        if not self._validate_ui_state('recorded_name_entry'):
            return
            
        try:
          
            self.recorded_name_entry.winfo_exists()
        except tk.TclError:
          
            return

        try:
            name = self.recorded_name_entry.get().strip()

            if not name:
                messagebox.showerror("Error", "Please enter a name for the recorded pattern.")
                return

            if not self._validate_pattern_name(name):
                return

         
            pattern = self._current_pattern.copy()
            if not pattern:
                messagebox.showerror("Error", "No pattern recorded.")
                return

        
            success, message = self.automation_manager.save_pattern(name, pattern)

            if success:
                messagebox.showinfo("Success", message)
                self._clear_recording_ui()
                self.refresh_pattern_list()
          
                self.switch_to_patterns_tab()
            else:
                messagebox.showerror("Error", message)

        except tk.TclError:
      
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save pattern: {str(e)}")

    def _validate_pattern_name(self, name):
        if len(name) > 50:
            messagebox.showerror("Error", "Pattern name too long (max 50 characters).")
            return False

        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in name for char in invalid_chars):
            invalid_chars_str = ', '.join(invalid_chars)
            messagebox.showerror("Error", f"Pattern name contains invalid characters: {invalid_chars_str}")
            return False

        return True

    def _clear_recording_ui(self):
        if hasattr(self, 'recorded_name_entry') and self.recorded_name_entry:
            self.recorded_name_entry.delete(0, tk.END)
        self._show_empty_pattern_state()
        if hasattr(self, 'save_recorded_button') and self.save_recorded_button:
            self.save_recorded_button.config(state=tk.DISABLED)
        if hasattr(self, 'clear_button') and self.clear_button:
            self.clear_button.config(state=tk.DISABLED)
        if hasattr(self, 'record_status') and self.record_status:
            self.record_status.config(text="Ready to record", foreground="black")

    def close_window(self):
        self._update_running = False

        if hasattr(self.automation_manager, 'is_recording') and self.automation_manager.is_recording:
            self.automation_manager.stop_recording_pattern()

        if self.window:
            self.window.destroy()
            self.window = None
            
   
        self.pattern_listbox = None
        self.preview_canvas = None
        self.preview_pattern_frame = None
        self.pattern_info_label = None
        self.recording_frame = None
        self.record_button = None
        self.record_status = None
        self.recorded_name_entry = None
        self.save_recorded_button = None
        self.clear_button = None

    def _show_context_menu(self, event):
 
        if not self._validate_ui_state('pattern_listbox'):
            return
            
        try:
        
            self.pattern_listbox.winfo_exists()
        except tk.TclError:
       
            return
            
        try:
            selection = self.pattern_listbox.curselection()
            if not selection:
                return

            selected_text = self.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]

            pattern_info = self.automation_manager.get_pattern_list()
            if pattern_name not in pattern_info or pattern_info[pattern_name]['type'] == 'built-in':
                return

            context_menu = tk.Menu(self.window, tearoff=0)
            context_menu.add_command(label="Preview Pattern",
                                     command=lambda name=pattern_name: self._preview_pattern_by_name(name))
            context_menu.add_separator()
            context_menu.add_command(label="Export Pattern",
                                     command=lambda name=pattern_name: self._safe_export_pattern(name))

            context_menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass
        finally:
            context_menu.grab_release()

    def _on_custom_keys_changed(self):
        if hasattr(self, 'custom_keys_var') and self.custom_keys_var:
            allow_custom_keys = self.custom_keys_var.get()
            
     
            if hasattr(self.automation_manager, 'update_custom_keys_setting'):
                self.automation_manager.update_custom_keys_setting(allow_custom_keys)
            
      
            if (hasattr(self, 'record_status') and self.record_status and 
                hasattr(self.automation_manager, 'is_recording') and self.automation_manager.is_recording):
                
           
                if allow_custom_keys:
                    self.record_status.config(text="● Recording... Use any keys to move & click", foreground="red")
                else:
                    self.record_status.config(text="● Recording... Use WASD to move & click", foreground="red")

    def _safe_preview_pattern(self):
        if not self._check_button_cooldown():
            return

        if not self._validate_ui_state('pattern_listbox'):
            return

        try:
            self.pattern_listbox.winfo_exists()
        except tk.TclError:
            return

        try:
            selection = self.pattern_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a pattern to preview.")
                return

            selected_text = self.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]
            
     
            self._preview_pattern_by_name(pattern_name)

        except Exception as e:
            self._update_preview_button_states(False)
            messagebox.showerror("Error", f"Failed to preview pattern: {str(e)}")

    def _preview_pattern_by_name(self, pattern_name):
        try:
       
            message = (f"Preview pattern '{pattern_name}'?\n\n"
                      f"This will:\n"
                      f"• Focus the Roblox window\n"
                      f"• Execute the pattern once\n"
                      f"• Each step will be performed with brief pauses\n\n"
                      f"Make sure you're ready to move in Roblox!")
            
            if not messagebox.askyesno("Preview Pattern", message):
                return

     
            self._update_preview_button_states(True)

           
            def run_preview():
                try:
                    success, message = self.automation_manager.preview_pattern(pattern_name)
                    
                    def update_ui():
                        self._update_preview_button_states(False)
                        if success:
                            messagebox.showinfo("Preview Complete", message)
                        else:
                            messagebox.showerror("Preview Failed", message)
                    
                    self._safe_schedule_ui_update(0, update_ui)
                    
                except Exception as e:
                    def show_error():
                        self._update_preview_button_states(False)
                        messagebox.showerror("Preview Error", f"Unexpected error during preview: {str(e)}")
                    self._safe_schedule_ui_update(0, show_error)

            self._preview_thread = threading.Thread(target=run_preview, daemon=True)
            self._preview_thread.start()

        except Exception as e:
            self._update_preview_button_states(False)
            messagebox.showerror("Error", f"Failed to preview pattern: {str(e)}")

    def _safe_preview_recorded_pattern(self):
        if not self._check_button_cooldown():
            return



        try:
            if not hasattr(self, 'automation_manager') or not self.automation_manager:
                messagebox.showerror("Error", "Automation manager not available")
                return
                
        
            recorded_pattern = getattr(self.automation_manager, 'recorded_pattern', [])
            if not recorded_pattern:
                messagebox.showwarning("No Pattern", "No recorded pattern to preview. Record some steps first.")
                return

      
            pattern_keys = []
            for step in recorded_pattern:
                if isinstance(step, dict):
                    pattern_keys.append(step.get('key', ''))
                else:
                    pattern_keys.append(str(step))

            if not pattern_keys:
                messagebox.showwarning("No Pattern", "Recorded pattern is empty.")
                return

         
            message = (f"Preview Recorded Pattern\n\n"
                      f"Pattern: {' → '.join(pattern_keys[:10])}"
                      f"{'...' if len(pattern_keys) > 10 else ''}\n"
                      f"Steps: {len(pattern_keys)}\n\n"
                      f"This will:\n"
                      f"• Focus the Roblox window\n"
                      f"• Execute the recorded pattern once\n"
                      f"• Each step will be performed with brief pauses\n\n"
                      f"Make sure you're ready to move in Roblox!")
            
            if not messagebox.askyesno("Preview Recorded Pattern", message):
                return

            self._update_preview_button_states(True)

      
            def run_preview():
                try:
                    success, message = self.automation_manager.preview_recorded_pattern(recorded_pattern)
                    
                    def update_ui():
                        self._update_preview_button_states(False)
                        if success:
                            messagebox.showinfo("Preview Complete", message)
                        else:
                            messagebox.showerror("Preview Failed", message)
                    
                    self._safe_schedule_ui_update(0, update_ui)
                    
                except Exception as e:
                    def show_error():
                        self._update_preview_button_states(False)
                        messagebox.showerror("Preview Error", f"Unexpected error during preview: {str(e)}")
                    self._safe_schedule_ui_update(0, show_error)

            self._preview_thread = threading.Thread(target=run_preview, daemon=True)
            self._preview_thread.start()

        except Exception as e:
            self._update_preview_button_states(False)
            messagebox.showerror("Error", f"Failed to preview recorded pattern: {str(e)}")


    def _show_preview_step_context_menu(self, event, index, step):
        if self._current_pattern_type != 'custom':
            return
            
        context_menu = tk.Menu(self.window, tearoff=0)
        context_menu.add_command(label=f"Edit Step #{index + 1}", 
                               command=lambda: self._edit_step_dialog(index, step, is_preview=True))
        context_menu.add_separator()
        context_menu.add_command(label=f"Delete Step #{index + 1}", 
                               command=lambda: self._delete_preview_step(index))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def _delete_preview_step(self, index):
        if self._current_pattern_type != 'custom' or len(self._current_pattern) <= 1:
            return
            
        self._current_pattern.pop(index)
        
     
        self.automation_manager.save_pattern(self._current_pattern_name, self._current_pattern)
        
   
        self._show_preview_pattern_blocks(self._current_pattern)
        
     
        self.refresh_pattern_list()

    def _show_pattern_info_dialog(self, step):
        if isinstance(step, dict):
            key = step.get('key', '')
            duration = step.get('duration', None)
        else:
            key = str(step)
            duration = None
            
        info_text = f"Key: {key.upper()}\n"
        if duration is not None:
            info_text += f"Duration: {duration}ms\n"
        else:
            info_text += "Duration: Default Key Duration\n"
        info_text += f"Pattern: {self._current_pattern_name} (Built-in)\n"
        info_text += "Built-in patterns cannot be edited."
        
    
        dialog = tk.Toplevel(self.window)
        dialog.title("Step Information")
        dialog.geometry("300x200")
        dialog.transient(self.window)
        dialog.grab_set()
         
        dialog.geometry("+%d+%d" % (self.window.winfo_rootx() + 100, self.window.winfo_rooty() + 100))
        
        info_label = tk.Label(dialog, text=info_text, font=("Segoe UI", 10), justify=tk.LEFT)
        info_label.pack(padx=20, pady=20)
        
        ttk.Button(dialog, text="OK", command=dialog.destroy).pack(pady=(0, 20))

    def _toggle_always_on_top(self):
        if self.window:
            is_on_top = self.always_on_top_var.get()
            self.window.attributes('-topmost', is_on_top)

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

    def _save_current_pattern_changes(self):
        try:
            if not hasattr(self, '_current_pattern_name') or not self._current_pattern_name:
                return
            
            if not hasattr(self, '_current_pattern') or not self._current_pattern:
                return
            
       
            success, message = self.automation_manager.save_pattern(self._current_pattern_name, self._current_pattern)
            if not success:
                logger.debug(f"Failed to save pattern changes: {message}")
            
        except Exception as e:
            logger.debug(f"Error saving current pattern changes: {e}")

    def _update_step_with_selection_restore(self, index, new_step):

        current_pattern_name = getattr(self, '_current_pattern_name', None)

        if hasattr(self, '_current_pattern') and 0 <= index < len(self._current_pattern):
            self._current_pattern[index] = new_step
            if hasattr(self.automation_manager, 'recorded_pattern'):
                if 0 <= index < len(self.automation_manager.recorded_pattern):
                    self.automation_manager.recorded_pattern[index] = new_step
            self._unsaved_changes = True
            self._display_recorded_pattern_blocks(self._current_pattern, is_recording=False)

    def _delete_step_with_selection_restore(self, index):
      
        current_pattern_name = getattr(self, '_current_pattern_name', None)
      
        if hasattr(self, '_current_pattern') and 0 <= index < len(self._current_pattern):
            self._current_pattern.pop(index)
            if hasattr(self.automation_manager, 'recorded_pattern'):
                if 0 <= index < len(self.automation_manager.recorded_pattern):
                    self.automation_manager.recorded_pattern.pop(index)
            self._unsaved_changes = True
            self._display_recorded_pattern_blocks(self._current_pattern, is_recording=False)

    def _restore_pattern_selection_and_preview(self):
        try:
            current_pattern_name = getattr(self, '_current_pattern_name', None)
            if current_pattern_name:
               
                self._ensure_pattern_selected(current_pattern_name)
             
                if hasattr(self, '_current_pattern') and self._current_pattern:
                    self._show_preview_pattern_blocks(self._current_pattern)
        except Exception as e:
            logger.debug(f"Error restoring pattern selection and preview: {e}")

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

    def _stop_preview(self):
        if not self._check_button_cooldown():
            return
            
        try:
            if hasattr(self.automation_manager, 'stop_preview'):
                success, message = self.automation_manager.stop_preview()
                if success:
                    self._update_preview_button_states(False)
                    messagebox.showinfo("Preview Stopped", message)
                else:
                    messagebox.showerror("Error", f"Failed to stop preview: {message}")
            else:
                messagebox.showwarning("Not Available", "Stop preview functionality not available")
        except Exception as e:
            messagebox.showerror("Error", f"Error stopping preview: {str(e)}")

    def _update_preview_button_states(self, is_preview_running):
        try:
        
            if hasattr(self, 'preview_button') and self.preview_button:
                self.preview_button.configure(state=tk.DISABLED if is_preview_running else tk.NORMAL)
            if hasattr(self, 'stop_preview_button') and self.stop_preview_button:
                self.stop_preview_button.configure(state=tk.NORMAL if is_preview_running else tk.DISABLED)
                
        
            if hasattr(self, 'preview_recorded_button') and self.preview_recorded_button:
           
                current_state = str(self.preview_recorded_button['state'])
                if not is_preview_running and current_state != 'disabled':
                    self.preview_recorded_button.configure(state=tk.NORMAL)
                elif is_preview_running:
                    self.preview_recorded_button.configure(state=tk.DISABLED)
                    
            if hasattr(self, 'stop_recorded_preview_button') and self.stop_recorded_preview_button:
                self.stop_recorded_preview_button.configure(state=tk.NORMAL if is_preview_running else tk.DISABLED)
                
        except tk.TclError:
            return
        except Exception as e:
            logger.error(f"Error updating preview button states: {e}")

    def _safe_add_manual_key(self):
        dialog = tk.Toplevel(self.window)
        dialog.title("Add Manual Key")
        dialog.geometry("450x450")  
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.grab_set()
        
  
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (450 // 2) 
        dialog.geometry(f"450x450+{x}+{y}")
        
     
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
    
        title_label = ttk.Label(main_frame, text="Add Manual Key to Pattern", font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
    
        key_frame = ttk.LabelFrame(main_frame, text="Key/Combination", padding="10")
        key_frame.pack(fill=tk.X, pady=(0, 10))
        
        key_entry = ttk.Entry(key_frame, font=("Segoe UI", 12))
        key_entry.pack(fill=tk.X, pady=(5, 5))
        key_entry.focus()
    
        examples_label = ttk.Label(key_frame, text="Examples: w, a+d, shift+w, ctrl+space, f1, enter", 
                                  font=("Segoe UI", 9), foreground="#666666")
        examples_label.pack(pady=(0, 5))
        
     
        duration_frame = ttk.LabelFrame(main_frame, text="Key Duration (ms)", padding="10")
        duration_frame.pack(fill=tk.X, pady=(0, 10))
        
        duration_entry = ttk.Entry(duration_frame, font=("Segoe UI", 12))
        duration_entry.pack(fill=tk.X, pady=(5, 5))
        
    
        duration_help = ttk.Label(duration_frame, text="Leave empty to use default Key Duration setting", 
                                 font=("Segoe UI", 9), foreground="#666666")
        duration_help.pack(pady=(0, 5))
        
   
        click_frame = ttk.LabelFrame(main_frame, text="Click Behavior", padding="10")
        click_frame.pack(fill=tk.X, pady=(0, 15))
        
        click_enabled_var = tk.BooleanVar(value=True)
        click_checkbox = ttk.Checkbutton(click_frame, text="Enable clicking for this key", 
                                        variable=click_enabled_var, 
                                        onvalue=True, offvalue=False)
        click_checkbox.pack(anchor="w", pady=(5, 5))
        
    
        click_help = ttk.Label(click_frame, text="When disabled, this key will only be pressed without clicking", 
                              font=("Segoe UI", 9), foreground="#666666")
        click_help.pack(anchor="w")
        
       
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        def add_key():
            new_key = key_entry.get().strip().upper()
            duration_text = duration_entry.get().strip()
            
            if not new_key or not validate_step_input(new_key):
                messagebox.showerror("Invalid Input", "Please enter a valid key or combination (e.g., W, SHIFT+W, CTRL+SPACE)")
                return
            
        
            new_duration = None
            if duration_text:
                try:
                    new_duration = int(duration_text)
                    if new_duration <= 0:
                        messagebox.showerror("Invalid Duration", "Duration must be a positive number")
                        return
                except ValueError:
                    messagebox.showerror("Invalid Duration", "Duration must be a number")
                    return
            
      
            new_step = {'key': new_key, 'duration': new_duration, 'click': click_enabled_var.get()}
            
       
            if hasattr(self, '_current_pattern') and self._current_pattern is not None:
                self._current_pattern.append(new_step)
                
            
                self.automation_manager.recorded_pattern = self._current_pattern.copy()
                
            
                self._refresh_pattern_display(self._current_pattern)
                
                messagebox.showinfo("Success", f"Manual key '{new_key}' added to pattern! Remember to save the pattern.")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "No pattern selected for editing")
        
        def cancel_add():
            dialog.destroy()
        
       
        button_container = ttk.Frame(buttons_frame)
        button_container.pack(anchor=tk.CENTER)
              
        add_btn = ttk.Button(button_container, text="Add Key", command=add_key, width=15)
        add_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = ttk.Button(button_container, text="Cancel", command=cancel_add, width=12)
        cancel_btn.pack(side=tk.LEFT)
        
    
        dialog.bind('<Return>', lambda e: add_key())
        dialog.bind('<Escape>', lambda e: cancel_add())
        
        
        dialog.update_idletasks()

    def _update_unsaved_changes_indicator(self, has_changes=True):
        self._has_unsaved_changes = has_changes
        if hasattr(self, 'unsaved_changes_label') and self.unsaved_changes_label:
            if has_changes:
                self.unsaved_changes_label.config(text="⚠ Unsaved changes", foreground="orange")
            else:
                self.unsaved_changes_label.config(text="✓ Saved", foreground="green")
           
                safe_schedule_ui_update(self.window, lambda: self.unsaved_changes_label.config(text=""), 2000)

