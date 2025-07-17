import time
import threading
import json
import os
from tkinter import filedialog
from utils.debug_logger import logger
from utils.config_management import get_param

BUILT_IN_PATTERNS = {
    "_KC_Nugget_v1",
    "Brick_Pattern",
    "Circuit_Pattern", 
    "Spiral_Pattern",
}


class PatternManager:

    def __init__(self, dig_tool, keyboard_controller, shift_manager):
        self.dig_tool = dig_tool
        self.keyboard_controller = keyboard_controller
        self.shift_manager = shift_manager
        
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
                {"key": "w", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
            ],
            "Circuit_Pattern": [
                {"key": "w", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
            ],
            "Spiral_Pattern": [
                {"key": "w", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "d", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "s", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "a", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
                {"key": "w", "duration": None, "click": True},
            ],
        }
        
        self.is_recording = False
        self.recorded_pattern = []
        self.recording_start_time = None
        self.allow_custom_keys = False
        self.record_click_enabled = True
        self.recording_hook = None
        self.pressed_keys = set()
        
        self._preview_active = False
        self._stop_preview = False
        
        self.custom_patterns_file = None

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

            built_in_patterns = BUILT_IN_PATTERNS
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
        success = self.save_custom_patterns()

        if success:
            return True, f"Pattern '{name}' added successfully"
        else:
            return False, "Failed to save pattern"

    def delete_custom_pattern(self, name):
        if name in BUILT_IN_PATTERNS:
            return False, "Cannot delete built-in patterns"

        if name not in self.walk_patterns:
            return False, f"Pattern '{name}' not found"

        del self.walk_patterns[name]
        success = self.save_custom_patterns()

        if success:
            return True, f"Pattern '{name}' deleted successfully"
        else:
            return False, "Failed to delete pattern"

    def get_pattern_list(self):
        pattern_info = {}

        for name, pattern in self.walk_patterns.items():
            if name in BUILT_IN_PATTERNS:
                pattern_type = "built-in"
            else:
                pattern_type = "custom"
            
            pattern_info[name] = {
                "type": pattern_type,
                "steps": len(pattern),
                "length": len(pattern),
                "pattern": pattern
            }

        return pattern_info

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
                                # legacy format
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
                if hasattr(self.dig_tool, 'automation_manager') and hasattr(self.dig_tool.automation_manager, 'movement_manager'):
                    self.dig_tool.automation_manager.movement_manager.walk_pattern_index = 0
                logger.debug(f"Reset pattern index for modified pattern: {name}")

        success = self.save_custom_patterns()

        if success:
            return True, f"Pattern '{name}' saved successfully"
        else:
            return False, "Failed to save pattern"

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
            
            def on_key_press(event):
                if not self.is_recording:
                    return
                
                key_name = event.name.lower()
                
                if hasattr(self, '_pending_combination'):
                    if key_name not in self._pending_combination:
                        self._pending_combination.append(key_name)
                else:
                    self._pending_combination = [key_name]
                
                if hasattr(self, '_combination_timer'):
                    self._combination_timer.cancel()
                
                self._combination_timer = threading.Timer(0.1, self._record_pending_combination)
                self._combination_timer.start()

            def on_key_release(event):
                if not self.is_recording:
                    return
                    
                pass

            self.recording_hook = keyboard.hook(
                lambda event: (
                    on_key_press(event)
                    if event.event_type == keyboard.KEY_DOWN
                    else on_key_release(event)
                )
            )

        except Exception as e:
            logger.warning(f"Could not start keyboard recording: {e}")
            self.recording_hook = None

    def _record_pending_combination(self):
        try:
            if hasattr(self, "_pending_combination") and self._pending_combination:
                if len(self._pending_combination) == 1:
                    key = self._pending_combination[0]
                else:
                    key = "+".join(sorted(self._pending_combination))
                
                self.record_movement(key)
                self._pending_combination = []
        except Exception as e:
            logger.warning(f"Error recording combination: {e}")

    def stop_recording_pattern(self):
        self.is_recording = False

        try:
            if hasattr(self, "_combination_timer"):
                self._combination_timer.cancel()
            if hasattr(self, "_pending_combination") and self._pending_combination:
                self._record_pending_combination()
        except:
            pass

        try:
            import keyboard
            if hasattr(self, "recording_hook") and self.recording_hook:
                keyboard.unhook(self.recording_hook)
        except Exception as e:
            logger.warning(f"Warning: Could not unhook specific recording listener: {e}")
            try:
                import keyboard
                keyboard.unhook_all()
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
                movement_record = {
                    "key": direction.upper(),
                    "duration": None,
                    "click": click_enabled
                }
                self.recorded_pattern.append(movement_record)
                logger.debug(f"Recorded movement: {movement_record}")
                return True
        return False

    def preview_pattern(self, pattern_name):
        try:
            logger.info(f"Preview requested for pattern: '{pattern_name}'")
            logger.info(f"Available patterns: {list(self.walk_patterns.keys())}")

            self._preview_active = True
            self._stop_preview = False
            
            from utils.system_utils import find_and_focus_roblox_window
            if not find_and_focus_roblox_window():
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
                    success = self.dig_tool.automation_manager.movement_manager.execute_movement_with_duration(
                        key, custom_duration / 1000.0
                    )
                else:
                    success = self.dig_tool.automation_manager.movement_manager.perform_walk_step(key)

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
            from utils.system_utils import find_and_focus_roblox_window
            success = find_and_focus_roblox_window()
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
                    walk_duration = get_param(self.dig_tool, "walk_duration") / 1000.0

                logger.info(
                    f"Preview step {i+1}/{len(pattern)}: {key} (duration: {walk_duration:.3f}s)"
                )

                self.dig_tool.automation_manager.movement_manager.execute_movement_with_duration(key, walk_duration)

                time.sleep(0.2)

            self._preview_active = False
            return True, f"Successfully previewed {len(pattern)} steps"

        except Exception as e:
            self._preview_active = False
            logger.error(f"Error during recorded pattern preview: {str(e)}")
            return False, f"Preview failed: {str(e)}"

    def stop_preview(self):
        self._stop_preview = True
        logger.info("Pattern preview stop requested")
        return True, "Preview stopped"

    def is_preview_active(self):
        return self._preview_active

    def cleanup(self):
        try:
            if self.is_recording:
                self.stop_recording_pattern()
            logger.debug("PatternManager cleanup completed")
        except Exception as e:
            logger.debug(f"Error during PatternManager cleanup: {e}")
