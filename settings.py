import json
import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk


class SettingsManager:
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance

        self.default_params = {
            'line_sensitivity': 50,
            'line_min_height': 100,
            'zone_min_width': 100,
            'saturation_threshold': 1.0,
            'min_zone_height_percent': 100,
            'sweet_spot_width_percent': 15,
            'prediction_enabled': True,
            'system_latency': 0,
            'max_prediction_time': 50,
            'min_velocity_threshold': 300,
            'prediction_confidence_threshold': 0.8,
            'zone_smoothing_factor': 0.8,
            'post_click_blindness': 10,
            'max_zone_width_percent': 30,
            'main_on_top': True,
            'preview_on_top': True,
            'debug_on_top': True,
            'debug_clicks_enabled': False
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
            'debug_clicks_enabled': "Save screenshots and debug information for every click performed."
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

    def get_param(self, key):
        try:
            value = self.dig_tool.param_vars[key].get()
            self.dig_tool.last_known_good_params[key] = value
            return value
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

    def validate_param_value(self, key, value):
        try:
            if key in ['line_sensitivity', 'line_min_height', 'zone_min_width', 'saturation_threshold',
                       'min_zone_height_percent', 'sweet_spot_width_percent', 'system_latency',
                       'max_prediction_time', 'post_click_blindness', 'max_zone_width_percent',
                       'min_velocity_threshold']:
                val = int(value)
                if key in ['line_min_height', 'min_zone_height_percent', 'sweet_spot_width_percent',
                           'max_zone_width_percent']:
                    return 0 <= val <= 100
                elif key in ['line_sensitivity', 'zone_min_width', 'saturation_threshold', 'system_latency',
                             'max_prediction_time', 'post_click_blindness', 'min_velocity_threshold']:
                    return val >= 0
                return True
            elif key in ['zone_smoothing_factor', 'prediction_confidence_threshold']:
                val = float(value)
                if key == 'zone_smoothing_factor':
                    return 0.0 <= val <= 2.0
                elif key == 'prediction_confidence_threshold':
                    return 0.0 <= val <= 1.0
                return True
            elif key in ['prediction_enabled', 'main_on_top', 'preview_on_top', 'debug_on_top', 'debug_clicks_enabled']:
                return isinstance(value, bool)
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
        settings = {'params': {}, 'keybinds': {}, 'game_area': self.dig_tool.game_area}
        for key, var in self.dig_tool.param_vars.items():
            try:
                value = var.get()
                if self.validate_param_value(key, value):
                    settings['params'][key] = value
                else:
                    self.dig_tool.update_status(f"Warning: Invalid value for {key}, using default")
                    settings['params'][key] = self.default_params.get(key)
            except Exception:
                settings['params'][key] = self.default_params.get(key)
        for key, var in self.dig_tool.keybind_vars.items():
            try:
                value = var.get()
                if self.validate_keybind(key, value):
                    settings['keybinds'][key] = value
                else:
                    self.dig_tool.update_status(f"Warning: Invalid keybind for {key}, using default")
                    settings['keybinds'][key] = self.default_keybinds.get(key)
            except Exception:
                settings['keybinds'][key] = self.default_keybinds.get(key)
        try:
            with open(filepath, 'w') as f:
                json.dump(settings, f, indent=4)
            self.dig_tool.update_status(f"Settings saved to {os.path.basename(filepath)}")
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
                if key in self.dig_tool.param_vars and self.validate_param_value(key, value):
                    try:
                        self.dig_tool.param_vars[key].set(value)
                        params_loaded += 1
                    except Exception:
                        self.dig_tool.update_status(f"Warning: Could not set parameter {key}")
            keybinds_loaded = 0
            for key, value in settings.get('keybinds', {}).items():
                if key in self.dig_tool.keybind_vars and self.validate_keybind(key, value):
                    try:
                        self.dig_tool.keybind_vars[key].set(value)
                        keybinds_loaded += 1
                    except Exception:
                        self.dig_tool.update_status(f"Warning: Could not set keybind {key}")
            if 'game_area' in settings and self.validate_game_area(settings['game_area']):
                self.dig_tool.game_area = tuple(settings['game_area']) if isinstance(settings['game_area'], list) else \
                settings['game_area']
                self.dig_tool.preview_btn.config(state=tk.NORMAL)
                self.dig_tool.debug_btn.config(state=tk.NORMAL)
                self.dig_tool.start_threads()
                area_loaded = True
            else:
                area_loaded = False
            self.dig_tool.apply_keybinds()
            self.dig_tool.update_area_info()
            status_parts = [f"Settings loaded from {os.path.basename(filepath)}"]
            if params_loaded > 0:
                status_parts.append(f"{params_loaded} parameters")
            if keybinds_loaded > 0:
                status_parts.append(f"{keybinds_loaded} keybinds")
            if area_loaded:
                status_parts.append("game area")
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
        self.dig_tool.apply_keybinds()
        self.dig_tool.update_status("Settings reset to defaults")
