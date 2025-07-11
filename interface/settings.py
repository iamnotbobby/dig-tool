import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk


class SettingsManager:
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance

        self.default_params = {
            'line_sensitivity': 50,
            'line_min_height': 100,
            'zone_min_width': 100,
            'saturation_threshold': 0.5,
            'min_zone_height_percent': 100,
            'sweet_spot_width_percent': 10,
            'prediction_enabled': True,
            'system_latency': 0,
            'max_prediction_time': 50,
            'min_velocity_threshold': 300,
            'prediction_confidence_threshold': 0.8,
            'zone_smoothing_factor': 0.8,
            'post_click_blindness': 50,
            'max_zone_width_percent': 80,
            'main_on_top': True,
            'preview_on_top': True,
            'debug_on_top': True,
            'debug_clicks_enabled': False,
            'auto_sell_enabled': False,
            'sell_every_x_digs': 10,
            'sell_delay': 3000,
            'auto_walk_enabled': False,
            'walk_duration': 500,
            'user_id': '',
            'webhook_url': '',
            'milestone_interval': 100,
            'use_custom_cursor': False,
            'include_discord_in_settings': False
        }

        self.param_descriptions = {
            'line_sensitivity': "How sharp the contrast must be to be considered a line. Higher values = less sensitive to weak edges.",
            'line_min_height': "The line must span this percentage of the capture height to be considered valid. 100% = full height required.",
            'zone_min_width': "The minimum pixel width for a valid target zone. Smaller zones will be ignored.",
            'max_zone_width_percent': "The maximum width of a target zone as a percent of the capture width. Prevents detecting overly large areas.",
            'min_zone_height_percent': "A target zone must span this percentage of the capture height to be valid. 100% = full height required.",
            'saturation_threshold': "How colorful a pixel must be to be part of the initial target zone search. Higher = more colorful required.",
            'zone_smoothing_factor': "How much to smooth the movement of the target zone. 1.0 = no smoothing, lower = more smoothing.",
            'sweet_spot_width_percent': "The width of the clickable 'sweet spot' in the middle of the zone. Smaller = more precise clicking required.",
            'post_click_blindness': "How long to wait after clicking before scanning again (milliseconds). Prevents multiple rapid clicks.",
            'prediction_enabled': "Predicts the line's movement to click earlier, compensating for input/display latency.",
            'system_latency': "Your system's input/display latency in milliseconds. Used for prediction timing compensation.",
            'max_prediction_time': "The maximum time in the future the bot is allowed to predict a click (milliseconds).",
            'min_velocity_threshold': "Minimum velocity required for prediction (pixels per second). Prevents prediction on slow/stationary lines.",
            'prediction_confidence_threshold': "How confident the prediction must be (0.0-1.0). Higher = more conservative prediction.",
            'main_on_top': "Keep the main window always on top of other windows.",
            'preview_on_top': "Keep the preview window always on top of other windows.",
            'debug_on_top': "Keep the debug window always on top of other windows.",
            'debug_clicks_enabled': "Save screenshots and debug information for every click performed.",
            'auto_sell_enabled': "Automatically sell items after a certain number of digs.",
            'sell_every_x_digs': "Number of digs before auto-selling items.",
            'sell_delay': "Delay in milliseconds before clicking the sell button.",
            'auto_walk_enabled': "Automatically move around while digging.",
            'walk_duration': "How long to hold movement keys (milliseconds).",
            'user_id': "Discord user ID for notifications (optional - leave blank for no ping).",
            'webhook_url': "Discord webhook URL for sending notifications.",
            'milestone_interval': "Send Discord notification every X digs (milestone notifications).",
            'use_custom_cursor': "Move cursor to set position before clicking when enabled. Cannot be used with Auto-Walk.",
            'include_discord_in_settings': "When enabled, Discord webhook and user ID will be included in regular settings files. When disabled, they are excluded for security."
        }

        self.default_keybinds = {
            'toggle_bot': 'f1',
            'toggle_gui': 'f2',
            'toggle_overlay': 'f3'
        }

        self.keybind_descriptions = {
            'toggle_bot': "Start/stop the clicking detection and automation.",
            'toggle_gui': "Show/hide the main control window.",
            'toggle_overlay': "Toggle the game overlay display on/off."
        }

    def get_default_value(self, key):
        return self.default_params.get(key)

    def get_default_keybind(self, key):
        return self.default_keybinds.get(key)

    def get_param_type(self, key):
        default_value = self.get_default_value(key)
        if isinstance(default_value, bool):
            return tk.BooleanVar
        elif isinstance(default_value, float):
            return tk.DoubleVar
        elif isinstance(default_value, int):
            return tk.IntVar
        else:
            return tk.StringVar

    def get_description(self, key):
        return self.param_descriptions.get(key, "No description available.")

    def get_keybind_description(self, key):
        return self.keybind_descriptions.get(key, "No description available.")

    def load_icon(self, icon_path, size=(32, 32)):
        try:
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                img = img.resize(size, Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error loading icon from {icon_path}: {e}")
        return None

    def get_conflict_tooltip(self, setting_key):
        """Get conflict tooltip text for disabled settings"""
        if setting_key == 'use_custom_cursor':
            return "DISABLED: Cannot use Custom Cursor while Auto-Walk is enabled. Disable Auto-Walk first."
        elif setting_key == 'auto_walk_enabled':
            return "DISABLED: Cannot use Auto-Walk while Custom Cursor is enabled. Disable Custom Cursor first."
        return ""

    def is_setting_conflicted(self, setting_key):
        """Check if a setting should be disabled due to conflicts"""
        if setting_key == 'use_custom_cursor':
            return self.dig_tool.param_vars.get('auto_walk_enabled', tk.BooleanVar()).get()
        elif setting_key == 'auto_walk_enabled':
            return self.dig_tool.param_vars.get('use_custom_cursor', tk.BooleanVar()).get()
        return False

    def update_setting_states(self):
        """Update the enabled/disabled state of conflicting settings"""
        conflicting_settings = ['use_custom_cursor', 'auto_walk_enabled']

        for setting_key in conflicting_settings:
            if hasattr(self.dig_tool, 'setting_widgets') and setting_key in self.dig_tool.setting_widgets:
                widget = self.dig_tool.setting_widgets[setting_key]
                is_conflicted = self.is_setting_conflicted(setting_key)

                if is_conflicted:
                    widget.config(state='disabled', fg='#808080')
                else:
                    widget.config(state='normal', fg='#000000')

    def get_param(self, key):
        try:
            if key in self.dig_tool.param_vars:
                value = self.dig_tool.param_vars[key].get()
                self.dig_tool.last_known_good_params[key] = value

                if key == 'milestone_interval':
                    self.dig_tool.milestone_interval = max(1, value)

                if key in ['use_custom_cursor', 'auto_walk_enabled']:
                    self.update_setting_states()

                return value
            else:
                return self.default_params.get(key, 0)
        except (tk.TclError, ValueError, AttributeError):
            self.dig_tool.update_status(f"Error: Invalid value for '{key}'. Using last known good value.")
            if key in self.dig_tool.last_known_good_params:
                return self.dig_tool.last_known_good_params[key]
            return self.default_params.get(key, 0)

    def validate_game_area(self, area):
        if not area or not isinstance(area, (list, tuple)) or len(area) != 4:
            return False
        try:
            x1, y1, x2, y2 = area
            return (isinstance(x1, (int, float)) and isinstance(y1, (int, float)) and
                    isinstance(x2, (int, float)) and isinstance(y2, (int, float)) and
                    x2 > x1 and y2 > y1 and x1 >= 0 and y1 >= 0)
        except (ValueError, TypeError):
            return False

    def validate_position(self, position):
        if not position:
            return False
        try:
            if isinstance(position, (list, tuple)) and len(position) == 2:
                x, y = position
                return isinstance(x, (int, float)) and isinstance(y, (int, float)) and x >= 0 and y >= 0
        except (ValueError, TypeError):
            pass
        return False

    def validate_param_value(self, key, value):
        try:
            if key in ['line_sensitivity', 'line_min_height', 'zone_min_width', 'saturation_threshold',
                       'min_zone_height_percent', 'sweet_spot_width_percent', 'system_latency',
                       'max_prediction_time', 'post_click_blindness', 'max_zone_width_percent',
                       'min_velocity_threshold', 'sell_every_x_digs', 'sell_delay', 'walk_duration',
                       'milestone_interval']:
                val = int(value)
                if key in ['line_min_height', 'min_zone_height_percent', 'sweet_spot_width_percent',
                           'max_zone_width_percent']:
                    return 0 <= val <= 100
                elif key in ['line_sensitivity', 'zone_min_width', 'saturation_threshold', 'system_latency',
                             'max_prediction_time', 'post_click_blindness', 'min_velocity_threshold',
                             'sell_every_x_digs', 'sell_delay', 'walk_duration', 'milestone_interval']:
                    return val >= 1 if key == 'milestone_interval' else val >= 0
                return True
            elif key in ['zone_smoothing_factor', 'prediction_confidence_threshold']:
                val = float(value)
                if key == 'zone_smoothing_factor':
                    return 0.0 <= val <= 2.0
                elif key == 'prediction_confidence_threshold':
                    return 0.0 <= val <= 1.0
                return True
            elif key in ['prediction_enabled', 'main_on_top', 'preview_on_top', 'debug_on_top',
                         'debug_clicks_enabled', 'auto_sell_enabled', 'auto_walk_enabled', 'use_custom_cursor',
                         'include_discord_in_settings']:
                return isinstance(value, bool)
            elif key in ['user_id', 'webhook_url']:
                return isinstance(value, str)
            return True
        except (ValueError, TypeError):
            return False

    def validate_keybind(self, key, value):
        if not isinstance(value, str) or len(value.strip()) == 0:
            return False
        return key in self.default_keybinds

    def save_settings(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".json",
                                                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                                                title="Save Settings As")
        if not filepath:
            return

        settings = {
            'params': {},
            'keybinds': {},
            'game_area': self.dig_tool.game_area,
            'sell_button_position': getattr(self.dig_tool.automation_manager, 'sell_button_position', None),
            'cursor_position': getattr(self.dig_tool, 'cursor_position', None),
            'walk_pattern': getattr(self.dig_tool, 'walk_pattern_var', tk.StringVar()).get() if hasattr(self.dig_tool,
                                                                                                        'walk_pattern_var') else 'circle'
        }

        include_discord = self.get_param('include_discord_in_settings')

        for key in self.default_params.keys():
            try:
                if key in self.dig_tool.param_vars:
                    value = self.dig_tool.param_vars[key].get()

                    if key in ['user_id', 'webhook_url'] and not include_discord:
                        settings['params'][key] = ''
                    else:
                        settings['params'][key] = value
                else:
                    settings['params'][key] = self.default_params[key]
            except Exception as e:
                print(f"Error saving parameter {key}: {e}")
                settings['params'][key] = self.default_params.get(key)

        for key in self.default_keybinds.keys():
            try:
                if key in self.dig_tool.keybind_vars:
                    value = self.dig_tool.keybind_vars[key].get()
                    if self.validate_keybind(key, value):
                        settings['keybinds'][key] = value
                    else:
                        settings['keybinds'][key] = self.default_keybinds.get(key)
                else:
                    settings['keybinds'][key] = self.default_keybinds.get(key)
            except Exception as e:
                print(f"Error saving keybind {key}: {e}")
                settings['keybinds'][key] = self.default_keybinds.get(key)

        try:
            with open(filepath, 'w') as f:
                json.dump(settings, f, indent=4)

            discord_status = "included" if include_discord else "excluded"
            self.dig_tool.update_status(
                f"Settings saved to {os.path.basename(filepath)} (Discord info {discord_status})")
        except Exception as e:
            self.dig_tool.update_status(f"Error saving settings: {e}")

    def load_settings(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                                              title="Load Settings From")
        if not filepath:
            return

        try:
            with open(filepath, 'r') as f:
                settings = json.load(f)

            if not isinstance(settings, dict):
                self.dig_tool.update_status("Error: Invalid settings file format")
                return

            params_loaded = 0
            for key, value in settings.get('params', {}).items():
                if key in self.dig_tool.param_vars:
                    try:
                        param_var = self.dig_tool.param_vars[key]

                        if isinstance(param_var, tk.BooleanVar):
                            if isinstance(value, str):
                                converted_value = value.lower() in ('true', '1', 'yes', 'on')
                            else:
                                converted_value = bool(value)
                        elif isinstance(param_var, tk.DoubleVar):
                            converted_value = float(value)
                        elif isinstance(param_var, tk.IntVar):
                            converted_value = int(float(str(value).replace('JS:', '')))
                        else:
                            converted_value = str(value)

                        param_var.set(converted_value)
                        params_loaded += 1

                    except Exception as e:
                        print(f"Warning: Could not set parameter {key}: {e}")
                        self.dig_tool.update_status(f"Warning: Could not set parameter {key}")

            self.update_setting_states()

            keybinds_loaded = 0
            for key, value in settings.get('keybinds', {}).items():
                if key in self.dig_tool.keybind_vars and self.validate_keybind(key, value):
                    try:
                        self.dig_tool.keybind_vars[key].set(value)
                        keybinds_loaded += 1
                    except Exception as e:
                        print(f"Warning: Could not set keybind {key}: {e}")

            area_loaded = False
            if 'game_area' in settings and self.validate_game_area(settings['game_area']):
                self.dig_tool.game_area = tuple(settings['game_area']) if isinstance(settings['game_area'], list) else \
                settings['game_area']
                self.dig_tool.update_area_info()
                if hasattr(self.dig_tool, 'preview_btn'):
                    self.dig_tool.preview_btn.config(state=tk.NORMAL)
                if hasattr(self.dig_tool, 'debug_btn'):
                    self.dig_tool.debug_btn.config(state=tk.NORMAL)
                if not self.dig_tool.main_loop_thread or not self.dig_tool.main_loop_thread.is_alive():
                    self.dig_tool.start_threads()
                area_loaded = True

            sell_button_loaded = False
            if 'sell_button_position' in settings and self.validate_position(settings['sell_button_position']):
                try:
                    pos = settings['sell_button_position']
                    self.dig_tool.automation_manager.sell_button_position = tuple(pos)
                    self.dig_tool.update_sell_info()
                    sell_button_loaded = True
                except Exception as e:
                    print(f"Error loading sell button position: {e}")

            cursor_loaded = False
            if 'cursor_position' in settings and self.validate_position(settings['cursor_position']):
                try:
                    pos = settings['cursor_position']
                    self.dig_tool.cursor_position = tuple(pos)
                    self.dig_tool.update_cursor_info()
                    cursor_loaded = True
                except Exception as e:
                    print(f"Error loading cursor position: {e}")

            pattern_loaded = False
            if 'walk_pattern' in settings and hasattr(self.dig_tool, 'walk_pattern_var'):
                try:
                    pattern = settings['walk_pattern']
                    if hasattr(self.dig_tool.automation_manager,
                               'walk_patterns') and pattern in self.dig_tool.automation_manager.walk_patterns:
                        self.dig_tool.walk_pattern_var.set(pattern)
                        pattern_loaded = True
                except Exception as e:
                    print(f"Error loading walk pattern: {e}")

            self.dig_tool.apply_keybinds()

            status_parts = [f"Settings loaded from {os.path.basename(filepath)}"]
            if params_loaded > 0:
                status_parts.append(f"{params_loaded} parameters")
            if keybinds_loaded > 0:
                status_parts.append(f"{keybinds_loaded} keybinds")
            if area_loaded:
                status_parts.append("game area")
            if sell_button_loaded:
                status_parts.append("sell button")
            if cursor_loaded:
                status_parts.append("cursor position")
            if pattern_loaded:
                status_parts.append("walk pattern")

            self.dig_tool.update_status(f"{status_parts[0]} - {', '.join(status_parts[1:])}")

        except json.JSONDecodeError:
            self.dig_tool.update_status("Error: Invalid JSON file")
        except Exception as e:
            self.dig_tool.update_status(f"Error loading settings: {e}")

    def reset_to_defaults(self):
        for key, default_value in self.default_params.items():
            if key in self.dig_tool.param_vars:
                try:
                    self.dig_tool.param_vars[key].set(default_value)
                except Exception:
                    pass

        for key, default_value in self.default_keybinds.items():
            if key in self.dig_tool.keybind_vars:
                try:
                    self.dig_tool.keybind_vars[key].set(default_value)
                except Exception:
                    pass

        if hasattr(self.dig_tool, 'walk_pattern_var'):
            try:
                self.dig_tool.walk_pattern_var.set('circle')
            except Exception:
                pass

        self.dig_tool.apply_keybinds()
        self.dig_tool.update_status("Settings reset to defaults")
