import time
import threading
import math
from pynput.keyboard import Key
from utils.debug_logger import logger
from utils.config_management import get_param


class MovementManager:
    
    def __init__(self, dig_tool, keyboard_controller, shift_manager):
        self.dig_tool = dig_tool
        self.keyboard_controller = keyboard_controller
        self.shift_manager = shift_manager
        self.walking_lock = threading.Lock()
        
        self.is_walking = False
        self.walk_pattern_index = 0

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
    
    def convert_key_name(self, key_name):
        key_name = key_name.lower().strip()

        if key_name in self.key_mapping:
            return self.key_mapping[key_name]

        if len(key_name) == 1 and key_name.isalnum():
            return key_name

        return key_name

    def normalize_pattern_step(self, step):
        if isinstance(step, dict):
            return step
        elif isinstance(step, str):
            return {"key": step, "duration": None}
        else:
            return {"key": str(step), "duration": None}

    def get_step_key(self, step):
        if isinstance(step, dict):
            return step.get("key", "")
        else:
            return str(step)

    def get_step_duration(self, step, default_duration=None):
        if isinstance(step, dict):
            return step.get("duration", default_duration)
        else:
            return default_duration

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

    def execute_movement_with_duration(self, direction, duration):
        try:
            base_duration = duration
            
            if get_param(self.dig_tool, "dynamic_walkspeed_enabled"):
                items_collected = self.dig_tool.automation_manager.get_walkspeed_dig_count()
                initial_item_count = (
                    get_param(self.dig_tool, "initial_item_count") or 0
                )
                total_items = items_collected + initial_item_count

                formula_reduction = self.calculate_walkspeed_multiplier(total_items)

                initial_decrease = (
                    get_param(self.dig_tool, "initial_walkspeed_decrease") or 0.0
                )
                initial_decrease = max(0.0, min(1.0, initial_decrease))

                total_reduction = min(formula_reduction + initial_decrease, 0.99)
                duration_multiplier = 1.0 + total_reduction
                duration = base_duration * duration_multiplier

                if total_items > 35 or initial_decrease > 0:
                    logger.debug(f"Dynamic walkspeed applied: {duration_multiplier:.2f}x duration")

            if "+" in direction:
                keys_to_press = direction.lower().split("+")
                converted_keys = []

                for key in keys_to_press:
                    key = key.strip()
                    if key:
                        try:
                            converted_key = self.convert_key_name(key)
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
                    converted_key = self.convert_key_name(direction.lower())
                    self.keyboard_controller.press(converted_key)
                    time.sleep(duration)
                    self.keyboard_controller.release(converted_key)
                    logger.debug(f"Single key '{direction}' -> {converted_key}")
                except Exception as e:
                    logger.warning(
                        f"Failed to press/release single key '{direction}': {e}"
                    )
            else:
                try:
                    converted_key = self.convert_key_name(direction.lower())
                    self.keyboard_controller.press(converted_key)
                    time.sleep(duration)
                    self.keyboard_controller.release(converted_key)
                    logger.debug(f"Long key name '{direction}' -> {converted_key}")
                except Exception:
                    try:
                        for key in direction.lower():
                            if key in ["w", "a", "s", "d"]:
                                converted_key = self.convert_key_name(key)
                                self.keyboard_controller.press(converted_key)
                        time.sleep(duration)
                        for key in direction.lower():
                            if key in ["w", "a", "s", "d"]:
                                converted_key = self.convert_key_name(key)
                                self.keyboard_controller.release(converted_key)
                        logger.debug(f"Legacy multi-key '{direction}'")
                    except Exception as e:
                        logger.error(f"Failed to execute movement '{direction}': {e}")
                        return False

            return True

        except Exception as e:
            logger.error(f"Error in movement execution: {e}")
            return False

    def perform_walk_step(self, direction, record_movement_callback=None):
        try:
            with self.walking_lock:
                self.is_walking = True
                
                if record_movement_callback:
                    record_movement_callback(direction)
                    logger.debug(f"Recorded movement during walk: {direction}")

                walk_duration = get_param(self.dig_tool, "walk_duration") / 1000.0

                if get_param(self.dig_tool, "dynamic_walkspeed_enabled"):
                    base_duration = walk_duration

                    items_collected = self.dig_tool.automation_manager.get_walkspeed_dig_count()
                    initial_item_count = (
                        get_param(self.dig_tool, "initial_item_count") or 0
                    )
                    total_items = items_collected + initial_item_count

                    formula_reduction = self.calculate_walkspeed_multiplier(total_items)

                    initial_decrease = (
                        get_param(self.dig_tool, "initial_walkspeed_decrease") or 0.0
                    )
                    initial_decrease = max(0.0, min(1.0, initial_decrease))

                    total_reduction = min(formula_reduction + initial_decrease, 0.99)
                    duration_multiplier = 1.0 + total_reduction
                    walk_duration = base_duration * duration_multiplier

                    if total_items > 35 or initial_decrease > 0:
                        logger.debug(f"Dynamic walkspeed applied: {duration_multiplier:.2f}x duration")

                if "+" in direction:
                    keys_to_press = direction.lower().split("+")
                    converted_keys = []

                    for key in keys_to_press:
                        key = key.strip()
                        if key:
                            try:
                                converted_key = self.convert_key_name(key)
                                converted_keys.append(converted_key)
                                self.keyboard_controller.press(converted_key)

                                if self.shift_manager.is_shift_key(key):
                                    self.shift_manager.toggle_shiftlock_on_shift_press(key)

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
                        converted_key = self.convert_key_name(direction.lower())
                        self.keyboard_controller.press(converted_key)

                        if self.shift_manager.is_shift_key(direction.lower()):
                            self.shift_manager.toggle_shiftlock_on_shift_press(direction.lower())

                        time.sleep(walk_duration)
                        self.keyboard_controller.release(converted_key)
                        logger.debug(f"Single key '{direction}' -> {converted_key}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to press/release single key '{direction}': {e}"
                        )
                else:
                    try:
                        converted_key = self.convert_key_name(direction.lower())
                        self.keyboard_controller.press(converted_key)

                        if self.shift_manager.is_shift_key(direction.lower()):
                            self.shift_manager.toggle_shiftlock_on_shift_press(direction.lower())
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

            self.is_walking = False
            return True

        except Exception as e:
            self.is_walking = False
            logger.error(f"Error in walk step: {e}")
            return False

    def get_next_walk_direction(self, walk_patterns):
        current_pattern = getattr(self.dig_tool, "walk_pattern_var", None)
        if not current_pattern:
            pattern_name = "_KC_Nugget_v1"
        else:
            pattern_name = (
                current_pattern.get()
                if hasattr(current_pattern, "get")
                else "_KC_Nugget_v1"
            )

        pattern = walk_patterns.get(
            pattern_name, walk_patterns["_KC_Nugget_v1"]
        )

        step = pattern[self.walk_pattern_index]
        return step

    def get_current_walk_step(self, walk_patterns):
        current_pattern = getattr(self.dig_tool, "walk_pattern_var", None)
        if not current_pattern:
            pattern_name = "_KC_Nugget_v1"
        else:
            pattern_name = (
                current_pattern.get()
                if hasattr(current_pattern, "get")
                else "_KC_Nugget_v1"
            )

        pattern = walk_patterns.get(
            pattern_name, walk_patterns["_KC_Nugget_v1"]
        )

        step = pattern[self.walk_pattern_index]
        return step

    def advance_walk_pattern(self, walk_patterns):
        current_pattern = getattr(self.dig_tool, "walk_pattern_var", None)
        if not current_pattern:
            pattern_name = "_KC_Nugget_v1"
        else:
            pattern_name = (
                current_pattern.get()
                if hasattr(current_pattern, "get")
                else "_KC_Nugget_v1"
            )

        pattern = walk_patterns.get(
            pattern_name, walk_patterns["_KC_Nugget_v1"]
        )

        self.walk_pattern_index = (self.walk_pattern_index + 1) % len(pattern)

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

    def _execute_movement_with_duration(self, direction, duration):
        try:
            with self.walking_lock:
                self.is_walking = True
                
                base_duration = duration
                
                if get_param(self.dig_tool, "dynamic_walkspeed_enabled"):
                    items_collected = self.dig_tool.automation_manager.get_walkspeed_dig_count()
                    initial_item_count = (
                        get_param(self.dig_tool, "initial_item_count") or 0
                    )
                    total_items = items_collected + initial_item_count

                    formula_reduction = self.calculate_walkspeed_multiplier(total_items)

                    initial_decrease = (
                        get_param(self.dig_tool, "initial_walkspeed_decrease") or 0.0
                    )
                    initial_decrease = max(0.0, min(1.0, initial_decrease))

                    total_reduction = min(formula_reduction + initial_decrease, 0.99)
                    duration_multiplier = 1.0 + total_reduction
                    duration = base_duration * duration_multiplier

                    if total_items > 35 or initial_decrease > 0:
                        logger.debug(f"Dynamic walkspeed applied: {duration_multiplier:.2f}x duration")
                
                if isinstance(direction, str):
                    if direction.lower() in self.key_mapping:
                        key = self.key_mapping[direction.lower()]
                    else:
                        key = direction.lower()
                else:
                    key = direction

                logger.debug(f"Executing movement '{direction}' for {duration}s")
                
                if hasattr(key, 'name'):
                    self.keyboard_controller.press(key)
                    time.sleep(duration)
                    self.keyboard_controller.release(key)
                else:
                    self.keyboard_controller.press(key)
                    time.sleep(duration)
                    self.keyboard_controller.release(key)
                
                self.is_walking = False
                return True
                
        except Exception as e:
            logger.error(f"Movement execution failed: {e}")
            self.is_walking = False
            return False
        finally:
            self.is_walking = False
