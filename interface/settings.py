import json
import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import threading
import time
from utils.debug_logger import logger

from interface.settings_feedback_window import SettingsFeedbackWindow


class SettingsManager:
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance

        self.default_params = {
            'line_sensitivity': 100,
            'zone_min_width': 100,
            'saturation_threshold': 0.5,
            'min_zone_height_percent': 100,
            'sweet_spot_width_percent': 15,
            'prediction_enabled': True,
            'system_latency': 'auto',
            'prediction_confidence_threshold': 0.6,
            'zone_smoothing_factor': 0.8,
            'line_exclusion_radius': 10,
            'post_click_blindness': 50,
            'max_zone_width_percent': 80,
            'target_fps': 120,
            'line_detection_offset': 5.0,
            'main_on_top': True,
            'preview_on_top': True,
            'debug_on_top': True,
            'debug_clicks_enabled': False,
            'screenshot_fps': 240,
            'auto_sell_enabled': False,
            'sell_every_x_digs': 10,
            'sell_delay': 3000,
            'auto_walk_enabled': False,
            'walk_duration': 500,
            'auto_shovel_enabled': False,
            'shovel_slot': 1,
            'shovel_timeout': 5,
            'user_id': '',
            'webhook_url': '',
            'milestone_interval': 100,
            'use_custom_cursor': False,
            'include_discord_in_settings': False,
            'shovel_equip_mode': 'double',
            'click_method': 'win32api',
            'include_screenshot_in_discord': False
        }

        self.param_descriptions = {
            'line_sensitivity': "How sharp the contrast must be to be considered a line. Higher values = less sensitive to weak edges.",
            'line_detection_offset': "Pixels to offset the detected line position. Positive = right, negative = left. Decimals allowed for precise positioning.",
            'zone_min_width': "The minimum pixel width for a valid target zone. Smaller zones will be ignored.",
            'max_zone_width_percent': "The maximum width of a target zone as a percent of the capture width. Prevents detecting overly large areas.",
            'min_zone_height_percent': "A target zone must span this percentage of the capture height to be valid. 100% = full height required.",
            'saturation_threshold': "How colorful a pixel must be to be part of the initial target zone search. Higher = more colorful required.",
            'zone_smoothing_factor': "How much to smooth the movement of the target zone. 1.0 = no smoothing, lower = more smoothing.",
            'line_exclusion_radius': "Radius around detected line to exclude from zone detection. Prevents moving line from interfering with zone boundaries.",
            'sweet_spot_width_percent': "The width of the clickable 'sweet spot' in the middle of the zone. Smaller = more precise clicking required.",
            'post_click_blindness': "How long to wait after clicking before scanning again (milliseconds). Prevents multiple rapid clicks.",
            'prediction_enabled': "Predicts the line's movement to click earlier, compensating for input/display latency.",
            'system_latency': "Your system's input/display latency in milliseconds. Set to 'auto' for automatic measurement at startup, or enter a custom value. Use the 'Measure Latency' button to manually measure.",
            'prediction_confidence_threshold': "How confident the prediction must be (0.0-1.0). Higher = more conservative prediction.",
            'main_on_top': "Keep the main window always on top of other windows.",
            'preview_on_top': "Keep the preview window always on top of other windows.",
            'debug_on_top': "Keep the debug window always on top of other windows.",
            'debug_clicks_enabled': "Save screenshots and debug information for every click performed.",
            'screenshot_fps': "Target frames per second for screenshot capture. Higher = lower latency but more CPU usage.",
            'auto_sell_enabled': "Automatically sell items after a certain number of digs.",
            'sell_every_x_digs': "Number of digs before auto-selling items.",
            'sell_delay': "Delay in milliseconds before clicking the sell button.",
            'auto_walk_enabled': "Automatically move around while digging.",
            'walk_duration': "How long to hold movement keys (milliseconds).",
            'user_id': "Discord user ID for notifications (optional - leave blank for no ping).",
            'webhook_url': "Discord webhook URL for sending notifications.",
            'auto_shovel_enabled': "Automatically re-equip shovel when no activity detected for specified time.",
            'shovel_slot': "Hotbar slot number (0-9) where your shovel is located. 0 = slot 10.",
            'shovel_timeout': "Minutes of inactivity before auto-equipping shovel (based on clicks, digs, and target detection).",
            'milestone_interval': "Send Discord notification every X digs (milestone notifications).",
            'target_fps': "Your game's FPS for prediction calculations. Higher FPS = more precise predictions. Does not affect screenshot rate.",
            'use_custom_cursor': "Move cursor to set position before clicking when enabled. Cannot be used with Auto-Walk.",
            'include_discord_in_settings': "When enabled, Discord webhook and user ID will be included in regular settings files. When disabled, they are excluded for security.",
            'shovel_equip_mode': "Whether to press the shovel slot key once ('single') or twice ('double') when re-equipping.",
            'click_method': "Method used for sending clicks: 'win32api' or 'ahk'.",
            'include_screenshot_in_discord': "When enabled, screenshots of your game will be included in Discord milestone notifications."
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
            logger.error(f"Error loading icon from {icon_path}: {e}")
        return None

    def get_conflict_tooltip(self, setting_key):
        if setting_key == 'use_custom_cursor':
            return "DISABLED: Cannot use Custom Cursor while Auto-Walk is enabled. Disable Auto-Walk first."
        elif setting_key == 'auto_walk_enabled':
            return "DISABLED: Cannot use Auto-Walk while Custom Cursor is enabled. Disable Custom Cursor first."
        return ""

    def is_setting_conflicted(self, setting_key):
        if setting_key == 'use_custom_cursor':
            return self.dig_tool.param_vars.get('auto_walk_enabled', tk.BooleanVar()).get()
        elif setting_key == 'auto_walk_enabled':
            return self.dig_tool.param_vars.get('use_custom_cursor', tk.BooleanVar()).get()
        return False

    def update_setting_states(self):
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
            if key == 'system_latency':
                if isinstance(value, str) and value.strip().lower() == 'auto':
                    return True
                val = int(value)
                return val >= 0
            elif key in ['line_sensitivity', 'zone_min_width', 'saturation_threshold',
                       'min_zone_height_percent', 'sweet_spot_width_percent',
                       'post_click_blindness', 'max_zone_width_percent',
                       'sell_every_x_digs', 'sell_delay', 'walk_duration',
                       'milestone_interval', 'target_fps', 'screenshot_fps']:
                val = int(value)
                if key in ['min_zone_height_percent', 'sweet_spot_width_percent',
                           'max_zone_width_percent']:
                    return 0 <= val <= 100
                elif key in ['line_sensitivity', 'zone_min_width', 'saturation_threshold',
                             'post_click_blindness',
                             'sell_every_x_digs', 'sell_delay', 'walk_duration', 'milestone_interval']:
                    return val >= 1 if key == 'milestone_interval' else val >= 0
                elif key == 'target_fps':
                    return 1 <= val <= 1000
                elif key == 'screenshot_fps':
                    return 30 <= val <= 500
                return True
            elif key in ['zone_smoothing_factor', 'prediction_confidence_threshold', 'line_detection_offset', 'line_exclusion_radius']:
                val = float(value)
                if key == 'zone_smoothing_factor':
                    return 0.0 <= val <= 2.0
                elif key == 'prediction_confidence_threshold':
                    return 0.0 <= val <= 1.0
                elif key == 'line_detection_offset':
                    return True  # Allow any float value (positive, negative, decimal)
                elif key == 'line_exclusion_radius':
                    return val >= 0  # Allow 0 to disable, positive values for radius
                return True
            elif key in ['prediction_enabled', 'main_on_top', 'preview_on_top', 'debug_on_top',
                         'debug_clicks_enabled', 'auto_sell_enabled', 'auto_walk_enabled', 'use_custom_cursor',
                         'auto_shovel_enabled', 'include_discord_in_settings']:
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

    def refresh_pattern_dropdown(self):
        if hasattr(self.dig_tool, 'update_walk_pattern_dropdown'):
            self.dig_tool.update_walk_pattern_dropdown()
            self.dig_tool.update_status("Pattern list refreshed!")

    def open_custom_pattern_manager(self):
        if hasattr(self.dig_tool, 'open_custom_pattern_manager'):
            self.dig_tool.open_custom_pattern_manager()

    def save_settings(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".json",
                                                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                                                title="Save Settings As")
        if not filepath:
            return

        feedback = SettingsFeedbackWindow(self.dig_tool.root, "Saving Settings")
        feedback.show_window()

        def save_process():
            try:
                feedback.update_progress(10, "Preparing settings data...")
                time.sleep(0.1)

                settings = {
                    'params': {},
                    'keybinds': {},
                    'game_area': self.dig_tool.game_area,
                    'sell_button_position': getattr(self.dig_tool.automation_manager, 'sell_button_position', None),
                    'cursor_position': getattr(self.dig_tool, 'cursor_position', None),
                    'walk_pattern': getattr(self.dig_tool, 'walk_pattern_var', tk.StringVar()).get() if hasattr(
                        self.dig_tool, 'walk_pattern_var') else 'circle'
                }

                include_discord = self.get_param('include_discord_in_settings')

                feedback.add_section("PARAMETERS")
                feedback.update_progress(20, "Processing parameters...")

                total_params = len(self.default_params)
                for i, key in enumerate(self.default_params.keys()):
                    try:
                        if key in self.dig_tool.param_vars:
                            value = self.dig_tool.param_vars[key].get()

                            if key in ['user_id', 'webhook_url'] and not include_discord:
                                settings['params'][key] = ''
                                feedback.add_change_entry(key, str(value), '(excluded)', 'warning')
                            else:
                                settings['params'][key] = value
                                feedback.add_change_entry(key, "", str(value), 'success')
                        else:
                            settings['params'][key] = self.default_params[key]
                            feedback.add_change_entry(key, "", str(self.default_params[key]), 'info')
                    except Exception as e:
                        settings['params'][key] = self.default_params.get(key)
                        feedback.add_change_entry(key, "", f"ERROR: {e}", 'error')

                    progress = 20 + (i * 30 / total_params)
                    feedback.update_progress(progress)
                    time.sleep(0.02)

                feedback.add_section("KEYBINDS")
                feedback.update_progress(50, "Processing keybinds...")

                total_keybinds = len(self.default_keybinds)
                for i, key in enumerate(self.default_keybinds.keys()):
                    try:
                        if key in self.dig_tool.keybind_vars:
                            value = self.dig_tool.keybind_vars[key].get()
                            if self.validate_keybind(key, value):
                                settings['keybinds'][key] = value
                                feedback.add_change_entry(key, "", value, 'success')
                            else:
                                settings['keybinds'][key] = self.default_keybinds.get(key)
                                feedback.add_change_entry(key, value, self.default_keybinds.get(key), 'warning')
                        else:
                            settings['keybinds'][key] = self.default_keybinds.get(key)
                            feedback.add_change_entry(key, "", self.default_keybinds.get(key), 'info')
                    except Exception as e:
                        settings['keybinds'][key] = self.default_keybinds.get(key)
                        feedback.add_change_entry(key, "", f"ERROR: {e}", 'error')

                    progress = 50 + (i * 20 / total_keybinds)
                    feedback.update_progress(progress)
                    time.sleep(0.02)

                feedback.add_section("CONFIGURATION")
                feedback.update_progress(70, "Processing configuration...")

                if self.dig_tool.game_area:
                    feedback.add_text(f"✓ Game Area: {self.dig_tool.game_area}", 'success')
                else:
                    feedback.add_text("✗ Game Area: Not set", 'warning')

                if hasattr(self.dig_tool.automation_manager,
                           'sell_button_position') and self.dig_tool.automation_manager.sell_button_position:
                    feedback.add_text(f"✓ Sell Button: {self.dig_tool.automation_manager.sell_button_position}",
                                      'success')
                else:
                    feedback.add_text("✗ Sell Button: Not set", 'warning')

                if hasattr(self.dig_tool, 'cursor_position') and self.dig_tool.cursor_position:
                    feedback.add_text(f"✓ Cursor Position: {self.dig_tool.cursor_position}", 'success')
                else:
                    feedback.add_text("✗ Cursor Position: Not set", 'warning')

                feedback.update_progress(85, "Writing file...")
                time.sleep(0.1)

                with open(filepath, 'w') as f:
                    json.dump(settings, f, indent=4)

                feedback.update_progress(95, "Finalizing...")
                time.sleep(0.1)

                discord_status = "included" if include_discord else "excluded"
                filename = os.path.basename(filepath)

                feedback.add_section("COMPLETION")
                feedback.add_text(f"✓ Settings saved to: {filename}", 'success')
                feedback.add_text(f"✓ Discord information: {discord_status}", 'info')

                feedback.operation_complete(success=True)

                self.dig_tool.update_status(f"Settings saved to {filename} (Discord info {discord_status})")

            except Exception as e:
                feedback.show_error("Save Failed", str(e))
                self.dig_tool.update_status(f"Error saving settings: {e}")

        threading.Thread(target=save_process, daemon=True).start()

    def load_settings(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                                              title="Load Settings From")
        if not filepath:
            return

        feedback = SettingsFeedbackWindow(self.dig_tool.root, "Loading Settings")
        feedback.show_window()

        def load_process():
            try:
                feedback.update_progress(10, "Reading settings file...")
                time.sleep(0.1)

                with open(filepath, 'r') as f:
                    settings = json.load(f)

                if not isinstance(settings, dict):
                    feedback.show_error("Invalid File", "Settings file format is invalid")
                    return

                feedback.update_progress(20, "Validating settings structure...")
                time.sleep(0.1)

                feedback.add_section("PARAMETERS")
                params_loaded = 0
                params_failed = []

                total_params = len(settings.get('params', {}))
                for i, (key, value) in enumerate(settings.get('params', {}).items()):
                    if key in self.dig_tool.param_vars:
                        try:
                            param_var = self.dig_tool.param_vars[key]
                            old_value = param_var.get()

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
                            feedback.add_change_entry(key, str(old_value), str(converted_value), 'success')
                            params_loaded += 1

                        except Exception as e:
                            feedback.add_change_entry(key, "", f"ERROR: {str(e)}", 'error')
                            params_failed.append(key)
                    else:
                        feedback.add_change_entry(key, "", "Unknown parameter", 'warning')
                        params_failed.append(key)

                    progress = 20 + (i * 30 / max(total_params, 1))
                    feedback.update_progress(progress)
                    time.sleep(0.02)

                self.update_setting_states()

                feedback.add_section("KEYBINDS")
                keybinds_loaded = 0
                keybinds_failed = []

                total_keybinds = len(settings.get('keybinds', {}))
                for i, (key, value) in enumerate(settings.get('keybinds', {}).items()):
                    if key in self.dig_tool.keybind_vars and self.validate_keybind(key, value):
                        try:
                            old_value = self.dig_tool.keybind_vars[key].get()
                            self.dig_tool.keybind_vars[key].set(value)
                            feedback.add_change_entry(key, old_value, value, 'success')
                            keybinds_loaded += 1
                        except Exception as e:
                            feedback.add_change_entry(key, "", f"ERROR: {str(e)}", 'error')
                            keybinds_failed.append(key)
                    else:
                        feedback.add_change_entry(key, "", "Invalid keybind", 'warning')
                        keybinds_failed.append(key)

                    progress = 50 + (i * 20 / max(total_keybinds, 1))
                    feedback.update_progress(progress)
                    time.sleep(0.02)

                feedback.add_section("CONFIGURATION")
                feedback.update_progress(70, "Loading configuration settings...")

                area_loaded = False
                if 'game_area' in settings and self.validate_game_area(settings['game_area']):
                    old_area = self.dig_tool.game_area
                    self.dig_tool.game_area = tuple(settings['game_area']) if isinstance(settings['game_area'],
                                                                                         list) else settings[
                        'game_area']

                    feedback.add_change_entry("Game Area", str(old_area) if old_area else "None",
                                              str(self.dig_tool.game_area), 'success')

                    self.dig_tool.update_area_info()
                    if hasattr(self.dig_tool, 'preview_btn'):
                        self.dig_tool.preview_btn.config(state=tk.NORMAL)
                    if hasattr(self.dig_tool, 'debug_btn'):
                        self.dig_tool.debug_btn.config(state=tk.NORMAL)
                    if not self.dig_tool.main_loop_thread or not self.dig_tool.main_loop_thread.is_alive():
                        self.dig_tool.start_threads()
                    area_loaded = True
                else:
                    feedback.add_text("✗ Game Area: Not found or invalid", 'warning')

                sell_button_loaded = False
                if 'sell_button_position' in settings and self.validate_position(settings['sell_button_position']):
                    try:
                        pos = settings['sell_button_position']
                        old_pos = getattr(self.dig_tool.automation_manager, 'sell_button_position', None)
                        self.dig_tool.automation_manager.sell_button_position = tuple(pos)

                        feedback.add_change_entry("Sell Button", str(old_pos) if old_pos else "None", str(tuple(pos)),
                                                  'success')

                        self.dig_tool.update_sell_info()
                        sell_button_loaded = True
                    except Exception:
                        feedback.add_text("✗ Sell Button: Invalid position data", 'warning')
                else:
                    feedback.add_text("✗ Sell Button: Not found", 'warning')

                cursor_loaded = False
                if 'cursor_position' in settings and self.validate_position(settings['cursor_position']):
                    try:
                        pos = settings['cursor_position']
                        old_pos = getattr(self.dig_tool, 'cursor_position', None)
                        self.dig_tool.cursor_position = tuple(pos)

                        feedback.add_change_entry("Cursor Position", str(old_pos) if old_pos else "None",
                                                  str(tuple(pos)), 'success')

                        self.dig_tool.update_cursor_info()
                        cursor_loaded = True
                    except Exception:
                        feedback.add_text("✗ Cursor Position: Invalid position data", 'warning')
                else:
                    feedback.add_text("✗ Cursor Position: Not found", 'warning')

                pattern_loaded = False
                if 'walk_pattern' in settings and hasattr(self.dig_tool, 'walk_pattern_var'):
                    try:
                        pattern = settings['walk_pattern']
                        old_pattern = self.dig_tool.walk_pattern_var.get()
                        if hasattr(self.dig_tool.automation_manager,
                                   'walk_patterns') and pattern in self.dig_tool.automation_manager.walk_patterns:
                            self.dig_tool.walk_pattern_var.set(pattern)
                            feedback.add_change_entry("Walk Pattern", old_pattern, pattern, 'success')
                            pattern_loaded = True
                        else:
                            feedback.add_text(f"✗ Walk Pattern: Unknown pattern '{pattern}'", 'warning')
                    except Exception:
                        feedback.add_text("✗ Walk Pattern: Invalid data", 'warning')
                else:
                    feedback.add_text("✗ Walk Pattern: Not found", 'warning')

                feedback.update_progress(90, "Finalizing...")

                self.dig_tool.apply_keybinds()

                if hasattr(self.dig_tool, 'update_walk_pattern_dropdown'):
                    self.dig_tool.update_walk_pattern_dropdown()

                total_failed = len(params_failed + keybinds_failed)
                total_success = params_loaded + keybinds_loaded
                total_items = total_success + total_failed

                feedback.add_summary_stats(total_success, total_failed, total_items)
                feedback.operation_complete(success=total_failed == 0)

                filename = os.path.basename(filepath)
                self.dig_tool.update_status(f"Settings loaded from {filename} - See details window")

            except json.JSONDecodeError:
                feedback.show_error("Invalid JSON", "The selected file contains invalid JSON data")
            except Exception as e:
                feedback.show_error("Load Failed", str(e))

        threading.Thread(target=load_process, daemon=True).start()

    def reset_to_defaults(self):
        feedback = SettingsFeedbackWindow(self.dig_tool.root, "Resetting to Defaults")
        feedback.show_window()

        def reset_process():
            try:
                feedback.update_progress(10, "Resetting parameters...")
                time.sleep(0.1)

                feedback.add_section("PARAMETERS")
                params_reset = 0
                total_params = len(self.default_params)

                for i, (key, default_value) in enumerate(self.default_params.items()):
                    if key in self.dig_tool.param_vars:
                        try:
                            old_value = self.dig_tool.param_vars[key].get()
                            self.dig_tool.param_vars[key].set(default_value)
                            feedback.add_change_entry(key, str(old_value), str(default_value), 'success')
                            params_reset += 1
                        except Exception as e:
                            feedback.add_change_entry(key, "", f"ERROR: {e}", 'error')

                    progress = 10 + (i * 40 / total_params)
                    feedback.update_progress(progress)
                    time.sleep(0.02)

                feedback.add_section("KEYBINDS")
                feedback.update_progress(50, "Resetting keybinds...")

                keybinds_reset = 0
                total_keybinds = len(self.default_keybinds)

                for i, (key, default_value) in enumerate(self.default_keybinds.items()):
                    if key in self.dig_tool.keybind_vars:
                        try:
                            old_value = self.dig_tool.keybind_vars[key].get()
                            self.dig_tool.keybind_vars[key].set(default_value)
                            feedback.add_change_entry(key, old_value, default_value, 'success')
                            keybinds_reset += 1
                        except Exception as e:
                            feedback.add_change_entry(key, "", f"ERROR: {e}", 'error')

                    progress = 50 + (i * 30 / total_keybinds)
                    feedback.update_progress(progress)
                    time.sleep(0.02)

                feedback.add_section("CONFIGURATION")
                feedback.update_progress(80, "Resetting configuration...")

                if hasattr(self.dig_tool, 'walk_pattern_var'):
                    try:
                        old_pattern = self.dig_tool.walk_pattern_var.get()
                        self.dig_tool.walk_pattern_var.set('circle')
                        feedback.add_change_entry("Walk Pattern", old_pattern, "circle", 'success')
                    except Exception:
                        feedback.add_text("✗ Walk Pattern: Reset failed", 'error')

                feedback.update_progress(90, "Finalizing...")

                if hasattr(self.dig_tool, 'update_walk_pattern_dropdown'):
                    self.dig_tool.update_walk_pattern_dropdown()

                self.dig_tool.apply_keybinds()

                feedback.add_summary_stats(params_reset + keybinds_reset, 0, params_reset + keybinds_reset)
                feedback.operation_complete(success=True)

                self.dig_tool.update_status("Settings reset to defaults - See details window")

            except Exception as e:
                feedback.show_error("Reset Failed", str(e))

        threading.Thread(target=reset_process, daemon=True).start()
