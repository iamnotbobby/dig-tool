import time
import threading
import autoit
import json
import os
import math
from tkinter import filedialog
from pynput.keyboard import Controller as KeyboardController, Key
from utils.debug_logger import logger
import ctypes
from utils.system_utils import send_click


def perform_click_action(
    delay, running, use_custom_cursor, cursor_position, click_lock
):
    if delay > 0:
        time.sleep(delay)

    if not running:
        return

    if use_custom_cursor and cursor_position:
        try:
            ctypes.windll.user32.SetCursorPos(*cursor_position)
        except:
            pass

    send_click()
    if click_lock.locked():
        click_lock.release()


class AutomationManager:
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance
        self.keyboard_controller = KeyboardController()
        self.walk_pattern_index = 0
        self.last_successful_direction = None

        self._preview_active = False
        self._stop_preview = False

        self.walk_patterns = {
            "_KC_Nugget_v1": [
                {"key": "w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
            ],
            "Brick_Pattern": [
                {"key": "a+shift", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "shift+w", "duration": None, "click": True},
            ],
            "Circuit_Pattern": [
                {"key": "shift", "duration": None, "click": True},
                {"key": "shift+w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "shift", "duration": None, "click": True},
                {"key": "d+shift", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "d+shift", "duration": None, "click": True},
                {"key": "d+shift", "duration": None, "click": True},
                {"key": "shift", "duration": None, "click": True},
                {"key": "d+shift", "duration": None, "click": True},
                {"key": "shift", "duration": None, "click": True},
                {"key": "s+shift", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "shift", "duration": None, "click": True},
                {"key": "shift+s", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
            ],
            "Spiral_Pattern": [
                {"key": "d+shift", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "shift", "duration": None, "click": False},
            ],
        }

        self.key_mapping = {
            "up": Key.up,
            "down": Key.down,
            "left": Key.left,
            "right": Key.right,
            "shift": Key.shift,
            "ctrl": Key.ctrl,
            "alt": Key.alt,
            "cmd": Key.cmd,
            "space": Key.space,
            "enter": Key.enter,
            "tab": Key.tab,
            "backspace": Key.backspace,
            "delete": Key.delete,
            "esc": Key.esc,
            "escape": Key.esc,
            "f1": Key.f1,
            "f2": Key.f2,
            "f3": Key.f3,
            "f4": Key.f4,
            "f5": Key.f5,
            "f6": Key.f6,
            "f7": Key.f7,
            "f8": Key.f8,
            "f9": Key.f9,
            "f10": Key.f10,
            "f11": Key.f11,
            "f12": Key.f12,
            "home": Key.home,
            "end": Key.end,
            "page_up": Key.page_up,
            "page_down": Key.page_down,
            "insert": Key.insert,
        }

        self.custom_patterns_file = None

        self.sell_button_position = None
        self.sell_count = 0
        self.is_selling = False
        self.is_walking = False
        self.current_status = "STOPPED"

        self.shiftlock_state = {
            "shift": False,
            "right_shift": False,
            "was_active_before_sell": False,
        }

        self.is_recording = False
        self.recorded_pattern = []
        self.recording_start_time = None
        self.recording_listener = None
        self.recording_hook = None

        self.last_dig_time = None
        self.last_click_time = None
        self.last_target_lock_time = None
        self.shovel_re_equipped = False
        self.shovel_re_equipped_time = None
        self.walking_lock = threading.Lock()

        self.pattern_loop_count = 0
        self.pattern_compensation_factor = 0.0

    def load_custom_patterns(self):
        try:
            auto_walk_dir = self.dig_tool.settings_manager.get_auto_walk_directory()
            auto_filepath = os.path.join(auto_walk_dir, "custom_patterns.json")

            if os.path.exists(auto_filepath):
                filepath = auto_filepath
                logger.info(f"Auto-loading custom patterns from: {filepath}")
            else:
                filepath = filedialog.askopenfilename(
                    title="Load Custom Patterns",
                    filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                )
                if not filepath:
                    return

            with open(filepath, "r") as f:
                raw_patterns = json.load(f)

                processed_patterns = {}
                for pattern_name, pattern_steps in raw_patterns.items():
                    processed_steps = []
                    for step in pattern_steps:
                        if isinstance(step, dict):
                            if "click" not in step:
                                step["click"] = True
                            processed_steps.append(step)
                        else:
                            processed_steps.append(
                                {"key": str(step), "duration": None, "click": True}
                            )
                    processed_patterns[pattern_name] = processed_steps

                self.walk_patterns.update(processed_patterns)
                self.custom_patterns_file = filepath
                logger.info(
                    f"Loaded {len(processed_patterns)} custom patterns from {filepath}"
                )
        except Exception as e:
            logger.error(f"Error loading custom patterns: {e}")
        except Exception as e:
            logger.error(f"Error loading custom patterns: {e}")

    def save_custom_patterns(self):
        try:
            auto_walk_dir = self.dig_tool.settings_manager.get_auto_walk_directory()

            if not self.custom_patterns_file:
                self.custom_patterns_file = os.path.join(
                    auto_walk_dir, "custom_patterns.json"
                )
                logger.info(
                    f"Auto-setting custom patterns file to: {self.custom_patterns_file}"
                )

            built_in_patterns = {"_KC_Nugget_v1"}
            custom_patterns = {
                name: pattern
                for name, pattern in self.walk_patterns.items()
                if name not in built_in_patterns
            }

            with open(self.custom_patterns_file, "w") as f:
                json.dump(custom_patterns, f, indent=2)
            logger.info(
                f"Saved {len(custom_patterns)} custom patterns to {self.custom_patterns_file}"
            )
            return True
        except Exception as e:
            logger.error(f"Error saving custom patterns: {e}")
            return False

    def add_custom_pattern(self, name, pattern):
        if not name or not pattern:
            return False, "Pattern name and moves cannot be empty"

        processed_pattern = []
        for step in pattern:
            if isinstance(step, dict):
                if "key" in step:
                    processed_pattern.append(
                        {
                            "key": step["key"].upper().strip(),
                            "duration": step.get("duration", None),
                        }
                    )
                else:
                    return False, "Invalid pattern step format: missing 'key' field"
            elif isinstance(step, str):
                if not step.strip():
                    return False, "Invalid pattern step: empty step not allowed"
                processed_pattern.append(
                    {"key": step.upper().strip(), "duration": None}
                )
            else:
                return False, "Invalid pattern step format: must be a string or dict"

        self.walk_patterns[name] = processed_pattern
        success = self.save_custom_patterns()

        if success:
            return True, f"Custom pattern '{name}' added successfully"
        else:
            return False, "Failed to save custom pattern"

    def delete_custom_pattern(self, name):
        built_in_patterns = {"_KC_Nugget_v1"}

        if name in built_in_patterns:
            return False, "Cannot delete built-in patterns"

        if name not in self.walk_patterns:
            return False, "Pattern not found"

        del self.walk_patterns[name]
        success = self.save_custom_patterns()

        if success:
            return True, f"Custom pattern '{name}' deleted successfully"
        else:
            return False, "Failed to save changes"

    def get_pattern_list(self):
        built_in_patterns = {"_KC_Nugget_v1"}
        hardcoded_custom_patterns = {
            "Brick_Pattern",
            "Circuit_Pattern",
            "Spiral_Pattern",
        }
        pattern_info = {}

        for name, pattern in self.walk_patterns.items():
            if name in built_in_patterns:
                pattern_type = "built-in"
            elif name in hardcoded_custom_patterns:
                pattern_type = "custom"
            else:
                pattern_type = "custom"

            pattern_info[name] = {
                "pattern": pattern,
                "type": pattern_type,
                "length": len(pattern),
            }

        return pattern_info

        return pattern_info

    def start_recording_pattern(self, allow_custom_keys=False, click_enabled=True):
        self.is_recording = True
        self.recorded_pattern = []
        self.recording_start_time = time.time()
        self.allow_custom_keys = allow_custom_keys
        self.record_click_enabled = click_enabled
        self.start_recording_keyboard_listener()
        logger.info(
            f"Started recording pattern (custom keys: {allow_custom_keys}, click enabled: {click_enabled})"
        )
        return True

    def start_recording_keyboard_listener(self):
        try:
            import keyboard

            self.pressed_keys = set()
            self.last_key_time = 0
            self.key_combination_timeout = 0.3

            def on_key_press(event):
                if self.is_recording and event.event_type == keyboard.KEY_DOWN:
                    key = event.name.lower()

                    should_record = False
                    if hasattr(self, "allow_custom_keys") and self.allow_custom_keys:
                        allowed_keys = [
                            "a",
                            "b",
                            "c",
                            "d",
                            "e",
                            "f",
                            "g",
                            "h",
                            "i",
                            "j",
                            "k",
                            "l",
                            "m",
                            "n",
                            "o",
                            "p",
                            "q",
                            "r",
                            "s",
                            "t",
                            "u",
                            "v",
                            "w",
                            "x",
                            "y",
                            "z",
                            "1",
                            "2",
                            "3",
                            "4",
                            "5",
                            "6",
                            "7",
                            "8",
                            "9",
                            "0",
                            "up",
                            "down",
                            "left",
                            "right",
                            "arrow up",
                            "arrow down",
                            "arrow left",
                            "arrow right",
                            "shift",
                            "left shift",
                            "right shift",
                            "ctrl",
                            "left ctrl",
                            "right ctrl",
                            "alt",
                            "left alt",
                            "right alt",
                            "f1",
                            "f2",
                            "f3",
                            "f4",
                            "f5",
                            "f6",
                            "f7",
                            "f8",
                            "f9",
                            "f10",
                            "f11",
                            "f12",
                            "space",
                            "enter",
                            "tab",
                            "backspace",
                            "delete",
                            "insert",
                            "home",
                            "end",
                            "page up",
                            "page down",
                            "escape",
                            ",",
                            ".",
                            "/",
                            ";",
                            "'",
                            "[",
                            "]",
                            "\\",
                            "=",
                            "-",
                            "`",
                            "kp_1",
                            "kp_2",
                            "kp_3",
                            "kp_4",
                            "kp_5",
                            "kp_6",
                            "kp_7",
                            "kp_8",
                            "kp_9",
                            "kp_0",
                            "kp_plus",
                            "kp_minus",
                            "kp_multiply",
                            "kp_divide",
                            "kp_enter",
                            "kp_decimal",
                        ]
                        should_record = key in allowed_keys
                    else:
                        should_record = key in ["w", "a", "s", "d"]

                    if should_record:
                        current_time = time.time()

                        self.pressed_keys.add(key)

                        time_since_last = (
                            current_time - self.last_key_time
                            if self.last_key_time > 0
                            else float("inf")
                        )

                        if time_since_last > self.key_combination_timeout:
                            if (
                                hasattr(self, "_pending_combination")
                                and self._pending_combination
                            ):
                                combination = "+".join(
                                    sorted(self._pending_combination)
                                )
                                self.record_movement(combination)
                            self._pending_combination = {key}
                        else:
                            if not hasattr(self, "_pending_combination"):
                                self._pending_combination = set()
                            self._pending_combination.add(key)

                        self.last_key_time = current_time

                        if hasattr(self, "_combination_timer"):
                            try:
                                self._combination_timer.cancel()
                            except:
                                pass

                        import threading

                        self._combination_timer = threading.Timer(
                            self.key_combination_timeout,
                            self._record_pending_combination,
                        )
                        self._combination_timer.start()

            def on_key_release(event):
                if self.is_recording and event.event_type == keyboard.KEY_UP:
                    key = event.name.lower()
                    self.pressed_keys.discard(key)

            self.recording_hook = keyboard.hook(
                lambda event: (
                    on_key_press(event)
                    if event.event_type == keyboard.KEY_DOWN
                    else on_key_release(event)
                )
            )

        except Exception as e:
            self.recording_hook = None
            pass

    def _record_pending_combination(self):
        try:
            if hasattr(self, "_pending_combination") and self._pending_combination:
                combination = "+".join(sorted(self._pending_combination))
                self.record_movement(combination)
                self._pending_combination = set()
        except Exception as e:
            pass

    def stop_recording_pattern(self):
        self.is_recording = False

        try:
            if hasattr(self, "_combination_timer"):
                self._combination_timer.cancel()
            if hasattr(self, "_pending_combination") and self._pending_combination:
                combination = "+".join(sorted(self._pending_combination))
                self.record_movement(combination)
                self._pending_combination = set()
        except:
            pass

        try:
            import keyboard

            if hasattr(self, "recording_hook") and self.recording_hook:
                keyboard.unhook(self.recording_hook)
                self.recording_hook = None
        except Exception as e:
            logger.warning(
                f"Warning: Could not unhook specific recording listener: {e}"
            )
            try:
                import keyboard

                if hasattr(self.dig_tool, "apply_keybinds"):
                    self.dig_tool.root.after(100, self.dig_tool.apply_keybinds)
            except:
                pass

        if hasattr(self, "pressed_keys"):
            self.pressed_keys.clear()

        pattern = self.recorded_pattern.copy()
        self.recorded_pattern = []
        logger.info(f"Stopped recording pattern")
        return pattern

    def record_movement(self, direction):
        if self.is_recording:
            click_enabled = getattr(self, "record_click_enabled", True)

            if isinstance(direction, str):
                normalized = direction.lower()

                if hasattr(self, "allow_custom_keys") and self.allow_custom_keys:
                    if normalized:
                        step = {
                            "key": normalized,
                            "duration": None,
                            "click": click_enabled,
                        }
                        self.recorded_pattern.append(step)
                        return True
                else:
                    if all(c in "wasd+" for c in normalized) and normalized:
                        step = {
                            "key": normalized,
                            "duration": None,
                            "click": click_enabled,
                        }
                        self.recorded_pattern.append(step)
                        return True
        return False

    def update_dig_activity(self):
        self.last_dig_time = time.time()
        self.shovel_re_equipped = False
        self.shovel_re_equipped_time = None
        logger.debug("Dig activity updated - auto-shovel flag reset")

    def update_click_activity(self):
        self.last_click_time = time.time()

    def update_target_lock_activity(self):
        self.last_target_lock_time = time.time()

    def should_re_equip_shovel(self):
        if not self.dig_tool.get_param("auto_shovel_enabled"):
            return False

        current_time = time.time()
        shovel_timeout = self.dig_tool.get_param("shovel_timeout") * 60

        if self.shovel_re_equipped and self.shovel_re_equipped_time:
            time_since_reequip = current_time - self.shovel_re_equipped_time
            fallback_timeout = shovel_timeout * 2

            if time_since_reequip > fallback_timeout:
                logger.warning(
                    f"Auto-shovel fallback triggered: No successful digs for {time_since_reequip:.0f}s after shovel re-equip. Resetting flag."
                )
                self.shovel_re_equipped = False
                self.shovel_re_equipped_time = None

        if self.shovel_re_equipped:
            return False

        time_since_last_dig = (
            current_time - self.last_dig_time if self.last_dig_time else float("inf")
        )

        no_recent_pickup = time_since_last_dig > shovel_timeout

        if no_recent_pickup:
            logger.info(
                f"Auto-shovel triggered: No item pickups for {time_since_last_dig:.0f}s (timeout: {shovel_timeout:.0f}s)"
            )

        return no_recent_pickup

    def re_equip_shovel(self, is_test=False):
        try:
            if not is_test and not self.dig_tool.running:
                return False

            if not self.find_and_focus_roblox_window():
                logger.warning("Could not focus Roblox window for shovel equip")

            shovel_slot = self.dig_tool.get_param("shovel_slot")
            if shovel_slot < 0 or shovel_slot > 9:
                logger.warning(f"Invalid shovel slot: {shovel_slot}")
                return False

            slot_key = str(shovel_slot) if shovel_slot > 0 else "0"
            equip_mode = self.dig_tool.get_param("shovel_equip_mode")

            logger.info(
                f"Re-equipping shovel from slot {shovel_slot} (key: {slot_key}) using {equip_mode} mode"
            )

            with self.walking_lock:
                time.sleep(0.1)

                self.keyboard_controller.press(slot_key)
                time.sleep(0.05)
                self.keyboard_controller.release(slot_key)

                if equip_mode == "double":
                    time.sleep(0.5)

                    self.keyboard_controller.press(slot_key)
                    time.sleep(0.05)
                    self.keyboard_controller.release(slot_key)

            self.shovel_re_equipped = True
            self.shovel_re_equipped_time = time.time()
            self.last_dig_time = time.time()

            mode_text = "double press" if equip_mode == "double" else "single press"
            self.dig_tool.update_status(
                f"Auto-equipped shovel from slot {shovel_slot} ({mode_text})"
            )
            logger.info(
                f"Auto-shovel completed: Equipped shovel from slot {shovel_slot} using {mode_text}"
            )
            return True

        except Exception as e:
            logger.error(f"Error re-equipping shovel: {e}")
            return False

    def get_current_status(self):
        if not self.dig_tool.running:
            return "STOPPED"
        elif self.is_recording:
            return f"RECORDING ({len(self.recorded_pattern)} moves)"
        elif self.is_selling:
            return "AUTO SELLING"
        elif self.is_walking:
            return "WALKING"
        elif self.dig_tool.get_param("auto_walk_enabled"):
            if self.dig_tool.get_param("auto_shovel_enabled"):
                current_time = time.time()
                shovel_timeout = self.dig_tool.get_param("shovel_timeout") * 60
                time_since_last_dig = (
                    current_time - self.last_dig_time
                    if self.last_dig_time
                    else float("inf")
                )

                if self.shovel_re_equipped and self.shovel_re_equipped_time:
                    time_since_reequip = current_time - self.shovel_re_equipped_time
                    fallback_timeout = shovel_timeout * 2
                    if time_since_reequip < fallback_timeout:
                        fallback_remaining = fallback_timeout - time_since_reequip
                        return (
                            f"AUTO WALKING (shovel fallback {fallback_remaining:.0f}s)"
                        )

                if (
                    time_since_last_dig >= shovel_timeout
                    and not self.shovel_re_equipped
                ):
                    return "AUTO WALKING (shovel ready)"
                elif time_since_last_dig < shovel_timeout:
                    remaining_time = shovel_timeout - time_since_last_dig
                    return f"AUTO WALKING (shovel {remaining_time:.0f}s)"
                else:
                    return "AUTO WALKING"
            else:
                return "AUTO WALKING"
        else:
            return "ACTIVE"

    def perform_walk_step(self, direction):
        try:
            with self.walking_lock:
                self.is_walking = True

                if self.is_recording:
                    self.record_movement(direction)
                    logger.debug(f"Recorded movement during walk: {direction}")

                walk_duration = self.dig_tool.get_param("walk_duration") / 1000.0

                if self.dig_tool.get_param("dynamic_walkspeed_enabled"):
                    base_duration = walk_duration

                    items_collected = self.dig_tool.dig_count
                    initial_item_count = (
                        self.dig_tool.get_param("initial_item_count") or 0
                    )
                    total_items = items_collected + initial_item_count

                    formula_reduction = self.calculate_walkspeed_multiplier(total_items)

                    initial_decrease = (
                        self.dig_tool.get_param("initial_walkspeed_decrease") or 0.0
                    )
                    initial_decrease = max(0.0, min(1.0, initial_decrease))

                    total_reduction = min(formula_reduction + initial_decrease, 0.99)

                    duration_multiplier = 1.0 + total_reduction

                    walk_duration = base_duration * duration_multiplier

                    if total_items > 35 or initial_decrease > 0:
                        logger.debug(
                            f"Dynamic walkspeed: total_items={total_items} (collected={items_collected}+initial={initial_item_count}), formula_reduction={formula_reduction:.3f}, initial_decrease={initial_decrease:.3f}, total_reduction={total_reduction:.3f}, multiplier={duration_multiplier:.2f}x, duration={walk_duration:.3f}s"
                        )

                if "+" in direction:
                    keys_to_press = direction.lower().split("+")
                    converted_keys = []

                    for key in keys_to_press:
                        key = key.strip()
                        if key:
                            try:
                                converted_key = self._convert_key_name(key)
                                converted_keys.append(converted_key)
                                self.keyboard_controller.press(converted_key)

                                if self._is_shift_key(key):
                                    self._toggle_shiftlock_on_shift_press(key)

                                logger.debug(f"Pressed key '{key}' -> {converted_key}")
                            except Exception as e:
                                logger.warning(f"Failed to press key '{key}': {e}")

                    time.sleep(walk_duration)

                    for converted_key in converted_keys:
                        try:
                            self.keyboard_controller.release(converted_key)
                        except Exception as e:
                            logger.warning(
                                f"Failed to release key {converted_key}: {e}"
                            )

                elif len(direction) == 1:
                    try:
                        converted_key = self._convert_key_name(direction.lower())
                        self.keyboard_controller.press(converted_key)

                        if self._is_shift_key(direction.lower()):
                            self._toggle_shiftlock_on_shift_press(direction.lower())

                        time.sleep(walk_duration)
                        self.keyboard_controller.release(converted_key)
                        logger.debug(f"Single key '{direction}' -> {converted_key}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to press/release single key '{direction}': {e}"
                        )
                else:
                    try:
                        converted_key = self._convert_key_name(direction.lower())
                        self.keyboard_controller.press(converted_key)

                        if self._is_shift_key(direction.lower()):
                            self._toggle_shiftlock_on_shift_press(direction.lower())
                        time.sleep(walk_duration)
                        self.keyboard_controller.release(converted_key)
                        logger.debug(f"Long key name '{direction}' -> {converted_key}")
                    except Exception:
                        keys_to_press = list(direction.lower())

                        for key in keys_to_press:
                            if key in "wasd":
                                try:
                                    self.keyboard_controller.press(key)
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to press legacy key '{key}': {e}"
                                    )

                        time.sleep(walk_duration)

                        for key in keys_to_press:
                            if key in "wasd":
                                try:
                                    self.keyboard_controller.release(key)
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to release legacy key '{key}': {e}"
                                    )

                time.sleep(0.05)

            self.is_walking = False
            return True

        except Exception as e:
            self.is_walking = False
            logger.error(f"Error in walk step: {e}")
            return False

    def get_next_walk_direction(self):
        current_pattern = getattr(self.dig_tool, "walk_pattern_var", None)
        if not current_pattern:
            pattern_name = "_KC_Nugget_v1"
        else:
            pattern_name = (
                current_pattern.get()
                if hasattr(current_pattern, "get")
                else "_KC_Nugget_v1"
            )

        pattern = self.walk_patterns.get(
            pattern_name, self.walk_patterns["_KC_Nugget_v1"]
        )

        step = pattern[self.walk_pattern_index]
        return step

    def get_current_walk_step(self):
        current_pattern = getattr(self.dig_tool, "walk_pattern_var", None)
        if not current_pattern:
            pattern_name = "_KC_Nugget_v1"
        else:
            pattern_name = (
                current_pattern.get()
                if hasattr(current_pattern, "get")
                else "_KC_Nugget_v1"
            )

        pattern = self.walk_patterns.get(
            pattern_name, self.walk_patterns["_KC_Nugget_v1"]
        )

        step = pattern[self.walk_pattern_index]
        return step

    def advance_walk_pattern(self):
        current_pattern = getattr(self.dig_tool, "walk_pattern_var", None)
        if not current_pattern:
            pattern_name = "_KC_Nugget_v1"
        else:
            pattern_name = (
                current_pattern.get()
                if hasattr(current_pattern, "get")
                else "_KC_Nugget_v1"
            )

        pattern = self.walk_patterns.get(
            pattern_name, self.walk_patterns["_KC_Nugget_v1"]
        )

        old_index = self.walk_pattern_index
        self.walk_pattern_index = (self.walk_pattern_index + 1) % len(pattern)

        if old_index > 0 and self.walk_pattern_index == 0:
            self.pattern_loop_count += 1
            self._update_pattern_compensation()
            logger.debug(
                f"Pattern loop completed. Loop count: {self.pattern_loop_count}, Compensation: {self.pattern_compensation_factor:.3f}"
            )

    def _update_pattern_compensation(self):
        if not self.dig_tool.get_param("pattern_loop_compensation_enabled"):
            return

        max_loops = self.dig_tool.get_param("pattern_loop_compensation_max_loops") or 8
        compensation_per_loop = (
            self.dig_tool.get_param("pattern_loop_compensation_rate") or 0.02
        )
        reset_threshold = (
            self.dig_tool.get_param("pattern_loop_compensation_reset_threshold") or 0.15
        )

        self.pattern_compensation_factor = min(
            self.pattern_loop_count * compensation_per_loop, reset_threshold
        )

        if self.pattern_compensation_factor >= reset_threshold:
            logger.info(
                f"Pattern compensation reset at {self.pattern_compensation_factor:.3f} after {self.pattern_loop_count} loops"
            )
            self.pattern_loop_count = 0
            self.pattern_compensation_factor = 0.0

            if self.dig_tool.get_param("pattern_loop_correction_step_enabled"):
                self._perform_correction_step()

    def is_auto_sell_ready(self):
        if not self.dig_tool.running:
            return False

        if not self.dig_tool.get_param("auto_sell_enabled"):
            return False

        if self.is_selling:
            return False

        if not self.sell_button_position:
            return False

        return True

    def can_auto_sell(self):
        auto_walk_enabled = self.dig_tool.get_param("auto_walk_enabled")
        auto_sell_enabled = self.dig_tool.get_param("auto_sell_enabled")

        if auto_sell_enabled and not auto_walk_enabled:
            self.dig_tool.update_status(
                "Auto-sell disabled: Auto-walk must be enabled!"
            )
            return False

        return auto_sell_enabled and self.sell_button_position is not None

    def autoit_click(self, x, y, retries=3):
        for attempt in range(retries):
            try:
                logger.debug(f"AutoIt click attempt {attempt + 1}: Target: ({x}, {y})")

                try:
                    autoit.mouse_move(x, y, speed=2)
                    time.sleep(0.1)

                    current_pos = autoit.mouse_get_pos()
                    tolerance = 5

                    if (
                        abs(current_pos[0] - x) <= tolerance
                        and abs(current_pos[1] - y) <= tolerance
                    ):
                        autoit.mouse_click("left", x, y, speed=2)
                        time.sleep(0.1)
                        logger.debug(f"AutoIt click successful at {current_pos}")
                        return True
                    else:
                        logger.warning(
                            f"AutoIt position verification: Expected ({x}, {y}), Got {current_pos}"
                        )
                        if attempt < retries - 1:
                            time.sleep(0.2)
                            continue

                except (OSError, WindowsError, Exception) as com_error:
                    logger.warning(
                        f"AutoIt COM error on attempt {attempt + 1}: {com_error}"
                    )
                    try:
                        from utils.system_utils import send_click

                        send_click(x, y)
                        logger.debug(f"Fallback click successful at ({x}, {y})")
                        return True
                    except Exception as fallback_error:
                        logger.error(f"Fallback click also failed: {fallback_error}")
                        if attempt < retries - 1:
                            time.sleep(0.2)
                            continue

            except Exception as e:
                logger.error(f"AutoIt click attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(0.2)
                    continue

        logger.error("All AutoIt click attempts failed")
        return False

    def perform_auto_sell(self):
        try:
            if self.is_selling:
                logger.warning("Auto-sell already in progress, skipping")
                return

            if not self.dig_tool.get_param("auto_sell_enabled"):
                logger.warning("Auto-sell aborted: Auto-sell is disabled")
                return

            if not self.sell_button_position:
                logger.warning("Auto-sell aborted: No sell button position set")
                return

            if not self.dig_tool.running:
                logger.warning("Auto-sell aborted: Tool is not running")
                return

            logger.info(f"Starting auto-sell sequence #{self.sell_count + 1}")
            self.is_selling = True
            self.dig_tool.update_status("Auto-selling...")

            time.sleep(0.1)

            with self.walking_lock:
                disabled_shifts = self.disable_active_shifts_for_sell()
                if disabled_shifts:
                    logger.info(f"Disabled shift keys for auto-sell: {disabled_shifts}")
                    time.sleep(0.2)

                logger.debug("Opening inventory with 'G' key")
                try:
                    autoit.send("g")
                except (OSError, WindowsError, Exception) as e:
                    logger.warning(
                        f"AutoIt send 'g' failed, using keyboard fallback: {e}"
                    )
                    self.keyboard_controller.press("g")
                    self.keyboard_controller.release("g")

                logger.debug("Brief delay for inventory to open")
                time.sleep(0.5)

                x, y = self.sell_button_position

                logger.debug(f"Performing AutoIt click at sell button: {x}, {y}")
                success = self.autoit_click(x, y)

                if success:
                    logger.info("Sell click successful")
                    time.sleep(2.5)
                    logger.debug("Closing inventory with 'G' key")
                    try:
                        autoit.send("g")
                    except (OSError, WindowsError, Exception) as e:
                        logger.warning(
                            f"AutoIt send 'g' failed, using keyboard fallback: {e}"
                        )
                        self.keyboard_controller.press("g")
                        self.keyboard_controller.release("g")
                    time.sleep(1.0)

                    restored_shifts = self.restore_shifts_after_sell()
                    if restored_shifts:
                        logger.info(
                            f"Restored shift keys after auto-sell: {restored_shifts}"
                        )
                        time.sleep(0.1)

                    self.sell_count += 1

                    sell_every_x_digs = self.dig_tool.get_param("sell_every_x_digs")
                    if sell_every_x_digs and sell_every_x_digs > 0:
                        items_sold = min(self.dig_tool.dig_count, sell_every_x_digs)
                        self.dig_tool.dig_count = max(
                            0, self.dig_tool.dig_count - items_sold
                        )
                        logger.info(
                            f"Auto-sell completed: sold {items_sold} items, remaining dig_count: {self.dig_tool.dig_count}"
                        )

                    self.dig_tool.update_status(
                        f"Auto-sell #{self.sell_count} completed"
                    )
                    logger.info(f"Auto-sell #{self.sell_count} completed successfully")
                else:
                    logger.error("Auto-sell failed: AutoIt click error")
                    self.dig_tool.update_status("Auto-sell failed: AutoIt click error")

            self.is_selling = False

            try:
                restored_shifts = self.restore_shifts_after_sell()
                if restored_shifts:
                    logger.info(
                        f"Restored shift keys after auto-sell error: {restored_shifts}"
                    )
            except Exception as restore_error:
                logger.warning(
                    f"Failed to restore shifts after auto-sell error: {restore_error}"
                )

        except Exception as e:
            self.is_selling = False

            try:
                restored_shifts = self.restore_shifts_after_sell()
                if restored_shifts:
                    logger.info(
                        f"Restored shift keys after auto-sell exception: {restored_shifts}"
                    )
            except Exception as restore_error:
                logger.warning(
                    f"Failed to restore shifts after auto-sell exception: {restore_error}"
                )

            error_msg = f"Error in auto-sell: {e}"
            logger.error(error_msg)
            self.dig_tool.update_status(f"Auto-sell failed: {e}")

    def test_sell_button_click(self):
        if not self.sell_button_position:
            self.dig_tool.update_status("Sell button not set!")
            return

        threading.Thread(target=self._test_sell_click_with_delay, daemon=True).start()

    def _test_sell_click_with_delay(self):
        x, y = self.sell_button_position
        logger.info(f"Testing AutoIt click at position: {x}, {y}")

        for i in range(5, 0, -1):
            self.dig_tool.update_status(
                f"Test click in {i} seconds... Position: ({x}, {y})"
            )
            time.sleep(1.0)

        self.dig_tool.update_status("Performing AutoIt test click...")
        logger.info(f"Executing AutoIt test click at: {x}, {y}")

        success = self.autoit_click(x, y)

        if success:
            self.dig_tool.update_status("AutoIt test click completed successfully!")
        else:
            self.dig_tool.update_status("AutoIt test click failed!")

    def test_shovel_equip(self):
        if not self.dig_tool.get_param("auto_shovel_enabled"):
            self.dig_tool.update_status("Auto-shovel is disabled!")
            return

        shovel_slot = self.dig_tool.get_param("shovel_slot")
        equip_mode = self.dig_tool.get_param("shovel_equip_mode")
        mode_text = "double press" if equip_mode == "double" else "single press"

        self.dig_tool.update_status(
            f"Testing shovel equip from slot {shovel_slot} ({mode_text})..."
        )

        threading.Thread(target=self._test_shovel_equip_with_delay, daemon=True).start()

    def _test_shovel_equip_with_delay(self):
        for i in range(3, 0, -1):
            self.dig_tool.update_status(f"Equipping shovel in {i} seconds...")
            time.sleep(1.0)

        self.dig_tool.update_status("Focusing Roblox window...")
        focus_success = self.find_and_focus_roblox_window()

        if focus_success:
            self.dig_tool.update_status("Roblox focused - waiting briefly...")
            time.sleep(0.5)
        else:
            self.dig_tool.update_status(
                "Warning: Could not focus Roblox - testing anyway..."
            )
            time.sleep(0.2)

        self.dig_tool.update_status("Testing shovel equip now...")
        success = self.re_equip_shovel(is_test=True)

        if success:
            self.dig_tool.update_status("Shovel equip test completed successfully!")
        else:
            self.dig_tool.update_status("Shovel equip test failed!")

    def send_key(self, key, duration=0.1):
        try:
            with self.walking_lock:
                self.keyboard_controller.press(key)
                time.sleep(duration)
                self.keyboard_controller.release(key)
            return True
        except Exception as e:
            logger.error(f"Key press failed: {e}")
            return False

    def get_mouse_position(self):
        try:
            return self.mouse_controller.position
        except Exception as e:
            logger.error(f"Get mouse position failed: {e}")
            return (0, 0)

    def calculate_walkspeed_multiplier(self, items_collected):
        x = items_collected

        if x <= 35:
            return 0.0
        elif x <= 50:
            return 0.30
        else:
            term1 = 0.6065 * math.exp(-0.0388 * (x - 35))
            term2 = 0.3835 * math.exp(-0.005000 * (x - 35))
            return 0.9900 - term1 - term2

    def cleanup(self):
        try:
            if self.is_recording:
                self.stop_recording_pattern()

            self.sell_button_position = None
            self.is_selling = False
            self.is_walking = False

            if hasattr(self, "keyboard_controller"):
                try:
                    del self.keyboard_controller
                except:
                    pass
                self.keyboard_controller = None

            self.recorded_pattern = []

            import gc

            for _ in range(3):
                gc.collect()

            logger.debug("AutomationManager cleanup completed")

        except Exception as e:
            logger.debug(f"Error during AutomationManager cleanup: {e}")

    def update_custom_keys_setting(self, allow_custom_keys):
        self.allow_custom_keys = allow_custom_keys
        logger.info(f"Updated custom keys setting to: {allow_custom_keys}")

    def focus_roblox_window(self):
        try:
            from utils.system_utils import get_window_list

            windows = get_window_list()

            roblox_patterns = ["Roblox", "roblox"]

            for pattern in roblox_patterns:
                for window in windows:
                    if pattern.lower() in window["title"].lower():
                        if self._focus_window_no_resize(window["hwnd"]):
                            logger.info(
                                f"Successfully focused Roblox window: {window['title']}"
                            )
                            return True
                        else:
                            logger.warning(
                                f"Found Roblox window but failed to focus: {window['title']}"
                            )

            logger.warning("Roblox window not found")
            return False

        except Exception as e:
            logger.error(f"Error focusing Roblox window: {e}")
            return False

    def _focus_window_no_resize(self, hwnd):
        try:
            import win32gui

            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            logger.error(f"Failed to focus window: {e}")
            return False

    def preview_pattern(self, pattern_name):
        try:
            logger.info(f"Preview requested for pattern: '{pattern_name}'")
            logger.info(f"Available patterns: {list(self.walk_patterns.keys())}")

            self._preview_active = True
            self._stop_preview = False

            if not self.focus_roblox_window():
                self._preview_active = False
                return False, "Could not focus Roblox window"

            if pattern_name not in self.walk_patterns:
                logger.error(f"Pattern '{pattern_name}' not found in walk_patterns")
                self._preview_active = False
                return False, f"Pattern '{pattern_name}' not found"

            pattern = self.walk_patterns[pattern_name]
            logger.info(f"Previewing pattern '{pattern_name}': {pattern}")

            time.sleep(0.5)

            for i, step in enumerate(pattern):
                if self._stop_preview:
                    self._preview_active = False
                    return True, f"Pattern '{pattern_name}' preview stopped by user"

                logger.info(f"Preview step {i+1}/{len(pattern)}: {step}")

                if isinstance(step, dict):
                    key = step.get("key", "")
                    custom_duration = step.get("duration", None)
                else:
                    key = str(step)
                    custom_duration = None

                if not key:
                    continue

                if custom_duration is not None:
                    success = self._execute_movement_with_duration(
                        key, custom_duration / 1000.0
                    )
                else:
                    success = self.perform_walk_step(key)

                if not success:
                    error_msg = f"Failed to execute step '{key}' at position {i+1}"
                    logger.error(error_msg)
                    self._preview_active = False
                    return False, error_msg

                if i < len(pattern) - 1:
                    time.sleep(0.3)

            self._preview_active = False
            logger.info(f"Pattern preview completed: {pattern_name}")
            return True, f"Pattern '{pattern_name}' preview completed successfully"

        except Exception as e:
            self._preview_active = False
            logger.error(f"Error previewing pattern '{pattern_name}': {e}")
            return False, f"Error previewing pattern: {str(e)}"

    def preview_recorded_pattern(self, pattern):
        try:
            if not pattern:
                return False, "No pattern to preview"

            self._preview_active = True
            self._stop_preview = False

            success = self.focus_roblox_window()
            if not success:
                self._preview_active = False
                return (
                    False,
                    "Could not focus Roblox window. Make sure Roblox is running.",
                )

            time.sleep(0.5)

            logger.info(
                f"Starting preview of recorded pattern with {len(pattern)} steps"
            )

            for i, step in enumerate(pattern):
                if self._stop_preview:
                    self._preview_active = False
                    return True, "Recorded pattern preview stopped by user"

                if isinstance(step, dict):
                    key = step.get("key", "")
                    custom_duration = step.get("duration", None)
                else:
                    key = str(step)
                    custom_duration = None

                if not key:
                    continue

                if custom_duration is not None:
                    walk_duration = custom_duration / 1000.0
                else:
                    walk_duration = self.dig_tool.get_param("walk_duration") / 1000.0

                logger.info(
                    f"Preview step {i+1}/{len(pattern)}: {key} (duration: {walk_duration:.3f}s)"
                )

                self._execute_movement_with_duration(key, walk_duration)

                time.sleep(0.2)

            self._preview_active = False
            return True, f"Successfully previewed {len(pattern)} steps"

        except Exception as e:
            self._preview_active = False
            logger.error(f"Error during recorded pattern preview: {str(e)}")
            return False, f"Preview failed: {str(e)}"

    def auto_load_patterns(self):
        try:
            auto_walk_dir = self.dig_tool.settings_manager.get_auto_walk_directory()
            auto_filepath = os.path.join(auto_walk_dir, "custom_patterns.json")

            if os.path.exists(auto_filepath):
                with open(auto_filepath, "r") as f:
                    raw_patterns = json.load(f)

                    processed_patterns = {}
                    for pattern_name, pattern_steps in raw_patterns.items():
                        processed_steps = []
                        for step in pattern_steps:
                            if isinstance(step, dict):
                                if "click" not in step:
                                    step["click"] = True
                                processed_steps.append(step)
                            else:
                                # legacy
                                processed_steps.append(
                                    {"key": str(step), "duration": None, "click": True}
                                )
                        processed_patterns[pattern_name] = processed_steps

                    self.walk_patterns.update(processed_patterns)
                    self.custom_patterns_file = auto_filepath
                    logger.info(
                        f"Auto-loaded {len(processed_patterns)} custom patterns from {auto_filepath}"
                    )
            else:
                logger.info("No auto-load patterns file found in Auto Walk directory")
        except Exception as e:
            logger.error(f"Error auto-loading custom patterns: {e}")

    def _convert_key_name(self, key_name):
        key_name = key_name.lower().strip()

        if key_name in self.key_mapping:
            return self.key_mapping[key_name]

        if len(key_name) == 1 and key_name.isalnum():
            return key_name

        return key_name

    def _normalize_pattern_step(self, step):
        if isinstance(step, dict):
            return step
        elif isinstance(step, str):
            return {"key": step, "duration": None}
        else:
            return {"key": str(step), "duration": None}

    def _get_step_key(self, step):
        if isinstance(step, dict):
            return step.get("key", "")
        else:
            return str(step)

    def _get_step_duration(self, step, default_duration=None):
        if isinstance(step, dict):
            return step.get("duration", default_duration)
        else:
            return default_duration

    def _execute_movement_with_duration(self, direction, duration):
        try:
            common_movement_keys = [
                "w",
                "a",
                "s",
                "d",
                "up",
                "down",
                "left",
                "right",
                "shift",
                "ctrl",
                "alt",
                "space",
            ]
            for key in common_movement_keys:
                try:
                    converted_key = self._convert_key_name(key)
                    self.keyboard_controller.release(converted_key)
                except:
                    pass
            time.sleep(0.05)

            if "+" in direction:
                keys_to_press = direction.lower().split("+")
                converted_keys = []

                for key in keys_to_press:
                    key = key.strip()
                    if key:
                        try:
                            converted_key = self._convert_key_name(key)
                            converted_keys.append(converted_key)
                            self.keyboard_controller.press(converted_key)
                            logger.debug(f"Pressed key '{key}' -> {converted_key}")
                        except Exception as e:
                            logger.warning(f"Failed to press key '{key}': {e}")

                time.sleep(duration)

                for converted_key in converted_keys:
                    try:
                        self.keyboard_controller.release(converted_key)
                    except Exception as e:
                        logger.warning(f"Failed to release key {converted_key}: {e}")

            elif len(direction) == 1:
                try:
                    converted_key = self._convert_key_name(direction.lower())
                    self.keyboard_controller.press(converted_key)
                    time.sleep(duration)
                    self.keyboard_controller.release(converted_key)
                    logger.debug(f"Single key '{direction}' -> {converted_key}")
                except Exception as e:
                    logger.warning(
                        f"Failed to press/release single key '{direction}': {e}"
                    )
            else:
                # legacy
                try:
                    converted_key = self._convert_key_name(direction.lower())
                    self.keyboard_controller.press(converted_key)
                    time.sleep(duration)
                    self.keyboard_controller.release(converted_key)
                    logger.debug(f"Long key name '{direction}' -> {converted_key}")
                except Exception:
                    try:
                        for key in direction.lower():
                            if key in ["w", "a", "s", "d"]:
                                converted_key = self._convert_key_name(key)
                                self.keyboard_controller.press(converted_key)
                        time.sleep(duration)
                        for key in direction.lower():
                            if key in ["w", "a", "s", "d"]:
                                converted_key = self._convert_key_name(key)
                                self.keyboard_controller.release(converted_key)
                        logger.debug(f"Legacy multi-key '{direction}'")
                    except Exception as e:
                        logger.error(f"Failed to execute movement '{direction}': {e}")
                        return False

            time.sleep(0.05)
            return True

        except Exception as e:
            logger.error(f"Error in movement execution: {e}")
            return False

    def save_pattern(self, name, pattern):
        if not name or not pattern:
            return False, "Pattern name and moves cannot be empty"

        processed_pattern = []
        for step in pattern:
            if isinstance(step, dict):
                if "key" in step:
                    processed_pattern.append(
                        {
                            "key": step["key"].upper().strip(),
                            "duration": step.get("duration", None),
                            "click": step.get("click", True),
                        }
                    )
                else:
                    return False, "Invalid pattern format: missing 'key' field"
            elif isinstance(step, str):
                processed_pattern.append(
                    {"key": step.upper().strip(), "duration": None, "click": True}
                )
            else:
                return False, "Invalid pattern format"

        self.walk_patterns[name] = processed_pattern

        current_pattern = getattr(self.dig_tool, "walk_pattern_var", None)
        if current_pattern:
            current_pattern_name = (
                current_pattern.get() if hasattr(current_pattern, "get") else None
            )
            if current_pattern_name == name:
                self.walk_pattern_index = 0
                logger.debug(f"Reset pattern index for modified pattern: {name}")

        success = self.save_custom_patterns()

        if success:
            return True, f"Pattern '{name}' saved successfully"
        else:
            return False, "Failed to save pattern"

    def _update_shiftlock_state(self, key, is_pressed):
        key = key.lower().strip()

        if key == "shift" or key == "left shift":
            previous_state = self.shiftlock_state["shift"]
            self.shiftlock_state["shift"] = is_pressed

            if previous_state != is_pressed:
                logger.debug(f"Shiftlock state changed: left shift = {is_pressed}")

        elif key == "right shift":
            previous_state = self.shiftlock_state["right_shift"]
            self.shiftlock_state["right_shift"] = is_pressed

            if previous_state != is_pressed:
                logger.debug(f"Shiftlock state changed: right shift = {is_pressed}")

    def _is_shift_key(self, key):
        key = key.lower().strip()
        return key in ["shift", "left shift", "right shift"]

    def _toggle_shiftlock_on_shift_press(self, key):
        key = key.lower().strip()

        if key == "shift" or key == "left shift":
            self.shiftlock_state["shift"] = not self.shiftlock_state["shift"]
            logger.info(
                f"Shiftlock toggled: left shift = {self.shiftlock_state['shift']}"
            )

        elif key == "right shift":
            self.shiftlock_state["right_shift"] = not self.shiftlock_state[
                "right_shift"
            ]
            logger.info(
                f"Shiftlock toggled: right shift = {self.shiftlock_state['right_shift']}"
            )

    def get_shiftlock_state(self):
        return self.shiftlock_state.copy()

    def is_any_shift_active(self):
        return self.shiftlock_state["shift"] or self.shiftlock_state["right_shift"]

    def disable_active_shifts_for_sell(self):
        shifts_disabled = []

        self.shiftlock_state["was_active_before_sell"] = self.is_any_shift_active()

        try:
            if self.shiftlock_state["shift"]:
                self.keyboard_controller.press(Key.shift)
                time.sleep(0.05)
                self.keyboard_controller.release(Key.shift)
                shifts_disabled.append("shift")
                logger.debug("Toggled left shift off for auto-sell")

            if self.shiftlock_state["right_shift"]:
                self.keyboard_controller.press(Key.shift_r)
                time.sleep(0.05)
                self.keyboard_controller.release(Key.shift_r)
                shifts_disabled.append("right_shift")
                logger.debug("Toggled right shift off for auto-sell")

        except Exception as e:
            logger.warning(f"Error disabling shift keys for auto-sell: {e}")

        if shifts_disabled:
            logger.info(
                f"Disabled shiftlock for auto-sell: {', '.join(shifts_disabled)}"
            )
            self.shiftlock_state["shift"] = False
            self.shiftlock_state["right_shift"] = False

        return shifts_disabled

    def restore_shifts_after_sell(self):
        if not self.shiftlock_state["was_active_before_sell"]:
            return []

        shifts_restored = []

        try:
            if self.shiftlock_state["was_active_before_sell"]:
                self.keyboard_controller.press(Key.shift)
                time.sleep(0.05)
                self.keyboard_controller.release(Key.shift)

                self.shiftlock_state["shift"] = True
                shifts_restored.append("shift")
                logger.debug("Restored left shift after auto-sell")

        except Exception as e:
            logger.warning(f"Error restoring shift keys after auto-sell: {e}")

        if shifts_restored:
            logger.info(
                f"Restored shiftlock after auto-sell: {', '.join(shifts_restored)}"
            )

        self.shiftlock_state["was_active_before_sell"] = False

        return shifts_restored

    def disable_active_shifts(self):
        return self.disable_active_shifts_for_sell()

    def stop_preview(self):
        self._stop_preview = True
        logger.info("Pattern preview stop requested")
        return True, "Preview stopped"

    def is_preview_active(self):
        return self._preview_active

    def find_and_focus_roblox_window(self):
        try:
            from utils.system_utils import find_window_by_title

            roblox_patterns = ["Roblox", "roblox"]
            roblox_window = None

            for pattern in roblox_patterns:
                roblox_window = find_window_by_title(pattern, exact_match=False)
                if roblox_window:
                    logger.debug(f"Found Roblox window: {roblox_window['title']}")
                    break

            if roblox_window:
                success = self._focus_window_no_resize(roblox_window["hwnd"])
                if success:
                    logger.info(
                        f"Successfully focused Roblox window: {roblox_window['title']}"
                    )
                    time.sleep(0.2)
                    return True
                else:
                    logger.warning("Failed to focus Roblox window")
                    return False
            else:
                logger.warning("Roblox window not found")
                return False

        except Exception as e:
            logger.error(f"Error focusing Roblox window: {e}")
            return False

    def perform_shovel_action(self):
        try:
            if not self.find_and_focus_roblox_window():
                return False, "Roblox window not found or focus failed"

            success = self.re_equip_shovel()

            if success:
                logger.info("Shovel action performed successfully")
                return True, "Shovel action completed"
            else:
                logger.error("Shovel action failed during re-equip")
                return False, "Shovel action failed"

        except Exception as e:
            logger.error(f"Error performing shovel action: {e}")
            return False, f"Error: {e}"

    def get_auto_shovel_status(self):
        if not self.dig_tool.get_param("auto_shovel_enabled"):
            return "Auto-shovel disabled"

        if not self.dig_tool.running:
            return "Auto-shovel (waiting for tool to start)"

        if self.shovel_re_equipped:
            return "Shovel recently re-equipped"

        current_time = time.time()
        shovel_timeout = self.dig_tool.get_param("shovel_timeout") * 60

        time_since_last_dig = (
            current_time - self.last_dig_time if self.last_dig_time else float("inf")
        )

        if time_since_last_dig >= shovel_timeout:
            return "Ready to re-equip shovel"
        else:
            remaining_time = shovel_timeout - time_since_last_dig
            return f"Auto-shovel in {remaining_time:.0f}s"

    def update_record_click_setting(self, click_enabled):
        self.record_click_enabled = click_enabled
        logger.info(f"Updated record click setting to: {click_enabled}")
