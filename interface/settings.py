import json
import os
import re
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import threading
import time
import ast
import subprocess
from utils.debug_logger import logger
from utils.pattern_utils import update_walk_pattern_dropdown, open_custom_pattern_manager
from utils.input_management import apply_keybinds
from utils.ui_management import update_area_info, update_sell_info, update_cursor_info
from utils.config_management import get_param

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
            "debug_enabled": False,
            "screenshot_fps": 240,
            "auto_sell_enabled": False,
            "sell_every_x_digs": 10,
            "sell_delay": 1000,
            "auto_sell_method": "button_click",
            "auto_sell_ui_sequence": "down,up,enter",
            "auto_sell_target_engagement_enabled": True,
            "auto_sell_target_engagement_timeout": 120.0, 
            # Otsu detection parameters
            "use_otsu_detection": False,
            "otsu_min_area": 50,
            "otsu_max_area": "",
            "otsu_morph_kernel_size": 3,
            "otsu_adaptive_area": True,
            "otsu_area_percentile": 0.1,
            "otsu_disable_color_lock": False,
            # Color picker detection parameters
            "use_color_picker_detection": False,
            "picked_color_rgb": "",  # RGB color in hex format (e.g., "#FF0000")
            "color_tolerance": 30,
            "auto_walk_enabled": False,
            "walk_duration": 500,
            "max_wait_time": 5000,
            "dynamic_walkspeed_enabled": False,
            "initial_item_count": 0,
            "initial_walkspeed_decrease": 0.0,
            "auto_shovel_enabled": False,
            "shovel_slot": 1,
            "shovel_timeout": 5,
            "auto_rejoin_enabled": False,
            "roblox_server_link": "",
            "rejoin_check_interval": 30,
            "auto_rejoin_restart_delay": 60,
            "auto_rejoin_discord_notifications": True,
            "user_id": "",
            "server_id": "",
            "webhook_url": "",
            "milestone_interval": 100,
            "money_area": None,
            "item_area": None,
            "use_custom_cursor": False,
            "shovel_equip_mode": "double",
            "include_screenshot_in_discord": False,
            "enable_money_detection": False,
            "enable_item_detection": False,
            "notification_rarities": ["scarce", "legendary", "mythical", "divine", "prismatic"]
        }

        self.param_descriptions = {
            "line_sensitivity": "How sharp the contrast must be to be considered a line. Higher values = less sensitive to weak edges.",
            "line_detection_offset": "Pixels to offset the detected line position. Positive = right, negative = left. Decimals allowed for precise positioning.",
            "zone_min_width": "The minimum pixel width for a valid target zone. Smaller zones will be ignored.",
            "max_zone_width_percent": "The maximum width of a target zone as a percent of the capture width. Values above 100% allow detecting zones wider than the capture area (max 200%).",
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
            "debug_enabled": "Save screenshots and debug information for every click performed.",
            "screenshot_fps": "Target frames per second for screenshot capture. Higher = lower latency but more CPU usage.",
            "auto_sell_enabled": "Automatically sell items after a certain number of digs.",
            "sell_every_x_digs": "Number of digs before auto-selling items.",
            "sell_delay": "Delay in milliseconds before clicking the sell button.",
            "auto_sell_method": "Method for auto-selling: 'button_click' (click specific position) or 'ui_navigation' (use keyboard shortcuts).",
            "auto_sell_ui_sequence": "Keyboard sequence for UI navigation auto-sell. Use comma-separated keys from: down, up, left, right, enter. Example: 'down,up,enter'. Backslash keys are automatically added.",
            "auto_sell_target_engagement_enabled": "Enable waiting for target engagement after auto-sell completion. When disabled, auto-sell will not wait for re-engagement. Helpful in casews where inventory might stay open.",
            "auto_sell_target_engagement_timeout": "Time to wait for target engagement after auto-sell completion (seconds). If no engagement detected, applies auto-sell fallback to re-close inventory.",
            "auto_walk_enabled": "Automatically move around while digging.",
            "walk_duration": "Default duration to hold down key presses (milliseconds). Used as base duration unless custom durations are set for individual keys.",
            "max_wait_time": "Maximum time to wait for target engagement after clicking (milliseconds). If target isn't engaged within this time, the pattern advances to the next step.",
            "dynamic_walkspeed_enabled": "Apply a mathematical formula to determine the decreased walkspeed after X items.",
            "initial_item_count": "Starting item count for walkspeed calculation. Useful if you already have items collected.",
            # Otsu detection help text
            "use_otsu_detection": "Use Otsu's automatic thresholding instead of manual saturation threshold. Can be more adaptive to different lighting conditions.",
            "otsu_min_area": "Minimum area (pixels) for detected regions when using Otsu. Smaller regions will be filtered out.",
            "otsu_max_area": "Maximum area (pixels) for detected regions when using Otsu. Leave empty for no upper limit.",
            "otsu_morph_kernel_size": "Size of morphological operations kernel for noise reduction. 0 to disable, higher values = more smoothing.",
            "otsu_adaptive_area": "Use adaptive area filtering based on image size instead of fixed pixel values.",
            "otsu_area_percentile": "Minimum area as percentage of image size when using adaptive area filtering.",
            "otsu_disable_color_lock": "Disable color locking for Otsu detection. When enabled, detection runs continuously without locking to specific colors.",
            # Color picker detection help text
            "use_color_picker_detection": "Use a specific color picked from the screen. Click 'Pick Color' to select a target color.",
            "picked_color_rgb": "The RGB color value sampled from a screen area (automatically set when using Sample Area button).",
            "color_tolerance": "Tolerance for color matching. Higher values = more colors will match, lower = more precise matching.",
            "initial_walkspeed_decrease": "Additional walkspeed decrease factor (0.0-1.0) added on top of the formula. Higher = slower movement.",
            "user_id": "Discord user ID for notifications (optional - leave blank for no ping).",
            "server_id": "Discord server ID for message links (optional - leave blank to disable message links).",
            "webhook_url": "Discord webhook URL for sending notifications.",
            "money_area": "Selected screen area for money detection in Discord notifications.",
            "item_area": "Selected screen area for item detection in Discord notifications.",
            "enable_money_detection": "Enable automatic detection and notification of money values during digging.",
            "enable_item_detection": "Enable automatic detection and notification of rare items during digging.",
            "notification_rarities": "Select which item rarities will trigger Discord notifications when found.",
            "auto_shovel_enabled": "Automatically re-equip shovel when no activity detected for specified time.",
            "shovel_slot": "Hotbar slot number (0-9) where your shovel is located. 0 = slot 10.",
            "shovel_timeout": "Minutes of inactivity before auto-equipping shovel (based on clicks, digs, and target detection).",
            "milestone_interval": "Send Discord notification every X digs (milestone notifications).",
            "target_fps": "Your game's FPS for prediction calculations. Higher FPS = more precise predictions. Does not affect screenshot rate.",
            "use_custom_cursor": "Move cursor to set position before clicking when enabled. Cannot be used with Auto-Walk.",
            "shovel_equip_mode": "Whether to press the shovel slot key once ('single') or twice ('double') when re-equipping.",
            "include_screenshot_in_discord": "When enabled, screenshots of your game will be included in Discord milestone notifications.",
            "auto_rejoin_enabled": "Automatically rejoin Roblox servers when disconnected or kicked.",
            "roblox_server_link": "Roblox server link to rejoin (supports share links and direct game URLs).",
            "rejoin_check_interval": "How often to check for disconnection and attempt rejoining (minimum 10 seconds).",
            "auto_rejoin_restart_delay": "Seconds to wait before restarting automation after successful rejoin (minimum 5 seconds).",
            "auto_rejoin_discord_notifications": "Send Discord notifications for disconnections and rejoin attempts."
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

    def get_default(self, key, is_keybind=False):
        return (self.default_keybinds if is_keybind else self.default_params).get(key)

    def get_default_value(self, key):
        return self.get_default(key)

    def get_default_keybind(self, key):
        return self.get_default(key, True)

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

    def get_description(self, key, is_keybind=False):
        descriptions = self.keybind_descriptions if is_keybind else self.param_descriptions
        return descriptions.get(key, "No description available.")

    def get_keybind_description(self, key):
        return self.get_description(key, True)

    def load_icon(self, icon_path, size=(32, 32)):
        try:
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                img = img.resize(size, Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
        except Exception as e:
            logger.error(f"Error loading icon from {icon_path}: {e}")
        return None

    def _get_conflict_rules(self):
        return {
            "use_custom_cursor": {
                "conflicts_with": "auto_walk_enabled",
                "tooltip": "DISABLED: Cannot use Custom Cursor while Auto-Walk is enabled. Disable Auto-Walk first."
            },
            "auto_walk_enabled": {
                "conflicts_with": "use_custom_cursor", 
                "tooltip": "DISABLED: Cannot use Auto-Walk while Custom Cursor is enabled. Disable Custom Cursor first."
            },
            "auto_sell_target_engagement_timeout": {
                "depends_on": "auto_sell_target_engagement_enabled",
                "tooltip": "DISABLED: Target engagement timeout is disabled. Enable 'Auto Sell Target Engagement' first."
            }
        }

    def get_conflict_tooltip(self, setting_key):
        rules = self._get_conflict_rules()
        return rules.get(setting_key, {}).get("tooltip", "")

    def is_setting_conflicted(self, setting_key):
        rules = self._get_conflict_rules()
        rule = rules.get(setting_key, {})
        
        if "conflicts_with" in rule:
            return self.dig_tool.param_vars.get(rule["conflicts_with"], tk.BooleanVar()).get()
        elif "depends_on" in rule:
            return not self.dig_tool.param_vars.get(rule["depends_on"], tk.BooleanVar()).get()
        
        return False

    def update_setting_states(self):
        conflict_rules = self._get_conflict_rules()
        
        for setting_key in conflict_rules.keys():
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

    def get_local_param(self, key):
        try:
            return get_param(self.dig_tool, key)
        except Exception as e:
            logger.error(f"Error getting parameter {key}: {e}")
            return self.default_params.get(key, 0)

    def _get_multi_checkbox_params(self):
        return ["notification_rarities"]

    def _normalize_multi_checkbox_value(self, value):
        if isinstance(value, list):
            return json.dumps(value)
        elif isinstance(value, str):
            try:
                parsed = json.loads(value)
                return json.dumps(parsed)
            except (json.JSONDecodeError, TypeError):
                return json.dumps([])
        else:
            return json.dumps([])

    def _validate_coordinates(self, coords, expected_length, validate_area=False, validate_dimensions=False):
        if not coords or not isinstance(coords, (list, tuple)) or len(coords) != expected_length:
            return False
        try:
            if not all(isinstance(x, (int, float)) and x >= 0 for x in coords):
                return False
            if validate_area and expected_length == 4:
                x1, y1, x2, y2 = coords
                return x2 > x1 and y2 > y1
            if validate_dimensions and expected_length == 4:
                x, y, width, height = coords
                return width > 0 and height > 0
            return True
        except (ValueError, TypeError):
            return False

    def validate_game_area(self, area):
        return self._validate_coordinates(area, 4, validate_area=True)

    def validate_position(self, position):
        return self._validate_coordinates(position, 2)

    def validate_window_position(self, position):
        return self._validate_coordinates(position, 4, validate_dimensions=True)

    def _get_validation_rules(self):
        return {
            "special_cases": {
                "picked_color_rgb": lambda v: v in ["", None] or bool(re.match(r"^#[0-9A-Fa-f]{6}$", v)),
                "otsu_max_area": lambda v: v in ["", None] or (isinstance(v, (int, str)) and int(v) >= 1),
                "auto_sell_method": lambda v: isinstance(v, str) and v in ["button_click", "ui_navigation"],
                "auto_sell_ui_sequence": self._validate_ui_sequence,
                "notification_rarities": self._validate_rarities,
                "money_area": lambda v: self._validate_area_param(v),
                "item_area": lambda v: self._validate_area_param(v),
                "initial_walkspeed_decrease": lambda v: 0.0 <= float(v) <= 1.0,
                "initial_item_count": lambda v: int(v) >= 0,
                "roblox_server_link": self._validate_roblox_link
            },
            "int_ranges": {
                ("min_zone_height_percent", "sweet_spot_width_percent"): (0, 100),
                ("max_zone_width_percent",): (0, 200),
                ("milestone_interval",): (1, None),
                ("rejoin_check_interval",): (10, None),
                ("auto_rejoin_restart_delay",): (5, None),
                ("shovel_slot",): (0, 9),
                ("shovel_timeout",): (1, None)
            },
            "int_params": [
                "line_sensitivity", "zone_min_width", "post_click_blindness", "sell_every_x_digs",
                "sell_delay", "walk_duration", "max_wait_time", "otsu_min_area", "otsu_morph_kernel_size", "color_tolerance",
                "auto_rejoin_restart_delay", "shovel_slot", "shovel_timeout", "target_fps", "screenshot_fps"
            ],
            "float_ranges": {
                ("velocity_width_multiplier",): (0.0, 5.0),
                ("zone_smoothing_factor",): (0.0, 2.0),
                ("prediction_confidence_threshold",): (0.0, 1.0),
                ("otsu_area_percentile",): (0.01, 10.0)
            },
            "float_params": ["saturation_threshold", "line_detection_offset", "line_exclusion_radius", "velocity_max_factor", "auto_sell_target_engagement_timeout"],
            "bool_params": [
                "prediction_enabled", "main_on_top", "preview_on_top", "debug_on_top", "debug_enabled",
                "auto_sell_enabled", "auto_sell_target_engagement_enabled", "auto_walk_enabled", "use_custom_cursor",
                "auto_shovel_enabled", "use_otsu_detection", "otsu_adaptive_area", "otsu_disable_color_lock", "use_color_picker_detection",
                "enable_money_detection", "enable_item_detection", "auto_rejoin_enabled", "auto_rejoin_discord_notifications"
            ],
            "string_params": ["user_id", "server_id", "webhook_url", "roblox_server_link"]
        }

    def _validate_ui_sequence(self, value):
        if not isinstance(value, str) or not value.strip():
            return False
        valid_keys = {"down", "up", "left", "right", "enter"}
        keys = [k.strip().lower() for k in value.split(',') if k.strip()]
        return keys and all(k in valid_keys for k in keys)

    def _validate_rarities(self, value):
        valid_rarities = {"scarce", "legendary", "mythical", "divine", "prismatic"}
        
        if isinstance(value, list):
            return all(isinstance(rarity, str) and rarity.lower() in valid_rarities for rarity in value)
        elif isinstance(value, str):
            if not value.strip():
                return True
            try:
                parsed_list = json.loads(value)
                return (isinstance(parsed_list, list) and 
                       all(isinstance(rarity, str) and rarity.lower() in valid_rarities for rarity in parsed_list))
            except (json.JSONDecodeError, TypeError):
                return False
        return False

    def _validate_area_param(self, value):
        if value in [None, "None", ""]:
            return True
        if isinstance(value, str):
            try:
                value = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                return False
        return (isinstance(value, (list, tuple)) and len(value) == 4 and 
                all(isinstance(x, (int, float)) and x >= 0 for x in value))

    def _validate_roblox_link(self, value):
        if not isinstance(value, str) or not value.strip():
            return True
        
        value = value.strip()
        if value.startswith('roblox://'):
            return True
        
        if ('roblox.com/share?' in value or 'roblox.com/games/' in value):
            return True
        
        return False

    def validate_param_value(self, key, value):
        try:
            rules = self._get_validation_rules()
            
            if key in rules["special_cases"]:
                return rules["special_cases"][key](value)
            
            if key in rules["bool_params"]:
                return isinstance(value, bool)
            
            if key in rules["string_params"]:
                return isinstance(value, str)
            
            if key in rules["int_params"]:
                return int(value) >= 0
            
            for param_group, (min_val, max_val) in rules["int_ranges"].items():
                if key in param_group:
                    val = int(value)
                    return (min_val is None or val >= min_val) and (max_val is None or val <= max_val)
            
            if key in rules["float_params"]:
                float(value)
                return True
            
            for param_group, (min_val, max_val) in rules["float_ranges"].items():
                if key in param_group:
                    val = float(value)
                    return min_val <= val <= max_val
            
            return True
        except (ValueError, TypeError):
            return False

    def validate_keybind(self, key, value):
        if not isinstance(value, str) or len(value.strip()) == 0:
            return False
        return key in self.default_keybinds

    def refresh_pattern_dropdown(self):
        self.dig_tool.automation_manager.auto_load_patterns()
        update_walk_pattern_dropdown(self.dig_tool)
        self.dig_tool.update_status("Pattern list refreshed!")

    def open_custom_pattern_manager(self):
        if hasattr(self.dig_tool, "open_custom_pattern_manager"):
            open_custom_pattern_manager(self.dig_tool)

    def export_settings(self):
        options_dialog = ExportOptionsDialog(self.dig_tool.root, self.dig_tool)
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

        feedback = SettingsFeedbackWindow(self.dig_tool, "Exporting Settings")
        feedback.show_window()

        def export_process():
            try:
                feedback.update_progress(10, "Preparing settings data...")
                time.sleep(0.1)

                settings = {}

                settings["params"] = {}

                if export_options and export_options.get("keybinds", False):
                    settings["keybinds"] = {}

                if export_options and export_options.get("configuration", False):
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
                    settings["money_area"] = getattr(
                        self.dig_tool.money_ocr, "money_area", None
                    ) if hasattr(self.dig_tool, "money_ocr") else None
                    settings["item_area"] = getattr(
                        self.dig_tool.item_ocr, "item_area", None
                    ) if hasattr(self.dig_tool, "item_ocr") else None

                feedback.add_section("PARAMETERS")
                feedback.update_progress(20, "Processing parameters...")

                total_params = len(self.default_params)
                for i, key in enumerate(self.default_params.keys()):
                    try:
                        value = get_param(self.dig_tool, key)

                        if (
                            key in ["user_id", "server_id", "webhook_url", "milestone_interval", "money_area", "item_area", "include_screenshot_in_discord", "notification_rarities"]
                            and export_options
                            and not export_options.get("discord", True)
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
                    except Exception as e:
                        settings["params"][key] = self.default_params.get(key)
                        feedback.add_change_entry(key, "", f"ERROR: {e}", "error")

                    progress = 20 + (i * 30 / total_params)
                    feedback.update_progress(progress)
                    time.sleep(0.02)

                if export_options and export_options.get("keybinds", False):
                    feedback.add_section("KEYBINDS")
                    feedback.update_progress(50, "Processing keybinds...")

                    total_keybinds = len(self.default_keybinds)
                    for i, key in enumerate(self.default_keybinds.keys()):
                        try:
                            if key in self.dig_tool.keybind_vars:
                                value = self.dig_tool.keybind_vars[key].get()
                                from utils.config_management import validate_keybind
                                if validate_keybind(key, value):
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

                if export_options and export_options.get("configuration", False):
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
                if export_options and export_options.get("parameters", False):
                    included_items.append("Parameters")
                if export_options and export_options.get("keybinds", False):
                    included_items.append("Keybinds")
                if export_options and export_options.get("discord", False):
                    included_items.append("Discord Info")
                if export_options and export_options.get("configuration", False):
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

        feedback = SettingsFeedbackWindow(self.dig_tool, "Importing Settings")
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

                position_keys = ["game_area", "sell_button_position", "cursor_position"]
                found_position_keys = []
                for key in position_keys:
                    if key in settings:
                        found_position_keys.append(key)

                if found_position_keys:
                    from tkinter import messagebox
                    warning_message = (
                        f"This configuration file contains position data that may not be accurate for your setup:\n\n"
                        f"{', '.join(found_position_keys)}\n\n"
                        f"These positions are specific to screen resolution and game window placement. "
                        f"You may need to reconfigure these settings after import."
                    )
                    
                    messagebox.showwarning(
                        "Position Data Warning", 
                        warning_message
                    )

                feedback.add_section("PARAMETERS")
                params_loaded = 0
                params_failed = []

                total_params = len(settings.get("params", {}))
                for i, (key, value) in enumerate(settings.get("params", {}).items()):
                    if key in self.dig_tool.param_vars:
                        try:
                            param_var = self.dig_tool.param_vars[key]
                            old_value = param_var.get()


                            try:
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
                                    param_var.set(converted_value)
                                elif isinstance(param_var, tk.DoubleVar):
                                    converted_value = float(value)
                                    param_var.set(converted_value)
                                elif isinstance(param_var, tk.IntVar):
                                    converted_value = int(
                                        float(str(value).replace("JS:", ""))
                                    )
                                    param_var.set(converted_value)
                                else:
                                    if key in self._get_multi_checkbox_params():
                                        converted_value = self._normalize_multi_checkbox_value(value)
                                        param_var.set(converted_value)
                                    else:
                                        converted_value = str(value)
                                        param_var.set(converted_value)
                                
                                feedback.add_change_entry(
                                    key, str(old_value), str(converted_value), "success"
                                )
                                params_loaded += 1
                            except (ValueError, TypeError) as conv_error:
                                logger.error(f"Error setting parameter {key}: {conv_error}")
                                feedback.add_change_entry(
                                    key, str(old_value), f"ERROR: {conv_error}", "error"
                                )
                                params_failed.append(key)

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

                if 'money_area' in self.dig_tool.param_vars:
                    try:
                        money_area_str = self.dig_tool.param_vars['money_area'].get()
                        if money_area_str and money_area_str != "None" and hasattr(self.dig_tool, "money_ocr"):
                            money_area = ast.literal_eval(money_area_str)
                            if isinstance(money_area, (tuple, list)) and len(money_area) == 4:
                                self.dig_tool.money_ocr.money_area = tuple(money_area)
                                if not self.dig_tool.money_ocr.initialized:
                                    self.dig_tool.money_ocr.initialize_ocr()
                    except Exception as e:
                        logger.warning(f"Failed to apply money area to OCR: {e}")

                if 'item_area' in self.dig_tool.param_vars:
                    try:
                        item_area_str = self.dig_tool.param_vars['item_area'].get()
                        if item_area_str and item_area_str != "None" and hasattr(self.dig_tool, "item_ocr"):
                            item_area = ast.literal_eval(item_area_str)
                            if isinstance(item_area, (tuple, list)) and len(item_area) == 4:
                                self.dig_tool.item_ocr.item_area = tuple(item_area)
                                if not self.dig_tool.item_ocr.initialized:
                                    self.dig_tool.item_ocr.initialize_ocr()
                    except Exception as e:
                        logger.warning(f"Failed to apply item area to OCR: {e}")

                self.update_setting_states()

                feedback.add_section("KEYBINDS")
                keybinds_loaded = 0
                keybinds_failed = []

                total_keybinds = len(settings.get("keybinds", {}))
                for i, (key, value) in enumerate(settings.get("keybinds", {}).items()):
                    from utils.config_management import validate_keybind
                    if key in self.dig_tool.keybind_vars and validate_keybind(
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

                    update_area_info(self.dig_tool)
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

                        update_sell_info(self.dig_tool)
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

                        update_cursor_info(self.dig_tool)
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

                apply_keybinds(self.dig_tool)

                update_walk_pattern_dropdown(self.dig_tool)

                total_failed = len(params_failed + keybinds_failed)
                total_success = params_loaded + keybinds_loaded
                
                config_loaded = sum([
                    area_loaded, sell_button_loaded, cursor_loaded, 
                    pattern_loaded
                ])
                total_success += config_loaded
                
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
        feedback = SettingsFeedbackWindow(self.dig_tool, "Resetting to Defaults")
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
                            
                            if key in self._get_multi_checkbox_params():
                                normalized_value = self._normalize_multi_checkbox_value(default_value)
                                self.dig_tool.param_vars[key].set(normalized_value)
                                feedback.add_change_entry(
                                    key, str(old_value), str(default_value), "success"
                                )
                            else:
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

                if hasattr(self.dig_tool, "game_area") and self.dig_tool.game_area:
                    try:
                        old_area = str(self.dig_tool.game_area)
                        self.dig_tool.game_area = None
                        feedback.add_change_entry(
                            "Game Area", old_area, "None", "success"
                        )
                
                        from interface.main_window import update_area_info
                        update_area_info(self.dig_tool)
                        if hasattr(self.dig_tool, "preview_btn"):
                            self.dig_tool.preview_btn.config(state=tk.DISABLED)
                        if hasattr(self.dig_tool, "debug_btn"):
                            self.dig_tool.debug_btn.config(state=tk.DISABLED)
                    except Exception as e:
                        feedback.add_text(f"✗ Game Area: Reset failed - {e}", "error")

            
                if hasattr(self.dig_tool, "automation_manager") and hasattr(self.dig_tool.automation_manager, "sell_button_position") and self.dig_tool.automation_manager.sell_button_position:
                    try:
                        old_pos = str(self.dig_tool.automation_manager.sell_button_position)
                        self.dig_tool.automation_manager.sell_button_position = None
                        feedback.add_change_entry(
                            "Sell Button Position", old_pos, "None", "success"
                        )
                        update_sell_info(self.dig_tool)
                    except Exception as e:
                        feedback.add_text(f"✗ Sell Button Position: Reset failed - {e}", "error")

             
                if hasattr(self.dig_tool, "cursor_position") and self.dig_tool.cursor_position:
                    try:
                        old_pos = str(self.dig_tool.cursor_position)
                        self.dig_tool.cursor_position = None
                        feedback.add_change_entry(
                            "Cursor Position", old_pos, "None", "success"
                        )
                    
                        update_cursor_info(self.dig_tool)
                    except Exception as e:
                        feedback.add_text(f"✗ Cursor Position: Reset failed - {e}", "error")

                feedback.update_progress(90, "Finalizing...")

                update_walk_pattern_dropdown(self.dig_tool)

                apply_keybinds(self.dig_tool)

                if hasattr(self.dig_tool, "main_window"):
                    for param in self._get_multi_checkbox_params():
                        if hasattr(self.dig_tool.main_window, f'{param}_checkbox_vars'):
                            checkbox_vars = getattr(self.dig_tool.main_window, f'{param}_checkbox_vars')
                            options = self.get_default_value(param)
                            self.dig_tool.main_window._update_multi_checkbox_display(param, options, checkbox_vars)

                self.save_all_settings()

                feedback.update_progress(
                    100,
                    f"Reset Complete! {params_reset} parameters, {keybinds_reset} keybinds, and configuration data reset.",
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
            for env_var in ["LOCALAPPDATA", "APPDATA"]:
                appdata_dir = os.environ.get(env_var)
                if appdata_dir and os.path.exists(appdata_dir):
                    self.settings_dir = os.path.join(appdata_dir, "DigTool")
                    return

            self.settings_dir = os.path.join(os.getcwd(), "settings")
            logger.warning("Using current directory for settings storage as fallback")
        except Exception as e:
            logger.error(f"Error setting up settings directory: {e}")
            self.settings_dir = os.path.join(os.getcwd(), "settings")

    def _ensure_settings_directory(self):
        try:
            directories = [
                self.settings_dir,
                os.path.join(self.settings_dir, "Auto Walk")
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
            
            self.auto_walk_dir = directories[1]
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

    def _validate_and_cleanup_settings(self):
        settings_file = os.path.join(self.settings_dir, "settings.json")
        if not os.path.exists(settings_file):
            return
        
        try:
            with open(settings_file, "r") as f:
                settings = json.load(f)
            
            settings_modified = False
            
            if "params" in settings:
                original_params = settings["params"].copy()
                cleaned_params = {}
                
                for key, value in original_params.items():
                    if key in self.default_params:
                        try:
                            if self.validate_param_value(key, value):
                                cleaned_params[key] = value
                            else:
                                cleaned_params[key] = self.default_params[key]
                                logger.warning(f"Invalid parameter {key} reset to default: {self.default_params[key]}")
                                settings_modified = True
                        except Exception:
                            cleaned_params[key] = self.default_params[key]
                            logger.warning(f"Invalid parameter {key} reset to default: {self.default_params[key]}")
                            settings_modified = True
                    else:
                        logger.warning(f"Unknown parameter {key} removed from settings")
                        settings_modified = True
                
                for key in self.default_params:
                    if key not in cleaned_params:
                        cleaned_params[key] = self.default_params[key]
                        logger.info(f"Missing parameter {key} added with default: {self.default_params[key]}")
                        settings_modified = True
                
                settings["params"] = cleaned_params
            else:
                settings["params"] = self.default_params.copy()
                logger.info("Missing params section added to settings")
                settings_modified = True
            
            if "keybinds" in settings:
                original_keybinds = settings["keybinds"].copy()
                cleaned_keybinds = {}
                
                for key, value in original_keybinds.items():
                    if key in self.default_keybinds:
                        from utils.config_management import validate_keybind
                        is_valid, _ = validate_keybind(key, value)
                        if is_valid:
                            cleaned_keybinds[key] = value
                        else:
                            cleaned_keybinds[key] = self.default_keybinds[key]
                            logger.warning(f"Invalid keybind {key} reset to default: {self.default_keybinds[key]}")
                            settings_modified = True
                    else:
                        logger.warning(f"Unknown keybind {key} removed from settings")
                        settings_modified = True
                
                for key in self.default_keybinds:
                    if key not in cleaned_keybinds:
                        cleaned_keybinds[key] = self.default_keybinds[key]
                        logger.info(f"Missing keybind {key} added with default: {self.default_keybinds[key]}")
                        settings_modified = True
                
                settings["keybinds"] = cleaned_keybinds
            else:
                settings["keybinds"] = self.default_keybinds.copy()
                logger.info("Missing keybinds section added to settings")
                settings_modified = True
            
            if "window_positions" not in settings:
                settings["window_positions"] = {}
                settings_modified = True
            
            if settings_modified:
                with open(settings_file, "w") as f:
                    json.dump(settings, f, indent=2)
                logger.info("Settings file validated and cleaned up")
            
        except Exception as e:
            logger.error(f"Failed to validate settings: {e}")
            logger.info("Creating new settings file with defaults")
            default_settings = {
                "params": self.default_params.copy(),
                "keybinds": self.default_keybinds.copy(),
                "window_positions": {}
            }
            try:
                with open(settings_file, "w") as f:
                    json.dump(default_settings, f, indent=2)
            except Exception as write_error:
                logger.error(f"Failed to create default settings file: {write_error}")

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
        self._validate_and_cleanup_settings()

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
                                elif isinstance(param_var, tk.DoubleVar):
                                    param_var.set(float(value))
                                elif isinstance(param_var, tk.IntVar):
                                    param_var.set(int(value))
                                elif isinstance(param_var, tk.StringVar):
                                    if key in self._get_multi_checkbox_params():
                                        param_var.set(self._normalize_multi_checkbox_value(value))
                                    else:
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
                        update_area_info(self.dig_tool)
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
                        update_sell_info(self.dig_tool)

                if "cursor_position" in settings and self.validate_position(
                    settings["cursor_position"]
                ):
                    self.dig_tool.cursor_position = tuple(settings["cursor_position"])
                    logger.debug(
                        f"Loaded cursor position: {self.dig_tool.cursor_position}"
                    )
                    if hasattr(self.dig_tool, "update_cursor_info"):
                        update_cursor_info(self.dig_tool)

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
                
            if hasattr(self.dig_tool, "money_ocr") and 'money_area' in self.dig_tool.param_vars:
                try:
                    money_area_str = self.dig_tool.param_vars['money_area'].get()
                    if money_area_str and money_area_str != "None":
                        money_area = ast.literal_eval(money_area_str)
                        if isinstance(money_area, (tuple, list)) and len(money_area) == 4:
                            self.dig_tool.money_ocr.money_area = tuple(money_area)
                            if not self.dig_tool.money_ocr.initialized:
                                self.dig_tool.money_ocr.initialize_ocr()
                            logger.info(f"Loaded money area from settings: {money_area}")
                except Exception as e:
                    logger.warning(f"Failed to load money area from settings: {e}")

            if hasattr(self.dig_tool, "item_ocr") and 'item_area' in self.dig_tool.param_vars:
                try:
                    item_area_str = self.dig_tool.param_vars['item_area'].get()
                    if item_area_str and item_area_str != "None":
                        item_area = ast.literal_eval(item_area_str)
                        if isinstance(item_area, (tuple, list)) and len(item_area) == 4:
                            self.dig_tool.item_ocr.item_area = tuple(item_area)
                            if not self.dig_tool.item_ocr.initialized:
                                self.dig_tool.item_ocr.initialize_ocr()
                            logger.info(f"Loaded item area from settings: {item_area}")
                except Exception as e:
                    logger.warning(f"Failed to load item area from settings: {e}")

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
        feedback = SettingsFeedbackWindow(self.dig_tool, "Importing Settings")
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
                
                position_keys = ["game_area", "sell_button_position", "cursor_position"]
                found_position_keys = []
                for key in position_keys:
                    if key in settings:
                        found_position_keys.append(key)

                if found_position_keys:
                    from tkinter import messagebox
                    warning_message = (
                        f"This configuration file contains position data that may not be accurate for your setup:\n\n"
                        f"{', '.join(found_position_keys)}\n\n"
                        f"These positions are specific to screen resolution and game window placement. "
                        f"You may need to reconfigure these settings after import."
                    )
                    
                    messagebox.showwarning(
                        "Position Data Warning", 
                        warning_message
                    )

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
                    update_area_info(self.dig_tool)
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
                    update_sell_info(self.dig_tool)
                    
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
                    update_cursor_info(self.dig_tool)
                    
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
                
                apply_keybinds(self.dig_tool)

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
