import tkinter as tk
from tkinter import Label, Button, Frame, Checkbutton, ttk
from interface.components import CollapsiblePane, AccordionManager, Tooltip


class DisabledTooltip:
    def __init__(self, widget, disabled_text, original_tooltip=None):
        self.widget = widget
        self.disabled_text = disabled_text
        self.original_tooltip = original_tooltip
        self.tooltip_window = None
        self.is_disabled = False

        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<Motion>", self.on_motion)

    def set_disabled(self, disabled, reason=None):
        self.is_disabled = disabled
        if reason: self.disabled_text = reason

    def on_motion(self, event=None):
        if self.tooltip_window: self.update_position()

    def show_tooltip(self, event=None):
        if self.tooltip_window: return
        if self.is_disabled and str(self.widget.cget('state')) == 'disabled':
            text = self.disabled_text
        elif self.original_tooltip:
            text = self.original_tooltip
        else:
            return
        self.create_tooltip(text)

    def create_tooltip(self, text):
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes('-topmost', True)
        bg_color = "#ffcccc" if self.is_disabled and str(
            self.widget.cget('state')) == 'disabled' else "#ffffe0"  # Light red for disabled, light yellow for normal
        label = tk.Label(self.tooltip_window, text=text, justify='left', background=bg_color, relief='solid',
                         borderwidth=1, font=("Segoe UI", 9, "normal"), wraplength=300, padx=8, pady=6)
        label.pack()
        self.update_position()

    def update_position(self):
        if not self.tooltip_window: return
        try:
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 25
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except tk.TclError:
                pass
            self.tooltip_window = None


class StatusTooltip:
    def __init__(self, widget, not_set_text, set_text, status_check_func):
        self.widget = widget
        self.not_set_text = not_set_text
        self.set_text = set_text
        self.status_check_func = status_check_func
        self.tooltip_window = None

        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<Motion>", self.on_motion)

    def on_motion(self, event=None):
        if self.tooltip_window: self.update_position()

    def show_tooltip(self, event=None):
        if self.tooltip_window: return
        is_set = self.status_check_func()
        text = self.set_text if is_set else self.not_set_text
        self.create_tooltip(text, is_set)

    def create_tooltip(self, text, is_set):
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes('-topmost', True)
        bg_color = "#e8f5e8" if is_set else "#fff0e0"  # Light green if set, light orange if not set
        label = tk.Label(self.tooltip_window, text=text, justify='left', background=bg_color, relief='solid',
                         borderwidth=1, font=("Segoe UI", 9, "normal"), wraplength=300, padx=8, pady=6)
        label.pack()
        self.update_position()

    def update_position(self):
        if not self.tooltip_window: return
        try:
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 25
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except tk.TclError:
                pass
            self.tooltip_window = None


class CollapsibleSubsection:
    def __init__(self, parent, title, bg_color="#f0f0f0"):  # Light gray default background
        self.parent = parent
        self.title = title
        self.bg_color = bg_color
        self.is_open = tk.BooleanVar(value=False)

        self.container = Frame(parent, bg=parent.cget('bg'))
        self.container.pack(fill='x', pady=(4, 2), padx=8)

        self.header = Frame(self.container, bg=bg_color, relief='raised', bd=1)
        self.header.pack(fill='x')

        self.toggle_btn = Button(self.header, text=f"▶ {title}", font=("Segoe UI", 9, 'bold'),
                                 bg=bg_color, fg="#333333", relief='flat', anchor='w',  # Dark gray text
                                 command=self.toggle, pady=2, padx=8)
        self.toggle_btn.pack(fill='x')

        self.content = Frame(self.container, bg=bg_color, relief='sunken', bd=1)

    def toggle(self):
        if self.is_open.get():
            self.content.pack_forget()
            self.toggle_btn.config(text=f"▶ {self.title}")
            self.is_open.set(False)
        else:
            self.content.pack(fill='x', pady=(0, 2))
            self.toggle_btn.config(text=f"▼ {self.title}")
            self.is_open.set(True)


class MainWindow:
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance
        self.walk_pattern_combo = None
        self.auto_shovel_checkbox = None
        self.auto_sell_checkbox = None
        self.use_cursor_checkbox = None
        self.shovel_dependent_widgets = []
        self.sell_dependent_widgets = []
        self.cursor_dependent_widgets = []
        self.disabled_tooltips = []
        self.status_tooltips = []

    def validate_param_entry(self, var_key, value):
        if not hasattr(self, '_validation_throttle'):
            self._validation_throttle = {}
        
        import time
        current_time = time.time()
        
        if var_key in self._validation_throttle:
            if current_time - self._validation_throttle[var_key] < 0.1:
                return True
        
        self._validation_throttle[var_key] = current_time
        
        if not value or value.strip() == "":
            self.dig_tool.root.after_idle(lambda: self._restore_default_value(var_key))
            return False
        
        try:
            if not self.dig_tool.settings_manager.validate_param_value(var_key, value):
                self.dig_tool.root.after_idle(lambda: self._restore_default_value(var_key))
                return False
        except:
            self.dig_tool.root.after_idle(lambda: self._restore_default_value(var_key))
            return False
        
        return True
    
    def _restore_default_value(self, var_key):
        try:
            default_value = self.dig_tool.settings_manager.get_default_value(var_key)
            if var_key in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key].set(default_value)
        except:
            pass

    def validate_cursor_position_toggle(self, *args):
        if not hasattr(self.dig_tool, 'cursor_position') or not self.dig_tool.cursor_position:
            if self.dig_tool.param_vars['use_custom_cursor'].get():
                self.dig_tool.param_vars['use_custom_cursor'].set(False)
                self.dig_tool.update_status("Error: Set cursor position first before enabling custom cursor!")
        if not hasattr(self.dig_tool, 'cursor_position') or not self.dig_tool.cursor_position:
            if self.dig_tool.param_vars['use_custom_cursor'].get():
                self.dig_tool.param_vars['use_custom_cursor'].set(False)
                self.dig_tool.update_status("Error: Set cursor position first before enabling custom cursor!")

    def validate_auto_sell_toggle(self, *args):
        if not self.dig_tool.automation_manager.sell_button_position:
            if self.dig_tool.param_vars['auto_sell_enabled'].get():
                self.dig_tool.param_vars['auto_sell_enabled'].set(False)
                self.dig_tool.update_status("Error: Set sell button first before enabling auto-sell!")

    def is_sell_button_set(self):
        return self.dig_tool.automation_manager.sell_button_position is not None

    def is_cursor_position_set(self):
        return hasattr(self.dig_tool, 'cursor_position') and self.dig_tool.cursor_position is not None

    def test_click_method(self):
        import threading
        threading.Thread(target=self._test_click_method_with_delay, daemon=True).start()

    def _test_click_method_with_delay(self):
        import time
        method = self.dig_tool.get_param('click_method')

        for i in range(3, 0, -1):
            self.dig_tool.root.after(0, lambda count=i, m=method:
            self.dig_tool.update_status(f"Testing {m.upper()} click in {count} seconds..."))
            time.sleep(1.0)

        self.dig_tool.root.after(0, lambda m=method:
        self.dig_tool.update_status(f"Performing {m.upper()} test click..."))

        from utils.system_utils import send_click
        success = send_click()

        if success:
            self.dig_tool.root.after(0, lambda m=method:
            self.dig_tool.update_status(f"{m.upper()} test click completed successfully!"))
        else:
            self.dig_tool.root.after(0, lambda m=method:
            self.dig_tool.update_status(f"{m.upper()} test click failed!"))
    def update_dependent_widgets_state(self, *args):
        auto_walk_enabled = self.dig_tool.param_vars.get('auto_walk_enabled', tk.BooleanVar()).get()

        if self.auto_shovel_checkbox:
            if auto_walk_enabled:
                self.auto_shovel_checkbox.config(state='normal', fg="#000000")  # Black text when enabled
            else:
                self.auto_shovel_checkbox.config(state='disabled', fg="#666666")  # Gray text when disabled
                self.dig_tool.param_vars['auto_shovel_enabled'].set(False)

        shovel_enabled = auto_walk_enabled and self.dig_tool.param_vars.get('auto_shovel_enabled',
                                                                            tk.BooleanVar()).get()
        for widget in self.shovel_dependent_widgets:
            widget.config(state='normal' if shovel_enabled else 'disabled')

        if self.auto_sell_checkbox:
            if auto_walk_enabled:
                self.auto_sell_checkbox.config(state='normal', fg="#000000")  # Black text when enabled
            else:
                self.auto_sell_checkbox.config(state='disabled', fg="#666666")  # Gray text when disabled
                self.dig_tool.param_vars['auto_sell_enabled'].set(False)

        sell_enabled = auto_walk_enabled and self.dig_tool.param_vars.get('auto_sell_enabled', tk.BooleanVar()).get()
        for widget in self.sell_dependent_widgets:
            widget.config(state='normal' if sell_enabled else 'disabled')

        cursor_enabled = self.dig_tool.param_vars.get('use_custom_cursor', tk.BooleanVar()).get()
        has_cursor_pos = hasattr(self.dig_tool, 'cursor_position') and self.dig_tool.cursor_position
        for widget in self.cursor_dependent_widgets:
            widget.config(state='normal' if cursor_enabled and has_cursor_pos else 'disabled')

        for tooltip in self.disabled_tooltips:
            if hasattr(tooltip, 'widget_type'):
                if tooltip.widget_type == 'shovel':
                    tooltip.set_disabled(not auto_walk_enabled, "Disabled: Auto-walk must be enabled first.")
                elif tooltip.widget_type == 'sell':
                    tooltip.set_disabled(not auto_walk_enabled, "Disabled: Auto-walk must be enabled first.")
                elif tooltip.widget_type == 'cursor':
                    tooltip.set_disabled(not has_cursor_pos, "Disabled: Set cursor position first")

    def create_ui(self):
        BG_COLOR = "#f0f0f0"  # Light gray main background
        FRAME_BG = "#ffffff"  # White frame background
        TEXT_COLOR = "#000000"  # Black text
        BTN_BG = "#e1e1e1"  # Light gray button background
        FONT_FAMILY = "Segoe UI"
        SECTION_PADY = 5
        PARAM_PADY = 4
        PARAM_PADX = 8
        ENTRY_WIDTH = 15
        BUTTON_PADY = 8
        LABEL_WIDTH = 25

        self.dig_tool.root.configure(bg=BG_COLOR)
        self.dig_tool.controls_panel = Frame(self.dig_tool.root, bg=BG_COLOR, padx=10, pady=10)
        self.dig_tool.controls_panel.pack(side=tk.TOP, fill=tk.X, expand=False)

        Label(self.dig_tool.controls_panel, text="Dig Tool", font=(FONT_FAMILY, 14, 'bold'), bg=BG_COLOR,
              fg=TEXT_COLOR).pack(pady=(0, 8), anchor='center')

        self.dig_tool.status_label = Label(self.dig_tool.controls_panel, text="Status: Select a game area to begin.",
                                           font=(FONT_FAMILY, 9), bg=BG_COLOR, fg=TEXT_COLOR, wraplength=780,
                                           justify='left')
        self.dig_tool.status_label.pack(fill=tk.X, pady=(0, 10), anchor='w')

        info_panel = Frame(self.dig_tool.controls_panel, bg=FRAME_BG, relief='solid', bd=1)
        info_panel.pack(fill=tk.X, pady=(0, 10), padx=2)

        info_header = Label(info_panel, text="Configuration Status", font=(FONT_FAMILY, 9, 'bold'), bg=FRAME_BG,
                            fg=TEXT_COLOR)
        info_header.pack(pady=(6, 4))

        self.dig_tool.area_info_label = Label(info_panel, text="Game Area: Not set", font=(FONT_FAMILY, 8), bg=FRAME_BG,
                                              fg="#666666", anchor='w')  # Gray text for info
        self.dig_tool.area_info_label.pack(fill='x', padx=12, pady=2)

        self.dig_tool.sell_info_label = Label(info_panel, text="Sell Button: Not set", font=(FONT_FAMILY, 8),
                                              bg=FRAME_BG, fg="#666666", anchor='w')  # Gray text for info
        self.dig_tool.sell_info_label.pack(fill='x', padx=12, pady=2)

        self.dig_tool.cursor_info_label = Label(info_panel, text="Cursor Position: Not set", font=(FONT_FAMILY, 8),
                                                bg=FRAME_BG, fg="#666666", anchor='w')  # Gray text for info
        self.dig_tool.cursor_info_label.pack(fill='x', padx=12, pady=(2, 8))

        actions_frame = Frame(self.dig_tool.controls_panel, bg=BG_COLOR)
        actions_frame.pack(fill=tk.X, pady=(0, SECTION_PADY))

        button_style = {'font': (FONT_FAMILY, 9), 'bg': BTN_BG, 'fg': TEXT_COLOR, 'relief': 'solid', 'borderwidth': 1,
                        'pady': 6}

        for i, (text, command) in enumerate(
                [("Select Area", self.dig_tool.start_area_selection), ("Start", self.dig_tool.toggle_detection),
                 ("Show/Hide", self.dig_tool.toggle_gui), ("Overlay", self.dig_tool.toggle_overlay)]):
            btn = Button(actions_frame, text=text, command=command, **button_style)
            if text == "Start":
                self.dig_tool.start_stop_btn = btn
            elif text == "Show/Hide":
                self.dig_tool.toggle_gui_btn = btn
            elif text == "Overlay":
                self.dig_tool.overlay_btn = btn
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0 if i == 0 else 2, 2 if i < 3 else 0))

        actions_frame2 = Frame(self.dig_tool.controls_panel, bg=BG_COLOR)
        actions_frame2.pack(fill=tk.X, pady=(SECTION_PADY, 0))

        sell_button_btn = Button(actions_frame2, text="Set Sell Button",
                                 command=self.dig_tool.start_sell_button_selection, **button_style)
        sell_button_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        StatusTooltip(sell_button_btn, "Click to set the sell button position for auto-selling",
                      "Sell button position is set. Click to change it.", self.is_sell_button_set)

        cursor_pos_btn = Button(actions_frame2, text="Set Cursor Pos",
                                command=self.dig_tool.start_cursor_position_selection, **button_style)
        cursor_pos_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        StatusTooltip(cursor_pos_btn, "Click to set a custom cursor position for clicking",
                      "Cursor position is set. Click to change it.", self.is_cursor_position_set)

        for i, (text, command, attr) in enumerate([("Show Preview", self.dig_tool.toggle_preview_window, 'preview_btn'),
                                                   ("Show Debug", self.dig_tool.toggle_debug_window, 'debug_btn')]):
            btn = Button(actions_frame2, text=text, command=command, **button_style)
            if attr:
                setattr(self.dig_tool, attr, btn)
                btn.config(state=tk.DISABLED)
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        config_frame = Frame(self.dig_tool.controls_panel, bg=BG_COLOR)
        config_frame.pack(fill='x', expand=True, pady=(8, 0))

        style = ttk.Style()
        style.configure("Header.TButton", font=(FONT_FAMILY, 9, 'bold'), background="#dcdcdc",
                        relief="flat")  # Light gray header buttons
        style.map("Header.TButton", background=[('active', '#c8c8c8')])  # Darker gray on hover

        self.dig_tool.accordion = AccordionManager(self.dig_tool)

        panes_config = [
            ("Detection", "#e8f4f8"),  # Light blue - detection settings
            ("Behavior", FRAME_BG),  # White - behavior settings
            ("Auto-Sell", "#fff8e8"),  # Light yellow - auto-sell settings
            ("Discord", "#f8e8f8"),  # Light pink - discord settings
            ("Window", "#f8f0e8"),  # Light orange - window settings
            ("Debug", "#f8e8e8"),  # Light red - debug settings
            ("Hotkeys", "#e8e8f8"),  # Light purple - hotkey settings
            ("Settings", "#e8f8f0")  # Light green - settings
        ]

        panes = {}
        for name, color in panes_config:
            pane = CollapsiblePane(config_frame, text=name, manager=self.dig_tool.accordion, bg_color=color)
            pane.pack(fill='x', pady=2)
            self.dig_tool.accordion.add_pane(pane)
            panes[name.lower().replace('-', '_')] = pane

        def create_param_entry(parent, text, var_key, dependent_list=None, widget_type=None):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

            label = Label(frame, text=text, font=(FONT_FAMILY, 9), bg=parent.cget('bg'), fg=TEXT_COLOR,
                          width=LABEL_WIDTH, anchor='w')
            label.pack(side='left')

            tooltip_text = self.dig_tool.settings_manager.get_description(var_key)
            Tooltip(label, tooltip_text)

            default_value = self.dig_tool.settings_manager.get_default_value(var_key)
            var_type = self.dig_tool.settings_manager.get_param_type(var_key)

            if var_key not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key] = var_type(value=default_value)
                self.dig_tool.last_known_good_params[var_key] = default_value

            if var_type != tk.BooleanVar:
                vcmd = (self.dig_tool.root.register(lambda value, key=var_key: self.validate_param_entry(key, value)), '%P')
                entry = tk.Entry(frame, textvariable=self.dig_tool.param_vars[var_key], font=(FONT_FAMILY, 9),
                                 bg=FRAME_BG, fg=TEXT_COLOR, relief='solid', width=ENTRY_WIDTH, borderwidth=1,
                                 validate='focusout', validatecommand=vcmd)
                entry.pack(side='right', ipady=3)

                if dependent_list is not None: dependent_list.append(entry)
                if widget_type:
                    disabled_tooltip = DisabledTooltip(entry, "", tooltip_text)
                    disabled_tooltip.widget_type = widget_type
                    self.disabled_tooltips.append(disabled_tooltip)

        def create_dual_param_entry(parent, text1, var_key1, text2, var_key2, dependent_list=None, widget_type=None):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

            left_frame = Frame(frame, bg=parent.cget('bg'))
            left_frame.pack(side='left', fill='x', expand=True)

            label1 = Label(left_frame, text=text1, font=(FONT_FAMILY, 9), bg=parent.cget('bg'), fg=TEXT_COLOR, width=18,
                           anchor='w')
            label1.pack(side='left')

            tooltip_text1 = self.dig_tool.settings_manager.get_description(var_key1)
            Tooltip(label1, tooltip_text1)

            default_value1 = self.dig_tool.settings_manager.get_default_value(var_key1)
            var_type1 = self.dig_tool.settings_manager.get_param_type(var_key1)

            if var_key1 not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key1] = var_type1(value=default_value1)
                self.dig_tool.last_known_good_params[var_key1] = default_value1

            if var_type1 != tk.BooleanVar:
                vcmd1 = (self.dig_tool.root.register(lambda value, key=var_key1: self.validate_param_entry(key, value)), '%P')
                entry1 = tk.Entry(left_frame, textvariable=self.dig_tool.param_vars[var_key1], font=(FONT_FAMILY, 9),
                                  bg=FRAME_BG, fg=TEXT_COLOR, relief='solid', width=12, borderwidth=1,
                                  validate='focusout', validatecommand=vcmd1)
                entry1.pack(side='right', ipady=3, padx=(4, 8))
                if dependent_list is not None: dependent_list.append(entry1)
                if widget_type:
                    disabled_tooltip = DisabledTooltip(entry1, "", tooltip_text1)
                    disabled_tooltip.widget_type = widget_type
                    self.disabled_tooltips.append(disabled_tooltip)

            right_frame = Frame(frame, bg=parent.cget('bg'))
            right_frame.pack(side='right', fill='x', expand=True)

            label2 = Label(right_frame, text=text2, font=(FONT_FAMILY, 9), bg=parent.cget('bg'), fg=TEXT_COLOR,
                           width=18, anchor='w')
            label2.pack(side='left')

            tooltip_text2 = self.dig_tool.settings_manager.get_description(var_key2)
            Tooltip(label2, tooltip_text2)

            default_value2 = self.dig_tool.settings_manager.get_default_value(var_key2)
            var_type2 = self.dig_tool.settings_manager.get_param_type(var_key2)

            if var_key2 not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key2] = var_type2(value=default_value2)
                self.dig_tool.last_known_good_params[var_key2] = default_value2

            if var_type2 != tk.BooleanVar:
                vcmd2 = (self.dig_tool.root.register(lambda value, key=var_key2: self.validate_param_entry(key, value)), '%P')
                entry2 = tk.Entry(right_frame, textvariable=self.dig_tool.param_vars[var_key2], font=(FONT_FAMILY, 9),
                                  bg=FRAME_BG, fg=TEXT_COLOR, relief='solid', width=12, borderwidth=1,
                                  validate='focusout', validatecommand=vcmd2)
                entry2.pack(side='right', ipady=3)
                if dependent_list is not None: dependent_list.append(entry2)
                if widget_type:
                    disabled_tooltip = DisabledTooltip(entry2, "", tooltip_text2)
                    disabled_tooltip.widget_type = widget_type
                    self.disabled_tooltips.append(disabled_tooltip)

        def create_checkbox_param(parent, text, var_key, dependent_list=None, widget_type=None,
                                  validation_callback=None):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

            default_value = self.dig_tool.settings_manager.get_default_value(var_key)
            if var_key not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key] = tk.BooleanVar(value=default_value)
                self.dig_tool.last_known_good_params[var_key] = default_value

            check = Checkbutton(frame, text=text, variable=self.dig_tool.param_vars[var_key], bg=parent.cget('bg'),
                                fg=TEXT_COLOR,
                                selectcolor=BG_COLOR, activebackground=parent.cget('bg'), activeforeground=TEXT_COLOR,
                                font=(FONT_FAMILY, 9), anchor='w')
            check.pack(anchor='w', fill='x')

            tooltip_text = self.dig_tool.settings_manager.get_description(var_key)

            if widget_type:
                disabled_tooltip = DisabledTooltip(check, "", tooltip_text)
                disabled_tooltip.widget_type = widget_type
                self.disabled_tooltips.append(disabled_tooltip)
            else:
                Tooltip(check, tooltip_text)

            if validation_callback: self.dig_tool.param_vars[var_key].trace_add('write', validation_callback)
            if dependent_list is not None: dependent_list.append(check)

            return check

        def create_dropdown_param(parent, text, var_key, values, dependent_list=None, widget_type=None):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

            label = Label(frame, text=text, font=(FONT_FAMILY, 9), bg=parent.cget('bg'), fg=TEXT_COLOR,
                          width=LABEL_WIDTH, anchor='w')
            label.pack(side='left')

            tooltip_text = self.dig_tool.settings_manager.get_description(var_key)
            Tooltip(label, tooltip_text)

            default_value = self.dig_tool.settings_manager.get_default_value(var_key)
            if var_key not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key] = tk.StringVar(value=default_value)
                self.dig_tool.last_known_good_params[var_key] = default_value

            combo = ttk.Combobox(frame, textvariable=self.dig_tool.param_vars[var_key], values=values, state="readonly",
                                 width=ENTRY_WIDTH - 2, font=(FONT_FAMILY, 9))
            combo.pack(side='right', ipady=3)

            if dependent_list is not None: dependent_list.append(combo)
            if widget_type:
                disabled_tooltip = DisabledTooltip(combo, "", tooltip_text)
                disabled_tooltip.widget_type = widget_type
                self.disabled_tooltips.append(disabled_tooltip)

            return combo

        def create_section_button(parent, text, command, dependent_list=None, widget_type=None):
            btn_frame = Frame(parent, bg=parent.cget('bg'))
            btn_frame.pack(fill='x', pady=BUTTON_PADY, padx=PARAM_PADX)
            btn = Button(btn_frame, text=text, command=command, font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR,
                         relief='solid', borderwidth=1, pady=4)
            btn.pack(expand=True, fill=tk.X)

            if dependent_list is not None: dependent_list.append(btn)
            if widget_type:
                disabled_tooltip = DisabledTooltip(btn, "", f"Test button for {text.lower()}")
                disabled_tooltip.widget_type = widget_type
                self.disabled_tooltips.append(disabled_tooltip)

            return btn

        create_dual_param_entry(panes['detection'].sub_frame, "Line Sensitivity:", 'line_sensitivity',
                                "Line Detection Offset:", 'line_detection_offset')
        create_dual_param_entry(panes['detection'].sub_frame, "Zone Min Width:", 'zone_min_width',
                                "Zone Max Width (%):", 'max_zone_width_percent')
        create_dual_param_entry(panes['detection'].sub_frame, "Zone Min Height (%):", 'min_zone_height_percent',
                                "Saturation Threshold:", 'saturation_threshold')

        create_param_entry(panes['behavior'].sub_frame, "Zone Smoothing:", 'zone_smoothing_factor')
        create_param_entry(panes['behavior'].sub_frame, "Target Width (%):", 'sweet_spot_width_percent')
        create_param_entry(panes['behavior'].sub_frame, "Line Exclusion Radius:", 'line_exclusion_radius')
        create_param_entry(panes['behavior'].sub_frame, "Post-Click Blindness (ms):", 'post_click_blindness')

        pred_subsection = CollapsibleSubsection(panes['behavior'].sub_frame, "Prediction Settings",
                                                "#e8f5e8")  # Light green for predictions
        create_checkbox_param(pred_subsection.content, "Enable Prediction", 'prediction_enabled')
        create_param_entry(pred_subsection.content, "System Latency (ms):", 'system_latency')
        
        # Manual latency measurement button
        latency_button_frame = Frame(pred_subsection.content)
        latency_button_frame.pack(fill='x', pady=2)
        
        latency_measure_btn = ttk.Button(latency_button_frame, text="Measure Latency", 
                                        command=lambda: self.dig_tool.manual_latency_measurement())
        latency_measure_btn.pack(side='left', padx=(0, 5))
        
        Tooltip(latency_measure_btn, "Manually measure system latency. This will test your system's input/display latency and update the System Latency setting.")
        
        self.latency_status_label = Label(latency_button_frame, text="", fg='gray', font=('Segoe UI', 8))
        self.latency_status_label.pack(side='left', padx=(5, 0))
        
        create_param_entry(pred_subsection.content, "Game FPS:", 'target_fps')
        create_param_entry(pred_subsection.content, "Prediction Confidence:", 'prediction_confidence_threshold')

        walk_subsection = CollapsibleSubsection(panes['behavior'].sub_frame, "Auto-Walk Settings",
                                                "#e8f0ff")  # Light blue for auto-walk
        auto_walk_check = create_checkbox_param(walk_subsection.content, "Enable Auto-Walk", 'auto_walk_enabled')
        create_param_entry(walk_subsection.content, "Walk Duration (ms):", 'walk_duration')

        pattern_frame = Frame(walk_subsection.content, bg="#e8f0ff")  # Light blue background
        pattern_frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

        Label(pattern_frame, text="Walk Pattern:", font=(FONT_FAMILY, 9), bg="#e8f0ff", fg=TEXT_COLOR,
              width=LABEL_WIDTH, anchor='w').pack(side='left')

        self.dig_tool.walk_pattern_var = tk.StringVar(value="circle")
        self.walk_pattern_combo = ttk.Combobox(pattern_frame, textvariable=self.dig_tool.walk_pattern_var,
                                               values=list(self.dig_tool.automation_manager.get_pattern_list().keys()),
                                               state="readonly", width=ENTRY_WIDTH, font=(FONT_FAMILY, 9))
        self.walk_pattern_combo.pack(side='right', ipady=3)

        custom_pattern_frame = Frame(walk_subsection.content, bg="#e8f0ff")  # Light blue background
        custom_pattern_frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

        custom_pattern_btn = Button(custom_pattern_frame, text="Manage Custom Patterns",
                                    command=self.dig_tool.open_custom_pattern_manager,
                                    font=(FONT_FAMILY, 9), bg="#4CAF50", fg="white", relief='solid', borderwidth=1,
                                    pady=4)  # Green button
        custom_pattern_btn.pack(side='left', expand=True, fill='x', padx=(0, 2))

        refresh_pattern_btn = Button(custom_pattern_frame, text="Refresh Patterns",
                                     command=self.dig_tool.settings_manager.refresh_pattern_dropdown,
                                     font=(FONT_FAMILY, 9), bg="#2196F3", fg="white", relief='solid', borderwidth=1,
                                     pady=4)  # Blue button
        refresh_pattern_btn.pack(side='left', expand=True, fill='x', padx=2)

        shovel_subsection = CollapsibleSubsection(panes['behavior'].sub_frame, "Shovel Management",
                                                  "#ffe8e8")  # Light red for shovel management
        self.auto_shovel_checkbox = create_checkbox_param(shovel_subsection.content, "Enable Auto-Shovel",
                                                          'auto_shovel_enabled', widget_type='shovel')
        create_dual_param_entry(shovel_subsection.content, "Shovel Slot (0-9):", 'shovel_slot', "Timeout (minutes):",
                                'shovel_timeout',
                                self.shovel_dependent_widgets, 'shovel')

        create_dropdown_param(shovel_subsection.content, "Equip Mode:", 'shovel_equip_mode', ["single", "double"],
                              self.shovel_dependent_widgets, 'shovel')

        create_section_button(shovel_subsection.content, "Test Shovel Equip",
                              self.dig_tool.automation_manager.test_shovel_equip,
                              self.shovel_dependent_widgets, 'shovel')

        cursor_subsection = CollapsibleSubsection(panes['behavior'].sub_frame, "Cursor Settings",
                                                  "#fff0e8")  # Light orange for cursor settings
        self.use_cursor_checkbox = create_checkbox_param(cursor_subsection.content, "Use Custom Cursor Position",
                                                         'use_custom_cursor',
                                                         widget_type='cursor',
                                                         validation_callback=self.validate_cursor_position_toggle)

        self.auto_sell_checkbox = create_checkbox_param(panes['auto_sell'].sub_frame, "Enable Auto-Sell",
                                                        'auto_sell_enabled',
                                                        widget_type='sell',
                                                        validation_callback=self.validate_auto_sell_toggle)
        create_dual_param_entry(panes['auto_sell'].sub_frame, "Sell Every X Digs:", 'sell_every_x_digs',
                                "Sell Delay (ms):", 'sell_delay',
                                self.sell_dependent_widgets, 'sell')

        create_param_entry(panes['discord'].sub_frame, "Discord User ID:", 'user_id')
        create_param_entry(panes['discord'].sub_frame, "Discord Webhook URL:", 'webhook_url')
        create_param_entry(panes['discord'].sub_frame, "Milestone Interval:", 'milestone_interval')
        create_checkbox_param(panes['discord'].sub_frame, "Include Screenshot in Discord Notifications",
                              'include_screenshot_in_discord')
        create_section_button(panes['discord'].sub_frame, "Test Discord Ping", self.dig_tool.test_discord_ping)

        create_checkbox_param(panes['window'].sub_frame, "Main Window Always on Top", 'main_on_top')
        self.dig_tool.param_vars['main_on_top'].trace_add('write', self.dig_tool.toggle_main_on_top)
        create_checkbox_param(panes['window'].sub_frame, "Preview Window Always on Top", 'preview_on_top')
        self.dig_tool.param_vars['preview_on_top'].trace_add('write', self.dig_tool.toggle_preview_on_top)
        create_checkbox_param(panes['window'].sub_frame, "Debug Window Always on Top", 'debug_on_top')
        self.dig_tool.param_vars['debug_on_top'].trace_add('write', self.dig_tool.toggle_debug_on_top)

        create_checkbox_param(panes['debug'].sub_frame, "Save Debug Screenshots", 'debug_clicks_enabled')
        create_param_entry(panes['debug'].sub_frame, "Screenshot FPS:", 'screenshot_fps')
        create_dropdown_param(panes['debug'].sub_frame, "Click Method:", 'click_method', ["win32api", "ahk"])
        create_section_button(panes['debug'].sub_frame, "Show Debug Console", self.dig_tool.show_debug_console)
        create_section_button(panes['debug'].sub_frame, "Test Sell Click", self.dig_tool.test_sell_button_click)
        create_section_button(panes['debug'].sub_frame, "Test Click Method", self.test_click_method)

        def create_hotkey_setter(parent, text, key_name):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=BUTTON_PADY, padx=PARAM_PADX)

            label = Label(frame, text=text, font=(FONT_FAMILY, 10), bg=parent.cget('bg'), fg=TEXT_COLOR, width=18,
                          anchor='w')
            label.pack(side='left')

            tooltip_text = self.dig_tool.settings_manager.get_keybind_description(key_name)
            Tooltip(label, tooltip_text)

            default_value = self.dig_tool.settings_manager.get_default_keybind(key_name)
            
            if key_name not in self.dig_tool.keybind_vars:
                self.dig_tool.keybind_vars[key_name] = tk.StringVar(value=default_value)
            
            key_var = self.dig_tool.keybind_vars[key_name]

            def set_hotkey_thread(key_var, button):
                button.config(text="Press any key...", state=tk.DISABLED, bg="#0078D4",
                              fg="#ffffff")
                self.dig_tool.root.update_idletasks()
                try:
                    import keyboard
                    event = keyboard.read_event(suppress=True)
                    if event.event_type == keyboard.KEY_DOWN: 
                        new_key = event.name
                        if new_key and new_key.strip():
                            key_var.set(new_key)
                        else:
                            key_var.set(default_value)
                except Exception as e:
                    self.dig_tool.update_status(f"Hotkey capture failed: {e}")
                    key_var.set(default_value)
                finally:
                    current_key = key_var.get()
                    if not current_key or current_key.strip() == "":
                        key_var.set(default_value)
                    button.config(text=key_var.get().upper(), state=tk.NORMAL, bg=BTN_BG, fg=TEXT_COLOR)
                    self.dig_tool.apply_keybinds()

            hotkey_btn = Button(frame, text=key_var.get().upper(), font=(FONT_FAMILY, 10, 'bold'), bg=BTN_BG,
                                fg=TEXT_COLOR, relief='solid', borderwidth=1, width=12, pady=4)
            hotkey_btn.config(command=lambda v=key_var, b=hotkey_btn:
            __import__('threading').Thread(target=set_hotkey_thread, args=(v, b), daemon=True).start())
            hotkey_btn.pack(side='right')

        create_hotkey_setter(panes['hotkeys'].sub_frame, "Toggle Bot:", 'toggle_bot')
        create_hotkey_setter(panes['hotkeys'].sub_frame, "Toggle GUI:", 'toggle_gui')
        create_hotkey_setter(panes['hotkeys'].sub_frame, "Toggle Overlay:", 'toggle_overlay')

        create_checkbox_param(panes['settings'].sub_frame, "Include Discord Info in Settings",
                              'include_discord_in_settings')

        save_load_frame = Frame(panes['settings'].sub_frame, bg=panes['settings'].sub_frame.cget('bg'))
        save_load_frame.pack(fill='x', pady=(BUTTON_PADY, 4), padx=PARAM_PADX)

        Button(save_load_frame, text="Save Settings", command=self.dig_tool.settings_manager.save_settings,
               font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR, relief='solid', borderwidth=1, pady=4).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        Button(save_load_frame, text="Load Settings", command=self.dig_tool.settings_manager.load_settings,
               font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR, relief='solid', borderwidth=1, pady=4).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        reset_frame = Frame(panes['settings'].sub_frame, bg=panes['settings'].sub_frame.cget('bg'))
        reset_frame.pack(fill='x', pady=(4, BUTTON_PADY), padx=PARAM_PADX)
        Button(reset_frame, text="Reset to Defaults", command=self.dig_tool.settings_manager.reset_to_defaults,
               font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR, relief='solid', borderwidth=1, pady=4).pack(expand=True,
                                                                                                            fill=tk.X)

        self.dig_tool.param_vars['auto_walk_enabled'].trace_add('write', self.update_dependent_widgets_state)
        self.dig_tool.param_vars['auto_shovel_enabled'].trace_add('write', self.update_dependent_widgets_state)
        self.dig_tool.param_vars['auto_sell_enabled'].trace_add('write', self.update_dependent_widgets_state)
        self.dig_tool.param_vars['use_custom_cursor'].trace_add('write', self.update_dependent_widgets_state)

        self.update_dependent_widgets_state()

        self.dig_tool.update_main_button_text()
        self.dig_tool.toggle_main_on_top()
        self.dig_tool.update_area_info()
        self.dig_tool.update_sell_info()
        self.dig_tool.update_cursor_info()
