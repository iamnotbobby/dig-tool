import json
import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import threading
import time
from utils.debug_logger import logger

from interface.settings_feedback_window import SettingsFeedbackWindow
from interface.export_options_dialog import ExportOptionsDialog


class SettingsManager:
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance

        self._setup_settings_directory()

        self._ensure_settings_directory()

        self.default_params = {
            "line_sensitivity": 100,
            "zone_min_width": 100,
            "saturation_threshold": 0.5,
            "min_zone_height_percent": 100,
            "sweet_spot_width_percent": 15,
            "velocity_based_width_enabled": False,
            "velocity_width_multiplier": 1.5,
            "velocity_max_factor": 2000.0,
            "prediction_enabled": True,
            "prediction_confidence_threshold": 0.6,
            "zone_smoothing_factor": 0.8,
            "line_exclusion_radius": 10,
            "post_click_blindness": 50,
            "max_zone_width_percent": 80,
            "target_fps": 120,
            "line_detection_offset": 5.0,
            "system_latency": "auto",
            "main_on_top": True,
            "preview_on_top": True,
            "debug_on_top": True,
            "debug_clicks_enabled": False,
            "screenshot_fps": 240,
            "auto_sell_enabled": False,
            "sell_every_x_digs": 10,
            "sell_delay": 3000,
            "auto_sell_method": "button_click", 
            # Otsu detection parameters
            "use_otsu_detection": False,
            "otsu_min_area": 50,
            "otsu_max_area": "",
            "otsu_morph_kernel_size": 3,
            "otsu_adaptive_area": True,
            "otsu_area_percentile": 0.1,
            # Color picker detection parameters
            "use_color_picker_detection": False,
            "picked_color_rgb": "",  # RGB color in hex format (e.g., "#FF0000")
            "color_tolerance": 30,
            "auto_walk_enabled": False,
            "ranged_auto_walk_enabled": False,
            "walk_min_duration": 500,
            "walk_max_duration": 1000,
            "walk_duration": 500,
            "dynamic_walkspeed_enabled": True,
            "initial_item_count": 0,
            "initial_walkspeed_decrease": 0.0,
            "auto_shovel_enabled": False,
            "shovel_slot": 1,
            "shovel_timeout": 5,
            "user_id": "",
            "webhook_url": "",
            "milestone_interval": 100,
            "use_custom_cursor": False,
            "shovel_equip_mode": "double",
            "include_screenshot_in_discord": False
        }

        self.param_descriptions = {
            "line_sensitivity": "How sharp the contrast must be to be considered a line. Higher values = less sensitive to weak edges.",
            "line_detection_offset": "Pixels to offset the detected line position. Positive = right, negative = left. Decimals allowed for precise positioning.",
            "zone_min_width": "The minimum pixel width for a valid target zone. Smaller zones will be ignored.",
            "max_zone_width_percent": "The maximum width of a target zone as a percent of the capture width. Prevents detecting overly large areas.",
            "min_zone_height_percent": "A target zone must span this percentage of the capture height to be valid. 100% = full height required.",
            "saturation_threshold": "How colorful a pixel must be to be part of the initial target zone search. Higher = more colorful required.",
            "zone_smoothing_factor": "How much to smooth the movement of the target zone. 1.0 = no smoothing, lower = more smoothing.",
            "line_exclusion_radius": "Radius around detected line to exclude from zone detection. Prevents moving line from interfering with zone boundaries.",
            "sweet_spot_width_percent": "The width of the clickable 'sweet spot' in the middle of the zone. Smaller = more precise clicking required.",
            "velocity_based_width_enabled": "Dynamically adjust sweet spot width based on line velocity. Faster movement = wider sweet spot for easier targeting.",
            "velocity_width_multiplier": "How much velocity affects sweet spot width. Higher values = more dramatic width changes based on speed.",
            "velocity_max_factor": "Maximum velocity for normalization (px/s). Velocities above this are treated as maximum speed.",
            "post_click_blindness": "How long to wait after clicking before scanning again (milliseconds). Prevents multiple rapid clicks.",
            "prediction_enabled": "Predicts the line's movement to click earlier, compensating for input/display latency.",
            "prediction_confidence_threshold": "How confident the prediction must be (0.0-1.0). Higher = more conservative prediction.",
            "main_on_top": "Keep the main window always on top of other windows.",
            "preview_on_top": "Keep the preview window always on top of other windows.",
            "debug_on_top": "Keep the debug window always on top of other windows.",
            "debug_clicks_enabled": "Save screenshots and debug information for every click performed.",
            "screenshot_fps": "Target frames per second for screenshot capture. Higher = lower latency but more CPU usage.",
            "auto_sell_enabled": "Automatically sell items after a certain number of digs.",
            "sell_every_x_digs": "Number of digs before auto-selling items.",
            "sell_delay": "Delay in milliseconds before clicking the sell button.",
            "auto_sell_method": "Method for auto-selling: 'button_click' (click specific position) or 'ui_navigation' (use keyboard shortcuts).",
            "auto_walk_enabled": "Automatically move around while digging.",
            "ranged_auto_walk_enabled": "Automatically move around in a range while digging.",
            "walk_min_duration": "Min duration for range",
            "walk_max_duration": "Max duration for range",
            "walk_duration": "Default duration to hold down key presses (milliseconds). Used as base duration unless custom durations are set for individual keys.",
            "dynamic_walkspeed_enabled": "Apply a mathematical formula to determine the decreased walkspeed after X items.",
            "initial_item_count": "Starting item count for walkspeed calculation. Useful if you already have items collected.",
            # Otsu detection help text
            "use_otsu_detection": "Use Otsu's automatic thresholding instead of manual saturation threshold. Can be more adaptive to different lighting conditions.",
            "otsu_min_area": "Minimum area (pixels) for detected regions when using Otsu. Smaller regions will be filtered out.",
            "otsu_max_area": "Maximum area (pixels) for detected regions when using Otsu. Leave empty for no upper limit.",
            "otsu_morph_kernel_size": "Size of morphological operations kernel for noise reduction. 0 to disable, higher values = more smoothing.",
            "otsu_adaptive_area": "Use adaptive area filtering based on image size instead of fixed pixel values.",
            "otsu_area_percentile": "Minimum area as percentage of image size when using adaptive area filtering.",
            # Color picker detection help text
            "use_color_picker_detection": "Use a specific color picked from the screen. Click 'Pick Color' to select a target color.",
            "picked_color_rgb": "The RGB color value sampled from a screen area (automatically set when using Sample Area button).",
            "color_tolerance": "Tolerance for color matching. Higher values = more colors will match, lower = more precise matching.",
            "initial_walkspeed_decrease": "Additional walkspeed decrease factor (0.0-1.0) added on top of the formula. Higher = slower movement.",
            "user_id": "Discord user ID for notifications (optional - leave blank for no ping).",
            "webhook_url": "Discord webhook URL for sending notifications.",
            "auto_shovel_enabled": "Automatically re-equip shovel when no activity detected for specified time.",
            "shovel_slot": "Hotbar slot number (0-9) where your shovel is located. 0 = slot 10.",
            "shovel_timeout": "Minutes of inactivity before auto-equipping shovel (based on clicks, digs, and target detection).",
            "milestone_interval": "Send Discord notification every X digs (milestone notifications).",
            "target_fps": "Your game's FPS for prediction calculations. Higher FPS = more precise predictions. Does not affect screenshot rate.",
            "use_custom_cursor": "Move cursor to set position before clicking when enabled. Cannot be used with Auto-Walk.",
            "shovel_equip_mode": "Whether to press the shovel slot key once ('single') or twice ('double') when re-equipping.",
            "include_screenshot_in_discord": "When enabled, screenshots of your game will be included in Discord milestone notifications."
        }

        self.default_keybinds = {
            "toggle_bot": "f1",
            "toggle_gui": "f2",
            "toggle_overlay": "f3",
            "toggle_autowalk_overlay": "f4",
        }

        self.keybind_descriptions = {
            "toggle_bot": "Start/stop the clicking detection and automation.",
            "toggle_gui": "Show/hide the main control window.",
            "toggle_overlay": "Toggle the game overlay display on/off.",
            "toggle_autowalk_overlay": "Toggle the auto walk overlay display on/off.",
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
        if setting_key == "use_custom_cursor":
            return "DISABLED: Cannot use Custom Cursor while Auto-Walk is enabled. Disable Auto-Walk first."
        elif setting_key in ("auto_walk_enabled", "ranged_auto_walk_enabled"):
            return "DISABLED: Cannot use Auto-Walk while Custom Cursor is enabled. Disable Custom Cursor first."
        return ""

    def is_setting_conflicted(self, setting_key):
        if setting_key == "use_custom_cursor":
            return self.dig_tool.param_vars.get(
                "auto_walk_enabled", tk.BooleanVar()
            ).get()
        elif setting_key in ("auto_walk_enabled", "ranged_auto_walk_enabled"):
            return self.dig_tool.param_vars.get(
                "use_custom_cursor", tk.BooleanVar()
            ).get()
        return False

    def update_setting_states(self):
        conflicting_settings = ["use_custom_cursor", "auto_walk_enabled", "ranged_auto_walk_enabled"]

        for setting_key in conflicting_settings:
            if (
                hasattr(self.dig_tool, "setting_widgets")
                and setting_key in self.dig_tool.setting_widgets
            ):
                widget = self.dig_tool.setting_widgets[setting_key]
                is_conflicted = self.is_setting_conflicted(setting_key)

                if is_conflicted:
                    widget.config(state="disabled", fg="#808080")
                else:
                    widget.config(state="normal", fg="#000000")

    def get_param(self, key):
        try:
            if key in self.dig_tool.param_vars:
                value = self.dig_tool.param_vars[key].get()

                if key in self.dig_tool.last_known_good_params:
                    old_value = self.dig_tool.last_known_good_params[key]
                    if old_value != value:
                        self.dig_tool.root.after_idle(
                            lambda: self.auto_save_setting("parameters")
                        )

                self.dig_tool.last_known_good_params[key] = value

                if key in ["use_custom_cursor", "auto_walk_enabled", "ranged_auto_walk_enabled"]:
                    self.update_setting_states()

                return value
            else:
                return self.default_params.get(key, 0)
        except (tk.TclError, ValueError, AttributeError):
            self.dig_tool.update_status(
                f"Error: Invalid value for '{key}'. Using last known good value."
            )
            if key in self.dig_tool.last_known_good_params:
                return self.dig_tool.last_known_good_params[key]
            return self.default_params.get(key, 0)

    def validate_game_area(self, area):
        if not area or not isinstance(area, (list, tuple)) or len(area) != 4:
            return False
        try:
            x1, y1, x2, y2 = area
            return (
                isinstance(x1, (int, float))
                and isinstance(y1, (int, float))
                and isinstance(x2, (int, float))
                and isinstance(y2, (int, float))
                and x2 > x1
                and y2 > y1
                and x1 >= 0
                and y1 >= 0
            )
        except (ValueError, TypeError):
            return False

    def validate_position(self, position):
        if not position:
            return False
        try:
            if isinstance(position, (list, tuple)) and len(position) == 2:
                x, y = position
                return (
                    isinstance(x, (int, float))
                    and isinstance(y, (int, float))
                    and x >= 0
                    and y >= 0
                )
        except (ValueError, TypeError):
            pass
        return False

    def validate_param_value(self, key, value):
        try:
            if key == "picked_color_rgb":
                if value == "" or value is None:
                    return True
                import re

                return bool(re.match(r"^#[0-9A-Fa-f]{6}$", value))

            if key == "otsu_max_area":
                if value == "" or value is None:
                    return True
                try:
                    val = int(value)
                    return val >= 1
                except ValueError:
                    return False

            if key in [
                "line_sensitivity",
                "zone_min_width",
                "saturation_threshold",
                "min_zone_height_percent",
                "sweet_spot_width_percent",
                "post_click_blindness",
                "max_zone_width_percent",
                "sell_every_x_digs",
                "sell_delay",
                "walk_duration",
                "walk_min_duration"
                "walk_max_duration"
                "milestone_interval",
                "target_fps",
                "screenshot_fps",
                "otsu_min_area",
                "otsu_morph_kernel_size",
                "color_tolerance",
            ]:
                val = int(value)
                if key in [
                    "min_zone_height_percent",
                    "sweet_spot_width_percent",
                    "max_zone_width_percent",
                ]:
                    return 0 <= val <= 100
                elif key in [
                    "line_sensitivity",
                    "zone_min_width",
                    "saturation_threshold",
                    "post_click_blindness",
                    "sell_every_x_digs",
                    "sell_delay",
                    "walk_duration",
                    "walk_min_duration",
                    "walk_max_duration",
                    "milestone_interval",
                    "otsu_min_area",
                    "otsu_morph_kernel_size",
                ]:
                    return val >= 1 if key == "milestone_interval" else val >= 0
                elif key == "target_fps":
                    return 1 <= val <= 1000
                elif key == "screenshot_fps":
                    return 30 <= val <= 500
                return True
            elif key in [
                "zone_smoothing_factor",
                "prediction_confidence_threshold",
                "line_detection_offset",
                "line_exclusion_radius",
                "velocity_width_multiplier",
                "velocity_max_factor",
                "otsu_area_percentile",
            ]:
                val = float(value)
                if key == "velocity_width_multiplier":
                    return 0.0 <= val <= 5.0
                elif key == "velocity_max_factor":
                    return 10.0 <= val <= 2000.0
                if key == "zone_smoothing_factor":
                    return 0.0 <= val <= 2.0
                elif key == "prediction_confidence_threshold":
                    return 0.0 <= val <= 1.0
                elif key == "line_detection_offset":
                    return True
                elif key == "line_exclusion_radius":
                    return val >= 0  #
                elif key == "otsu_area_percentile":
                    return 0.01 <= val <= 10.0
                return True
            elif key in [
                "prediction_enabled",
                "main_on_top",
                "preview_on_top",
                "debug_on_top",
                "debug_clicks_enabled",
                "auto_sell_enabled",
                "auto_walk_enabled",
                "ranged_auto_walk_enabled",
                "use_custom_cursor",
                "auto_shovel_enabled",
                "use_otsu_detection",
                "otsu_adaptive_area",
                "use_color_picker_detection",
            ]:
                return isinstance(value, bool)
            elif key in ["user_id", "webhook_url"]:
                return isinstance(value, str)
            elif key == "auto_sell_method":
                return isinstance(value, str) and value in ["button_click", "ui_navigation"]
            elif key == "initial_walkspeed_decrease":
                if isinstance(value, str):
                    value = float(value)
                return 0.0 <= value <= 1.0
            elif key == "initial_item_count":
                if isinstance(value, str):
                    value = int(value)
                return value >= 0
            return True
        except (ValueError, TypeError):
            return False

    def validate_keybind(self, key, value):
        if not isinstance(value, str) or len(value.strip()) == 0:
            return False
        return key in self.default_keybinds

    def refresh_pattern_dropdown(self):
        if hasattr(self.dig_tool, "update_walk_pattern_dropdown"):
            self.dig_tool.update_walk_pattern_dropdown()
            self.dig_tool.update_status("Pattern list refreshed!")

    def open_custom_pattern_manager(self):
        if hasattr(self.dig_tool, "open_custom_pattern_manager"):
            self.dig_tool.open_custom_pattern_manager()

    def export_settings(self):
        options_dialog = ExportOptionsDialog(self.dig_tool.root)
        export_options = options_dialog.show_dialog()

        if export_options is None:
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Export Settings As",
        )
        if not filepath:
            return

        feedback = SettingsFeedbackWindow(self.dig_tool.root, "Exporting Settings")
        feedback.show_window()

        def export_process():
            try:
                feedback.update_progress(10, "Preparing settings data...")
                time.sleep(0.1)

                settings = {}

                settings["params"] = {}

                if export_options["keybinds"]:
                    settings["keybinds"] = {}

                if export_options["configuration"]:
                    settings["game_area"] = self.dig_tool.game_area
                    settings["sell_button_position"] = getattr(
                        self.dig_tool.automation_manager, "sell_button_position", None
                    )
                    settings["cursor_position"] = getattr(
                        self.dig_tool, "cursor_position", None
                    )
                    settings["walk_pattern"] = (
                        getattr(self.dig_tool, "walk_pattern_var", tk.StringVar()).get()
                        if hasattr(self.dig_tool, "walk_pattern_var")
                        else "_KC_Nugget_v1"
                    )

                feedback.add_section("PARAMETERS")
                feedback.update_progress(20, "Processing parameters...")

                total_params = len(self.default_params)
                for i, key in enumerate(self.default_params.keys()):
                    try:
                        if key in self.dig_tool.param_vars:
                            value = self.dig_tool.param_vars[key].get()

                            if (
                                key in ["user_id", "webhook_url"]
                                and not export_options["discord"]
                            ):
                                settings["params"][key] = ""
                                feedback.add_change_entry(
                                    key, str(value), "(excluded)", "warning"
                                )
                            else:
                                settings["params"][key] = value
                                feedback.add_change_entry(
                                    key, "", str(value), "success"
                                )
                        else:
                            settings["params"][key] = self.default_params[key]
                            feedback.add_change_entry(
                                key, "", str(self.default_params[key]), "info"
                            )
                    except Exception as e:
                        settings["params"][key] = self.default_params.get(key)
                        feedback.add_change_entry(key, "", f"ERROR: {e}", "error")

                    progress = 20 + (i * 30 / total_params)
                    feedback.update_progress(progress)
                    time.sleep(0.02)

                if export_options["keybinds"]:
                    feedback.add_section("KEYBINDS")
                    feedback.update_progress(50, "Processing keybinds...")

                    total_keybinds = len(self.default_keybinds)
                    for i, key in enumerate(self.default_keybinds.keys()):
                        try:
                            if key in self.dig_tool.keybind_vars:
                                value = self.dig_tool.keybind_vars[key].get()
                                if self.validate_keybind(key, value):
                                    settings["keybinds"][key] = value
                                    feedback.add_change_entry(key, "", value, "success")
                                else:
                                    settings["keybinds"][key] = (
                                        self.default_keybinds.get(key)
                                    )
                                    feedback.add_change_entry(
                                        key,
                                        value,
                                        self.default_keybinds.get(key),
                                        "warning",
                                    )
                            else:
                                settings["keybinds"][key] = self.default_keybinds.get(
                                    key
                                )
                                feedback.add_change_entry(
                                    key, "", self.default_keybinds.get(key), "info"
                                )
                        except Exception as e:
                            settings["keybinds"][key] = self.default_keybinds.get(key)
                            feedback.add_change_entry(key, "", f"ERROR: {e}", "error")

                        progress = 50 + (i * 20 / total_keybinds)
                        feedback.update_progress(progress)
                        time.sleep(0.02)
                else:
                    feedback.add_section("KEYBINDS")
                    feedback.add_text("✗ Keybinds: excluded", "warning")

                if export_options["configuration"]:
                    feedback.add_section("CONFIGURATION")
                    feedback.update_progress(70, "Processing configuration...")

                    if self.dig_tool.game_area:
                        feedback.add_text(
                            f"✓ Game Area: {self.dig_tool.game_area}", "success"
                        )
                    else:
                        feedback.add_text("✗ Game Area: Not set", "warning")

                    if (
                        hasattr(
                            self.dig_tool.automation_manager, "sell_button_position"
                        )
                        and self.dig_tool.automation_manager.sell_button_position
                    ):
                        feedback.add_text(
                            f"✓ Sell Button: {self.dig_tool.automation_manager.sell_button_position}",
                            "success",
                        )
                    else:
                        feedback.add_text("✗ Sell Button: Not set", "warning")

                    if (
                        hasattr(self.dig_tool, "cursor_position")
                        and self.dig_tool.cursor_position
                    ):
                        feedback.add_text(
                            f"✓ Cursor Position: {self.dig_tool.cursor_position}",
                            "success",
                        )
                    else:
                        feedback.add_text("✗ Cursor Position: Not set", "warning")

                    if hasattr(self.dig_tool, "walk_pattern_var"):
                        pattern = self.dig_tool.walk_pattern_var.get()
                        feedback.add_text(f"✓ Walk Pattern: {pattern}", "success")
                    else:
                        feedback.add_text("✗ Walk Pattern: Not set", "warning")
                else:
                    feedback.add_section("CONFIGURATION")
                    feedback.add_text("✗ Configuration: excluded", "warning")

                feedback.update_progress(85, "Writing file...")
                time.sleep(0.1)

                with open(filepath, "w") as f:
                    json.dump(settings, f, indent=4)

                feedback.update_progress(95, "Finalizing...")
                time.sleep(0.1)

                included_items = []
                if export_options["parameters"]:
                    included_items.append("Parameters")
                if export_options["keybinds"]:
                    included_items.append("Keybinds")
                if export_options["discord"]:
                    included_items.append("Discord Info")
                if export_options["configuration"]:
                    included_items.append("Configuration")

                filename = os.path.basename(filepath)

                feedback.add_section("COMPLETION")
                feedback.add_text(f"✓ Settings exported to: {filename}", "success")
                feedback.add_text(f"✓ Included: {', '.join(included_items)}", "info")

                feedback.operation_complete(success=True)

                self.dig_tool.update_status(
                    f"Settings exported to {filename} (Included: {', '.join(included_items)})"
                )

            except Exception as e:
                feedback.show_error("Export Failed", str(e))
                self.dig_tool.update_status(f"Error exporting settings: {e}")

        threading.Thread(target=export_process, daemon=True).start()

    def import_settings(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Import Settings From",
        )
        if not filepath:
            return

        feedback = SettingsFeedbackWindow(self.dig_tool.root, "Importing Settings")
        feedback.show_window()

        def import_process():
            try:
                feedback.update_progress(10, "Reading settings file...")
                time.sleep(0.1)

                with open(filepath, "r") as f:
                    settings = json.load(f)

                if not isinstance(settings, dict):
                    feedback.show_error(
                        "Invalid File", "Settings file format is invalid"
                    )
                    return

                feedback.update_progress(20, "Validating settings structure...")
                time.sleep(0.1)

                feedback.add_section("PARAMETERS")
                params_loaded = 0
                params_failed = []

                total_params = len(settings.get("params", {}))
                for i, (key, value) in enumerate(settings.get("params", {}).items()):
                    if key in self.dig_tool.param_vars:
                        try:
                            param_var = self.dig_tool.param_vars[key]
                            old_value = param_var.get()

                            if isinstance(param_var, tk.BooleanVar):
                                if isinstance(value, str):
                                    converted_value = value.lower() in (
                                        "true",
                                        "1",
                                        "yes",
                                        "on",
                                    )
                                else:
                                    converted_value = bool(value)
                            elif isinstance(param_var, tk.DoubleVar):
                                converted_value = float(value)
                            elif isinstance(param_var, tk.IntVar):
                                converted_value = int(
                                    float(str(value).replace("JS:", ""))
                                )
                            else:
                                converted_value = str(value)

                            param_var.set(converted_value)
                            feedback.add_change_entry(
                                key, str(old_value), str(converted_value), "success"
                            )
                            params_loaded += 1

                        except Exception as e:
                            feedback.add_change_entry(
                                key, "", f"ERROR: {str(e)}", "error"
                            )
                            params_failed.append(key)
                    else:
                        feedback.add_change_entry(
                            key, "", "Unknown parameter", "warning"
                        )
                        params_failed.append(key)

                    progress = 20 + (i * 30 / max(total_params, 1))
                    feedback.update_progress(progress)
                    time.sleep(0.02)

                self.update_setting_states()

                feedback.add_section("KEYBINDS")
                keybinds_loaded = 0
                keybinds_failed = []

                total_keybinds = len(settings.get("keybinds", {}))
                for i, (key, value) in enumerate(settings.get("keybinds", {}).items()):
                    if key in self.dig_tool.keybind_vars and self.validate_keybind(
                        key, value
                    ):
                        try:
                            old_value = self.dig_tool.keybind_vars[key].get()
                            self.dig_tool.keybind_vars[key].set(value)
                            feedback.add_change_entry(key, old_value, value, "success")
                            keybinds_loaded += 1
                        except Exception as e:
                            feedback.add_change_entry(
                                key, "", f"ERROR: {str(e)}", "error"
                            )
                            keybinds_failed.append(key)
                    else:
                        feedback.add_change_entry(key, "", "Invalid keybind", "warning")
                        keybinds_failed.append(key)

                    progress = 50 + (i * 20 / max(total_keybinds, 1))
                    feedback.update_progress(progress)
                    time.sleep(0.02)

                feedback.add_section("CONFIGURATION")
                feedback.update_progress(70, "Loading configuration settings...")

                area_loaded = False
                if "game_area" in settings and self.validate_game_area(
                    settings["game_area"]
                ):
                    old_area = self.dig_tool.game_area
                    self.dig_tool.game_area = (
                        tuple(settings["game_area"])
                        if isinstance(settings["game_area"], list)
                        else settings["game_area"]
                    )

                    feedback.add_change_entry(
                        "Game Area",
                        str(old_area) if old_area else "None",
                        str(self.dig_tool.game_area),
                        "success",
                    )

                    self.dig_tool.update_area_info()
                    if hasattr(self.dig_tool, "preview_btn"):
                        self.dig_tool.preview_btn.config(state=tk.NORMAL)
                    if hasattr(self.dig_tool, "debug_btn"):
                        self.dig_tool.debug_btn.config(state=tk.NORMAL)
                    if (
                        not self.dig_tool.main_loop_thread
                        or not self.dig_tool.main_loop_thread.is_alive()
                    ):
                        self.dig_tool.start_threads()
                    area_loaded = True
                else:
                    feedback.add_text("✗ Game Area: Not found or invalid", "warning")

                sell_button_loaded = False
                if "sell_button_position" in settings and self.validate_position(
                    settings["sell_button_position"]
                ):
                    try:
                        pos = settings["sell_button_position"]
                        old_pos = getattr(
                            self.dig_tool.automation_manager,
                            "sell_button_position",
                            None,
                        )
                        self.dig_tool.automation_manager.sell_button_position = tuple(
                            pos
                        )

                        feedback.add_change_entry(
                            "Sell Button",
                            str(old_pos) if old_pos else "None",
                            str(tuple(pos)),
                            "success",
                        )

                        self.dig_tool.update_sell_info()
                        sell_button_loaded = True
                    except Exception:
                        feedback.add_text(
                            "✗ Sell Button: Invalid position data", "warning"
                        )
                else:
                    feedback.add_text("✗ Sell Button: Not found", "warning")

                cursor_loaded = False
                if "cursor_position" in settings and self.validate_position(
                    settings["cursor_position"]
                ):
                    try:
                        pos = settings["cursor_position"]
                        old_pos = getattr(self.dig_tool, "cursor_position", None)
                        self.dig_tool.cursor_position = tuple(pos)

                        feedback.add_change_entry(
                            "Cursor Position",
                            str(old_pos) if old_pos else "None",
                            str(tuple(pos)),
                            "success",
                        )

                        self.dig_tool.update_cursor_info()
                        cursor_loaded = True
                    except Exception:
                        feedback.add_text(
                            "✗ Cursor Position: Invalid position data", "warning"
                        )
                else:
                    feedback.add_text("✗ Cursor Position: Not found", "warning")

                pattern_loaded = False
                if "walk_pattern" in settings and hasattr(
                    self.dig_tool, "walk_pattern_var"
                ):
                    try:
                        pattern = settings["walk_pattern"]
                        old_pattern = self.dig_tool.walk_pattern_var.get()
                        if (
                            hasattr(self.dig_tool.automation_manager, "walk_patterns")
                            and pattern
                            in self.dig_tool.automation_manager.walk_patterns
                        ):
                            self.dig_tool.walk_pattern_var.set(pattern)
                            feedback.add_change_entry(
                                "Walk Pattern", old_pattern, pattern, "success"
                            )
                            pattern_loaded = True
                        else:
                            feedback.add_text(
                                f"✗ Walk Pattern: Unknown pattern '{pattern}'",
                                "warning",
                            )
                    except Exception:
                        feedback.add_text("✗ Walk Pattern: Invalid data", "warning")
                else:
                    feedback.add_text("✗ Walk Pattern: Not found", "warning")

                feedback.update_progress(90, "Finalizing...")

                self.dig_tool.apply_keybinds()

                if hasattr(self.dig_tool, "update_walk_pattern_dropdown"):
                    self.dig_tool.update_walk_pattern_dropdown()

                total_failed = len(params_failed + keybinds_failed)
                total_success = params_loaded + keybinds_loaded
                total_items = total_success + total_failed

                feedback.add_summary_stats(total_success, total_failed, total_items)
                feedback.operation_complete(success=total_failed == 0)

                filename = os.path.basename(filepath)
                self.dig_tool.update_status(
                    f"Settings imported from {filename} - See details window"
                )

            except json.JSONDecodeError:
                feedback.show_error(
                    "Invalid JSON", "The selected file contains invalid JSON data"
                )
            except Exception as e:
                feedback.show_error("Import Failed", str(e))

        threading.Thread(target=import_process, daemon=True).start()

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
                            feedback.add_change_entry(
                                key, str(old_value), str(default_value), "success"
                            )
                            params_reset += 1
                        except Exception as e:
                            feedback.add_change_entry(key, "", f"ERROR: {e}", "error")

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
                            feedback.add_change_entry(
                                key, old_value, default_value, "success"
                            )
                            keybinds_reset += 1
                        except Exception as e:
                            feedback.add_change_entry(key, "", f"ERROR: {e}", "error")

                    progress = 50 + (i * 30 / total_keybinds)
                    feedback.update_progress(progress)
                    time.sleep(0.02)

                feedback.add_section("CONFIGURATION")
                feedback.update_progress(80, "Resetting configuration...")

                if hasattr(self.dig_tool, "walk_pattern_var"):
                    try:
                        old_pattern = self.dig_tool.walk_pattern_var.get()
                        self.dig_tool.walk_pattern_var.set("_KC_Nugget_v1")
                        feedback.add_change_entry(
                            "Walk Pattern", old_pattern, "_KC_Nugget_v1", "success"
                        )
                    except Exception:
                        feedback.add_text("✗ Walk Pattern: Reset failed", "error")

                feedback.update_progress(90, "Finalizing...")

                if hasattr(self.dig_tool, "update_walk_pattern_dropdown"):
                    self.dig_tool.update_walk_pattern_dropdown()

                self.dig_tool.apply_keybinds()

                self.save_all_settings()

                feedback.update_progress(
                    100,
                    f"Reset Complete! {params_reset} parameters and {keybinds_reset} keybinds reset.",
                )
                feedback.operation_complete(success=True)

            except Exception as e:
                logger.error(f"Error during settings reset: {e}")
                feedback.add_text(f"Error: {e}", "error")
                feedback.update_progress(100, "Reset failed.")
                feedback.operation_complete(success=False)

        def perform_reset():
            reset_process()

        reset_thread = threading.Thread(target=perform_reset, daemon=True)
        reset_thread.start()

    def _setup_settings_directory(self):
        try:
            # Try to get LOCALAPPDATA first
            appdata_dir = os.environ.get("LOCALAPPDATA")
            if appdata_dir and os.path.exists(appdata_dir):
                self.settings_dir = os.path.join(appdata_dir, "DigTool")
                return

            # Fallback to APPDATA
            appdata_dir = os.environ.get("APPDATA")
            if appdata_dir and os.path.exists(appdata_dir):
                self.settings_dir = os.path.join(appdata_dir, "DigTool")
                return

            # Final fallback to current directory
            self.settings_dir = os.path.join(os.getcwd(), "settings")
            logger.warning("Using current directory for settings storage as fallback")
        except Exception as e:
            logger.error(f"Error setting up settings directory: {e}")
            self.settings_dir = os.path.join(os.getcwd(), "settings")

    def _ensure_settings_directory(self):
        try:
            os.makedirs(self.settings_dir, exist_ok=True)

            self.auto_walk_dir = os.path.join(self.settings_dir, "Auto Walk")
            os.makedirs(self.auto_walk_dir, exist_ok=True)

            logger.info(f"Settings directory ensured at: {self.settings_dir}")
            logger.info(f"Auto Walk directory ensured at: {self.auto_walk_dir}")
        except Exception as e:
            logger.error(f"Error ensuring settings directory: {e}")
            self.settings_dir = os.path.join(os.getcwd(), "settings")
            self.auto_walk_dir = os.path.join(self.settings_dir, "Auto Walk")
            try:
                os.makedirs(self.auto_walk_dir, exist_ok=True)
            except Exception as fallback_error:
                logger.error(f"Fallback directory creation failed: {fallback_error}")

    def get_settings_info(self):
        return {
            "settings_directory": self.settings_dir,
            "auto_walk_directory": getattr(
                self, "auto_walk_dir", os.path.join(self.settings_dir, "Auto Walk")
            ),
            "exists": os.path.exists(self.settings_dir),
        }

    def get_auto_walk_directory(self):
        return getattr(
            self, "auto_walk_dir", os.path.join(self.settings_dir, "Auto Walk")
        )

    def open_settings_directory(self):
        try:
            import subprocess

            self._ensure_settings_directory()

            subprocess.run(
                ["explorer", os.path.abspath(self.settings_dir)], check=False
            )
            logger.info(f"Opened settings directory: {self.settings_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to open settings directory: {e}")
            return False

    def load_all_settings(self):
        self._ensure_settings_directory()

        settings_file = os.path.join(self.settings_dir, "settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r") as f:
                    settings = json.load(f)

                if "params" in settings:
                    for key, value in settings["params"].items():
                        if key in self.dig_tool.param_vars:
                            try:
                                param_var = self.dig_tool.param_vars[key]
                                if isinstance(param_var, tk.BooleanVar):
                                    param_var.set(bool(value))
                                elif isinstance(param_var, (tk.IntVar, tk.DoubleVar)):
                                    param_var.set(
                                        float(value)
                                        if isinstance(param_var, tk.DoubleVar)
                                        else int(value)
                                    )
                                elif isinstance(param_var, tk.StringVar):
                                    param_var.set(str(value))
                                logger.debug(f"Loaded parameter {key}: {value}")
                            except Exception as e:
                                logger.warning(f"Failed to load parameter {key}: {e}")

                if "keybinds" in settings:
                    for key, value in settings["keybinds"].items():
                        if key in self.dig_tool.keybind_vars:
                            try:
                                self.dig_tool.keybind_vars[key].set(str(value))
                                logger.debug(f"Loaded keybind {key}: {value}")
                            except Exception as e:
                                logger.warning(f"Failed to load keybind {key}: {e}")

                if "window_positions" in settings:
                    for window_name, position in settings["window_positions"].items():
                        if self.validate_window_position(position):
                            self.dig_tool.window_positions[window_name] = position
                            logger.debug(
                                f"Loaded window position {window_name}: {position}"
                            )

                if "game_area" in settings and self.validate_game_area(
                    settings["game_area"]
                ):
                    self.dig_tool.game_area = tuple(settings["game_area"])
                    logger.debug(f"Loaded game area: {self.dig_tool.game_area}")
                    if hasattr(self.dig_tool, "preview_btn"):
                        self.dig_tool.preview_btn.config(state=tk.NORMAL)
                    if hasattr(self.dig_tool, "debug_btn"):
                        self.dig_tool.debug_btn.config(state=tk.NORMAL)
                    if hasattr(self.dig_tool, "update_area_info"):
                        self.dig_tool.update_area_info()
                    if hasattr(self.dig_tool, "start_threads"):
                        self.dig_tool.root.after(100, self.dig_tool.start_threads)

                if "sell_button_position" in settings and self.validate_position(
                    settings["sell_button_position"]
                ):
                    self.dig_tool.automation_manager.sell_button_position = tuple(
                        settings["sell_button_position"]
                    )
                    logger.debug(
                        f"Loaded sell button position: {self.dig_tool.automation_manager.sell_button_position}"
                    )
                    if hasattr(self.dig_tool, "update_sell_info"):
                        self.dig_tool.update_sell_info()

                if "cursor_position" in settings and self.validate_position(
                    settings["cursor_position"]
                ):
                    self.dig_tool.cursor_position = tuple(settings["cursor_position"])
                    logger.debug(
                        f"Loaded cursor position: {self.dig_tool.cursor_position}"
                    )
                    if hasattr(self.dig_tool, "update_cursor_info"):
                        self.dig_tool.update_cursor_info()

                if "walk_pattern" in settings and hasattr(
                    self.dig_tool, "walk_pattern_var"
                ):
                    try:
                        self.dig_tool.walk_pattern_var.set(settings["walk_pattern"])
                        logger.debug(f"Loaded walk pattern: {settings['walk_pattern']}")
                    except Exception as e:
                        logger.warning(f"Failed to load walk pattern: {e}")

                logger.info(f"Settings loaded successfully from {settings_file}")

            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                logger.info("Using default settings")
        else:
            logger.info("No settings file found, using defaults")

        self._load_auto_walk_patterns()

    def save_all_settings(self):
        self._ensure_settings_directory()

        try:
            settings_file = os.path.join(self.settings_dir, "settings.json")

            settings = {"params": {}, "keybinds": {}, "window_positions": {}}

            for key, var in self.dig_tool.param_vars.items():
                try:
                    settings["params"][key] = var.get()
                except Exception as e:
                    logger.warning(f"Failed to save parameter {key}: {e}")

            for key, var in self.dig_tool.keybind_vars.items():
                try:
                    settings["keybinds"][key] = var.get()
                except Exception as e:
                    logger.warning(f"Failed to save keybind {key}: {e}")

            for window_name, position in self.dig_tool.window_positions.items():
                if self.validate_window_position(position):
                    settings["window_positions"][window_name] = position

            if hasattr(self.dig_tool, "game_area") and self.dig_tool.game_area:
                settings["game_area"] = self.dig_tool.game_area

            if (
                hasattr(self.dig_tool, "automation_manager")
                and hasattr(self.dig_tool.automation_manager, "sell_button_position")
                and self.dig_tool.automation_manager.sell_button_position
            ):
                settings["sell_button_position"] = (
                    self.dig_tool.automation_manager.sell_button_position
                )

            if (
                hasattr(self.dig_tool, "cursor_position")
                and self.dig_tool.cursor_position
            ):
                settings["cursor_position"] = self.dig_tool.cursor_position

            if hasattr(self.dig_tool, "walk_pattern_var"):
                try:
                    settings["walk_pattern"] = self.dig_tool.walk_pattern_var.get()
                except:
                    pass

            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)

            logger.info(f"Settings saved successfully to {settings_file}")

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

        self._save_auto_walk_patterns()

    def apply_loaded_parameters(self):
        try:
            if hasattr(self.dig_tool, "main_window") and self.dig_tool.main_window:
                self.dig_tool.main_window.update_dependent_widgets_state()

            logger.info("Parameters applied successfully")
        except Exception as e:
            logger.error(f"Failed to apply parameters: {e}")

    def auto_save_setting(self, setting_type):
        try:
            if setting_type == "params":
                settings_file = os.path.join(self.settings_dir, "settings.json")
                existing_settings = {}

                if os.path.exists(settings_file):
                    try:
                        with open(settings_file, "r") as f:
                            existing_settings = json.load(f)
                    except:
                        pass

                existing_settings["params"] = {}
                for key, var in self.dig_tool.param_vars.items():
                    try:
                        existing_settings["params"][key] = var.get()
                    except Exception as e:
                        logger.warning(f"Failed to auto-save parameter {key}: {e}")

                with open(settings_file, "w") as f:
                    json.dump(existing_settings, f, indent=2)

                logger.debug(f"Auto-saved parameters to {settings_file}")

            elif setting_type == "keybinds":
                settings_file = os.path.join(self.settings_dir, "settings.json")
                existing_settings = {}

                if os.path.exists(settings_file):
                    try:
                        with open(settings_file, "r") as f:
                            existing_settings = json.load(f)
                    except:
                        pass

                existing_settings["keybinds"] = {}
                for key, var in self.dig_tool.keybind_vars.items():
                    try:
                        existing_settings["keybinds"][key] = var.get()
                    except Exception as e:
                        logger.warning(f"Failed to auto-save keybind {key}: {e}")

                with open(settings_file, "w") as f:
                    json.dump(existing_settings, f, indent=2)

                logger.debug(f"Auto-saved keybinds to {settings_file}")

            elif setting_type == "coordinates":
                settings_file = os.path.join(self.settings_dir, "settings.json")
                existing_settings = {}

                if os.path.exists(settings_file):
                    try:
                        with open(settings_file, "r") as f:
                            existing_settings = json.load(f)
                    except:
                        pass

                if hasattr(self.dig_tool, "game_area") and self.dig_tool.game_area:
                    existing_settings["game_area"] = self.dig_tool.game_area

                if (
                    hasattr(self.dig_tool, "automation_manager")
                    and hasattr(
                        self.dig_tool.automation_manager, "sell_button_position"
                    )
                    and self.dig_tool.automation_manager.sell_button_position
                ):
                    existing_settings["sell_button_position"] = (
                        self.dig_tool.automation_manager.sell_button_position
                    )

                if (
                    hasattr(self.dig_tool, "cursor_position")
                    and self.dig_tool.cursor_position
                ):
                    existing_settings["cursor_position"] = self.dig_tool.cursor_position

                if hasattr(self.dig_tool, "walk_pattern_var"):
                    try:
                        existing_settings["walk_pattern"] = (
                            self.dig_tool.walk_pattern_var.get()
                        )
                    except:
                        pass

                with open(settings_file, "w") as f:
                    json.dump(existing_settings, f, indent=2)

                logger.debug(f"Auto-saved coordinates to {settings_file}")

            else:
                logger.debug(f"Auto-saving {setting_type} - not implemented")

        except Exception as e:
            logger.error(f"Failed to auto-save {setting_type}: {e}")

    def _load_auto_walk_patterns(self):
        try:
            auto_walk_dir = os.path.join(self.settings_dir, "Auto Walk")
            if not os.path.exists(auto_walk_dir):
                logger.info("No Auto Walk directory found")
                return

            logger.debug("Auto-walk patterns loading checked")

        except Exception as e:
            logger.error(f"Failed to load auto-walk patterns: {e}")

    def _save_auto_walk_patterns(self):
        try:
            self._ensure_settings_directory()

            logger.debug("Auto-walk patterns saving checked")

        except Exception as e:
            logger.error(f"Failed to save auto-walk patterns: {e}")

    def import_settings_from_file(self, filepath):
        feedback = SettingsFeedbackWindow(self.dig_tool.root, "Importing Settings")
        feedback.show_window()

        def import_process():
            try:
                feedback.update_progress(10, "Reading settings file...")
                
                with open(filepath, "r") as f:
                    settings = json.load(f)

                if not isinstance(settings, dict):
                    feedback.show_error("Invalid File", "Settings file format is invalid")
                    return False

                feedback.update_progress(20, "Validating settings structure...")
                
                feedback.add_section("PARAMETERS")
                params_updated = 0
                params_data = settings.get("parameters", settings.get("params", {})) 
                
                total_params = len(params_data)
                for i, (key, value) in enumerate(params_data.items()):
                    if key in self.default_params:
                        try:
                            param_type = self.get_param_type(key)
                            if param_type == tk.BooleanVar:
                                converted_value = bool(value)
                            elif param_type == tk.IntVar:
                                converted_value = int(value)
                            elif param_type == tk.DoubleVar:
                                converted_value = float(value)
                            else:
                                converted_value = str(value)

                            if self.validate_param_value(key, converted_value):
                                if key in self.dig_tool.param_vars:
                                    old_value = self.dig_tool.param_vars[key].get()
                                    self.dig_tool.param_vars[key].set(converted_value)
                                    feedback.add_change_entry(
                                        key, str(old_value), str(converted_value), "success"
                                    )
                                    params_updated += 1
                            else:
                                feedback.add_change_entry(
                                    key, "", "Invalid value", "warning"
                                )
                        except Exception as e:
                            feedback.add_change_entry(
                                key, "", f"ERROR: {str(e)}", "error"
                            )
                    else:
                        feedback.add_change_entry(
                            key, "", "Unknown parameter", "warning"
                        )
                    
                    progress = 20 + (i * 30 / max(total_params, 1))
                    feedback.update_progress(progress)

                feedback.add_section("KEYBINDS")
                keybinds_updated = 0
                keybinds_data = settings.get("keybinds", {})
                
                total_keybinds = len(keybinds_data)
                for i, (key, value) in enumerate(keybinds_data.items()):
                    if key in self.default_keybinds and isinstance(value, str):
                        if key in self.dig_tool.keybind_vars:
                            old_value = self.dig_tool.keybind_vars[key].get()
                            self.dig_tool.keybind_vars[key].set(value)
                            feedback.add_change_entry(key, old_value, value, "success")
                            keybinds_updated += 1
                        else:
                            feedback.add_change_entry(key, "", "Keybind var not found", "warning")
                    else:
                        feedback.add_change_entry(key, "", "Invalid keybind", "warning")
                    
                    progress = 50 + (i * 20 / max(total_keybinds, 1))
                    feedback.update_progress(progress)

                feedback.add_section("CONFIGURATION")
                feedback.update_progress(70, "Loading configuration settings...")
                
                if "game_area" in settings and self.validate_game_area(settings["game_area"]):
                    old_area = self.dig_tool.game_area
                    self.dig_tool.game_area = tuple(settings["game_area"])
                    self.dig_tool.update_area_info()
                    if hasattr(self.dig_tool, "preview_btn"):
                        self.dig_tool.preview_btn.config(state=tk.NORMAL)
                    if hasattr(self.dig_tool, "debug_btn"):
                        self.dig_tool.debug_btn.config(state=tk.NORMAL)
                    if (
                        not self.dig_tool.main_loop_thread
                        or not self.dig_tool.main_loop_thread.is_alive()
                    ):
                        if hasattr(self.dig_tool, "start_threads"):
                            self.dig_tool.start_threads()
                    
                    feedback.add_change_entry(
                        "Game Area",
                        str(old_area) if old_area else "None",
                        str(self.dig_tool.game_area),
                        "success",
                    )
                else:
                    feedback.add_text("✗ Game Area: Not found or invalid", "warning")

                if "sell_button_position" in settings and self.validate_position(settings["sell_button_position"]):
                    old_pos = getattr(self.dig_tool.automation_manager, "sell_button_position", None)
                    self.dig_tool.automation_manager.sell_button_position = tuple(settings["sell_button_position"])
                    self.dig_tool.update_sell_info()
                    
                    feedback.add_change_entry(
                        "Sell Button",
                        str(old_pos) if old_pos else "None",
                        str(tuple(settings["sell_button_position"])),
                        "success",
                    )
                else:
                    feedback.add_text("✗ Sell Button: Not found or invalid", "warning")

                if "cursor_position" in settings and self.validate_position(settings["cursor_position"]):
                    old_pos = getattr(self.dig_tool, "cursor_position", None)
                    self.dig_tool.cursor_position = tuple(settings["cursor_position"])
                    self.dig_tool.update_cursor_info()
                    
                    feedback.add_change_entry(
                        "Cursor Position",
                        str(old_pos) if old_pos else "None",
                        str(tuple(settings["cursor_position"])),
                        "success",
                    )
                else:
                    feedback.add_text("✗ Cursor Position: Not found or invalid", "warning")

                if "walk_pattern" in settings and hasattr(self.dig_tool, "walk_pattern_var"):
                    try:
                        pattern = settings["walk_pattern"]
                        old_pattern = self.dig_tool.walk_pattern_var.get()
                        if (
                            hasattr(self.dig_tool.automation_manager, "walk_patterns")
                            and pattern in self.dig_tool.automation_manager.walk_patterns
                        ):
                            self.dig_tool.walk_pattern_var.set(pattern)
                            feedback.add_change_entry(
                                "Walk Pattern", old_pattern, pattern, "success"
                            )
                        else:
                            feedback.add_text(
                                f"✗ Walk Pattern: Unknown pattern '{pattern}'", "warning"
                            )
                    except Exception:
                        feedback.add_text("✗ Walk Pattern: Invalid data", "warning")
                else:
                    feedback.add_text("✗ Walk Pattern: Not found", "warning")

                feedback.update_progress(90, "Finalizing...")
                
                self.update_setting_states()
                
                if hasattr(self.dig_tool, 'apply_keybinds'):
                    self.dig_tool.apply_keybinds()

                feedback.update_progress(100, "Import completed successfully!")
                
                total_success = params_updated + keybinds_updated
                feedback.add_section("COMPLETION")
                feedback.add_text(f"✓ Parameters imported: {params_updated}", "success")
                feedback.add_text(f"✓ Keybinds imported: {keybinds_updated}", "success")
                feedback.add_text(f"✓ Total items imported: {total_success}", "info")
                
                feedback.operation_complete(success=True)
                
                filename = os.path.basename(filepath)
                self.dig_tool.update_status(f"Settings imported from {filename} - See details window")
                
                return True

            except json.JSONDecodeError:
                feedback.show_error("Invalid JSON", "The selected file contains invalid JSON data")
                return False
            except Exception as e:
                feedback.show_error("Import Failed", str(e))
                logger.error(f"Error importing settings from file: {e}")
                return False

        threading.Thread(target=import_process, daemon=True).start()

        return True
