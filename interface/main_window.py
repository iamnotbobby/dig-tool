import tkinter as tk
from tkinter import Label, Button, Frame, Checkbutton, TclError, ttk
from interface.components import CollapsiblePane, AccordionManager, Tooltip


class CollapsibleSubsection:
    def __init__(self, parent, title, bg_color="#f0f0f0"):
        self.parent = parent
        self.title = title
        self.bg_color = bg_color
        self.is_open = tk.BooleanVar(value=False)

        self.container = Frame(parent, bg=parent.cget('bg'))
        self.container.pack(fill='x', pady=(4, 2), padx=8)

        self.header = Frame(self.container, bg=bg_color, relief='raised', bd=1)
        self.header.pack(fill='x')

        self.toggle_btn = Button(self.header, text=f"▶ {title}", font=("Segoe UI", 9, 'bold'),
                                 bg=bg_color, fg="#333333", relief='flat', anchor='w',
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

    def create_ui(self):
        BG_COLOR = "#f0f0f0"  # Main background - light gray
        FRAME_BG = "#ffffff"  # Frame backgrounds - white
        TEXT_COLOR = "#000000"  # Primary text - black
        BTN_BG = "#e1e1e1"  # Button background - light gray
        FONT_FAMILY = "Segoe UI"  # Primary font

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
              fg=TEXT_COLOR).pack(
            pady=(0, 8), anchor='center')

        self.dig_tool.status_label = Label(self.dig_tool.controls_panel, text="Status: Select a game area to begin.",
                                           font=(FONT_FAMILY, 9), bg=BG_COLOR, fg=TEXT_COLOR, wraplength=780,
                                           justify='left')
        self.dig_tool.status_label.pack(fill=tk.X, pady=(0, 10), anchor='w')

        info_panel = Frame(self.dig_tool.controls_panel, bg=FRAME_BG, relief='solid', bd=1)
        info_panel.pack(fill=tk.X, pady=(0, 10), padx=2)

        info_header = Label(info_panel, text="Configuration Status", font=(FONT_FAMILY, 9, 'bold'),
                            bg=FRAME_BG, fg=TEXT_COLOR)
        info_header.pack(pady=(6, 4))

        # Status items - stacked vertically
        self.dig_tool.area_info_label = Label(info_panel, text="Game Area: Not set", font=(FONT_FAMILY, 8),
                                              bg=FRAME_BG, fg="#666666", anchor='w')
        self.dig_tool.area_info_label.pack(fill='x', padx=12, pady=2)

        self.dig_tool.sell_info_label = Label(info_panel, text="Sell Button: Not set", font=(FONT_FAMILY, 8),
                                              bg=FRAME_BG, fg="#666666", anchor='w')
        self.dig_tool.sell_info_label.pack(fill='x', padx=12, pady=2)

        self.dig_tool.cursor_info_label = Label(info_panel, text="Cursor Position: Not set", font=(FONT_FAMILY, 8),
                                                bg=FRAME_BG, fg="#666666", anchor='w')
        self.dig_tool.cursor_info_label.pack(fill='x', padx=12, pady=(2, 8))

        actions_frame = Frame(self.dig_tool.controls_panel, bg=BG_COLOR)
        actions_frame.pack(fill=tk.X, pady=(0, SECTION_PADY))

        button_style = {'font': (FONT_FAMILY, 9), 'bg': BTN_BG, 'fg': TEXT_COLOR, 'relief': 'solid', 'borderwidth': 1,
                        'pady': 6}

        for i, (text, command) in enumerate([
            ("Select Area", self.dig_tool.start_area_selection),
            ("Start", self.dig_tool.toggle_detection),
            ("Show/Hide", self.dig_tool.toggle_gui),
            ("Overlay", self.dig_tool.toggle_overlay)
        ]):
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

        for i, (text, command, attr) in enumerate([
            ("Set Sell Button", self.dig_tool.start_sell_button_selection, None),
            ("Set Cursor Pos", self.dig_tool.start_cursor_position_selection, None),
            ("Show Preview", self.dig_tool.toggle_preview_window, 'preview_btn'),
            ("Show Debug", self.dig_tool.toggle_debug_window, 'debug_btn')
        ]):
            btn = Button(actions_frame2, text=text, command=command, **button_style)
            if attr:
                setattr(self.dig_tool, attr, btn)
                btn.config(state=tk.DISABLED)
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0 if i == 0 else 2, 2 if i < 3 else 0))

        config_frame = Frame(self.dig_tool.controls_panel, bg=BG_COLOR)
        config_frame.pack(fill='x', expand=True, pady=(8, 0))

        style = ttk.Style()
        style.configure("Header.TButton", font=(FONT_FAMILY, 9, 'bold'), background="#dcdcdc", relief="flat")
        style.map("Header.TButton", background=[('active', '#c8c8c8')])

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

        def create_param_entry(parent, text, var_key):
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
                entry = tk.Entry(frame, textvariable=self.dig_tool.param_vars[var_key], font=(FONT_FAMILY, 9),
                                 bg=FRAME_BG, fg=TEXT_COLOR, relief='solid', width=ENTRY_WIDTH, borderwidth=1)
                entry.pack(side='right', ipady=3)

        def create_dual_param_entry(parent, text1, var_key1, text2, var_key2):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

            left_frame = Frame(frame, bg=parent.cget('bg'))
            left_frame.pack(side='left', fill='x', expand=True)

            label1 = Label(left_frame, text=text1, font=(FONT_FAMILY, 9), bg=parent.cget('bg'), fg=TEXT_COLOR,
                           width=18, anchor='w')
            label1.pack(side='left')

            tooltip_text1 = self.dig_tool.settings_manager.get_description(var_key1)
            Tooltip(label1, tooltip_text1)

            default_value1 = self.dig_tool.settings_manager.get_default_value(var_key1)
            var_type1 = self.dig_tool.settings_manager.get_param_type(var_key1)

            if var_key1 not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key1] = var_type1(value=default_value1)
                self.dig_tool.last_known_good_params[var_key1] = default_value1

            if var_type1 != tk.BooleanVar:
                entry1 = tk.Entry(left_frame, textvariable=self.dig_tool.param_vars[var_key1], font=(FONT_FAMILY, 9),
                                  bg=FRAME_BG, fg=TEXT_COLOR, relief='solid', width=12, borderwidth=1)
                entry1.pack(side='right', ipady=3, padx=(4, 8))

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
                entry2 = tk.Entry(right_frame, textvariable=self.dig_tool.param_vars[var_key2], font=(FONT_FAMILY, 9),
                                  bg=FRAME_BG, fg=TEXT_COLOR, relief='solid', width=12, borderwidth=1)
                entry2.pack(side='right', ipady=3)

        def create_checkbox_param(parent, text, var_key):
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
            Tooltip(check, tooltip_text)

            return check

        def create_section_button(parent, text, command):
            btn_frame = Frame(parent, bg=parent.cget('bg'))
            btn_frame.pack(fill='x', pady=BUTTON_PADY, padx=PARAM_PADX)
            Button(btn_frame, text=text, command=command, font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR,
                   relief='solid', borderwidth=1, pady=4).pack(expand=True, fill=tk.X)

        # Detection pane - Light blue background (#e8f4f8)
        create_dual_param_entry(panes['detection'].sub_frame, "Line Sensitivity:", 'line_sensitivity',
                                "Line Min Height (%):", 'line_min_height')
        create_dual_param_entry(panes['detection'].sub_frame, "Zone Min Width:", 'zone_min_width',
                                "Zone Max Width (%):", 'max_zone_width_percent')
        create_dual_param_entry(panes['detection'].sub_frame, "Zone Min Height (%):", 'min_zone_height_percent',
                                "Saturation Threshold:", 'saturation_threshold')

        # Behavior pane - White background with colored subsections
        create_param_entry(panes['behavior'].sub_frame, "Zone Smoothing:", 'zone_smoothing_factor')
        create_param_entry(panes['behavior'].sub_frame, "Target Width (%):", 'sweet_spot_width_percent')
        create_param_entry(panes['behavior'].sub_frame, "Post-Click Blindness (ms):", 'post_click_blindness')

        # Prediction subsection - Light green background (#e8f5e8)
        pred_subsection = CollapsibleSubsection(panes['behavior'].sub_frame, "Prediction Settings", "#e8f5e8")
        create_checkbox_param(pred_subsection.content, "Enable Prediction", 'prediction_enabled')
        create_param_entry(pred_subsection.content, "System Latency (ms):", 'system_latency')
        create_param_entry(pred_subsection.content, "Max Prediction (ms):", 'max_prediction_time')
        create_param_entry(pred_subsection.content, "Min Velocity:", 'min_velocity_threshold')
        create_param_entry(pred_subsection.content, "Prediction Confidence:", 'prediction_confidence_threshold')

        # Auto-walk subsection - Light blue background (#e8f0ff)
        walk_subsection = CollapsibleSubsection(panes['behavior'].sub_frame, "Auto-Walk Settings", "#e8f0ff")
        create_checkbox_param(walk_subsection.content, "Enable Auto-Walk", 'auto_walk_enabled')
        create_checkbox_param(walk_subsection.content, "Switch to Azerty Keyboard Layout",
                              'azerty_keyboard_layout')
        create_param_entry(walk_subsection.content, "Walk Duration (ms):", 'walk_duration')

        # Walk pattern selector
        pattern_frame = Frame(walk_subsection.content, bg="#e8f0ff")
        pattern_frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

        Label(pattern_frame, text="Walk Pattern:", font=(FONT_FAMILY, 9), bg="#e8f0ff", fg=TEXT_COLOR,
              width=LABEL_WIDTH, anchor='w').pack(side='left')

        self.dig_tool.walk_pattern_var = tk.StringVar(value="circle")
        pattern_combo = ttk.Combobox(pattern_frame, textvariable=self.dig_tool.walk_pattern_var,
                                     values=["circle", "figure_8", "random", "forward_back", "left_right"],
                                     state="readonly", width=ENTRY_WIDTH, font=(FONT_FAMILY, 9))
        pattern_combo.pack(side='right', ipady=3)

        # Cursor subsection - Light orange background (#fff0e8)
        cursor_subsection = CollapsibleSubsection(panes['behavior'].sub_frame, "Cursor Settings", "#fff0e8")
        create_checkbox_param(cursor_subsection.content, "Use Custom Cursor Position", 'use_custom_cursor')

        # Auto-Sell pane - Light yellow background (#fff8e8)
        create_checkbox_param(panes['auto_sell'].sub_frame, "Enable Auto-Sell", 'auto_sell_enabled')
        create_dual_param_entry(panes['auto_sell'].sub_frame, "Sell Every X Digs:", 'sell_every_x_digs',
                                "Sell Delay (ms):", 'sell_delay')

        # Discord pane - Light pink background (#f8e8f8)
        create_param_entry(panes['discord'].sub_frame, "Discord User ID:", 'user_id')
        create_param_entry(panes['discord'].sub_frame, "Discord Webhook URL:", 'webhook_url')
        create_param_entry(panes['discord'].sub_frame, "Milestone Interval:", 'milestone_interval')
        create_section_button(panes['discord'].sub_frame, "Test Discord Ping", self.dig_tool.test_discord_ping)

        # Window pane - Light orange background (#f8f0e8)
        create_checkbox_param(panes['window'].sub_frame, "Main Window Always on Top", 'main_on_top')
        self.dig_tool.param_vars['main_on_top'].trace_add('write', self.dig_tool.toggle_main_on_top)
        create_checkbox_param(panes['window'].sub_frame, "Preview Window Always on Top", 'preview_on_top')
        self.dig_tool.param_vars['preview_on_top'].trace_add('write', self.dig_tool.toggle_preview_on_top)
        create_checkbox_param(panes['window'].sub_frame, "Debug Window Always on Top", 'debug_on_top')
        self.dig_tool.param_vars['debug_on_top'].trace_add('write', self.dig_tool.toggle_debug_on_top)

        # Debug pane - Light red background (#f8e8e8)
        create_checkbox_param(panes['debug'].sub_frame, "Save Debug Screenshots", 'debug_clicks_enabled')
        create_section_button(panes['debug'].sub_frame, "Test Sell Click", self.dig_tool.test_sell_button_click)

        # Hotkeys pane - Light purple background (#e8e8f8)
        def create_hotkey_setter(parent, text, key_name):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=BUTTON_PADY, padx=PARAM_PADX)

            label = Label(frame, text=text, font=(FONT_FAMILY, 10), bg=parent.cget('bg'), fg=TEXT_COLOR,
                          width=18, anchor='w')
            label.pack(side='left')

            tooltip_text = self.dig_tool.settings_manager.get_keybind_description(key_name)
            Tooltip(label, tooltip_text)

            default_value = self.dig_tool.settings_manager.get_default_keybind(key_name)
            self.dig_tool.keybind_vars[key_name] = tk.StringVar(value=default_value)

            def set_hotkey_thread(key_var, button):
                button.config(text="Press any key...", state=tk.DISABLED, bg="#0078D4", fg="#ffffff")
                self.dig_tool.root.update_idletasks()
                try:
                    import keyboard
                    event = keyboard.read_event(suppress=True)
                    if event.event_type == keyboard.KEY_DOWN:
                        key_var.set(event.name)
                except Exception as e:
                    self.dig_tool.update_status(f"Hotkey capture failed: {e}")
                finally:
                    button.config(text=key_var.get().upper(), state=tk.NORMAL, bg=BTN_BG, fg=TEXT_COLOR)
                    self.dig_tool.apply_keybinds()

            hotkey_btn = Button(frame, text=default_value.upper(), font=(FONT_FAMILY, 10, 'bold'), bg=BTN_BG,
                                fg=TEXT_COLOR, relief='solid', borderwidth=1, width=12, pady=4)
            hotkey_btn.config(
                command=lambda v=self.dig_tool.keybind_vars[key_name], b=hotkey_btn: __import__('threading').Thread(
                    target=set_hotkey_thread,
                    args=(v, b),
                    daemon=True).start())
            hotkey_btn.pack(side='right')

        create_hotkey_setter(panes['hotkeys'].sub_frame, "Toggle Bot:", 'toggle_bot')
        create_hotkey_setter(panes['hotkeys'].sub_frame, "Toggle GUI:", 'toggle_gui')
        create_hotkey_setter(panes['hotkeys'].sub_frame, "Toggle Overlay:", 'toggle_overlay')

        # Settings pane - Light green background (#e8f8f0)
        create_checkbox_param(panes['settings'].sub_frame, "Include Discord Info in Settings",
                              'include_discord_in_settings')
        

        # Save/Load buttons
        save_load_frame = Frame(panes['settings'].sub_frame, bg=panes['settings'].sub_frame.cget('bg'))
        save_load_frame.pack(fill='x', pady=(BUTTON_PADY, 4), padx=PARAM_PADX)

        Button(save_load_frame, text="Save Settings", command=self.dig_tool.settings_manager.save_settings,
               font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR, relief='solid', borderwidth=1, pady=4).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        Button(save_load_frame, text="Load Settings", command=self.dig_tool.settings_manager.load_settings,
               font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR, relief='solid', borderwidth=1, pady=4).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # Reset button
        reset_frame = Frame(panes['settings'].sub_frame, bg=panes['settings'].sub_frame.cget('bg'))
        reset_frame.pack(fill='x', pady=(4, BUTTON_PADY), padx=PARAM_PADX)
        Button(reset_frame, text="Reset to Defaults", command=self.dig_tool.settings_manager.reset_to_defaults,
               font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR, relief='solid', borderwidth=1, pady=4).pack(
            expand=True, fill=tk.X)

        self.dig_tool.update_main_button_text()
        self.dig_tool.toggle_main_on_top()
        self.dig_tool.update_area_info()
        self.dig_tool.update_sell_info()
        self.dig_tool.update_cursor_info()