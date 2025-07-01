import time
import threading
import autoit
import json
import os
from tkinter import filedialog
from pynput.keyboard import Controller as KeyboardController


class AutomationManager:
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance
        self.keyboard_controller = KeyboardController()
        self.walk_pattern_index = 0
        self.last_successful_direction = None
        self.walk_patterns = {
            'circle': ['d', 'd', 'd', 'w', 'w', 'w', 'a', 'a', 'a', 's', 's', 's'],
            'figure_8': ['d', 'w', 'd', 'w', 'a', 's', 'a', 's'],
            'random': ['w', 'a', 's', 'd'],
            'forward_back': ['w', 'w', 's', 's'],
            'left_right': ['a', 'a', 'd', 'd']
        }

        self.custom_patterns_file = None

        self.sell_button_position = None
        self.sell_count = 0
        self.is_selling = False
        self.is_walking = False
        self.current_status = "STOPPED"

        self.is_recording = False
        self.recorded_pattern = []
        self.recording_start_time = None
        self.recording_listener = None
        self.recording_hook = None

        self.last_dig_time = None
        self.last_click_time = None
        self.last_target_lock_time = None
        self.shovel_re_equipped = False
        self.walking_lock = threading.Lock()

    def load_custom_patterns(self):
        try:
            filepath = filedialog.askopenfilename(
                title="Load Custom Patterns",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
            )
            if not filepath:
                return

            with open(filepath, 'r') as f:
                custom_patterns = json.load(f)
                self.walk_patterns.update(custom_patterns)
                self.custom_patterns_file = filepath
                print(f"Loaded {len(custom_patterns)} custom patterns")
        except Exception as e:
            print(f"Error loading custom patterns: {e}")

    def save_custom_patterns(self):
        try:
            if not self.custom_patterns_file:
                filepath = filedialog.asksaveasfilename(
                    title="Save Custom Patterns",
                    defaultextension=".json",
                    filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
                )
                if not filepath:
                    return False
                self.custom_patterns_file = filepath

            built_in_patterns = {'circle', 'figure_8', 'random', 'forward_back', 'left_right'}
            custom_patterns = {name: pattern for name, pattern in self.walk_patterns.items()
                               if name not in built_in_patterns}

            with open(self.custom_patterns_file, 'w') as f:
                json.dump(custom_patterns, f, indent=2)
            print(f"Saved {len(custom_patterns)} custom patterns")
            return True
        except Exception as e:
            print(f"Error saving custom patterns: {e}")
            return False

    def add_custom_pattern(self, name, pattern):
        if not name or not pattern:
            return False, "Pattern name and moves cannot be empty"

        valid_moves = {'w', 'a', 's', 'd'}
        if not all(move.lower() in valid_moves for move in pattern):
            return False, "Pattern can only contain W, A, S, D keys"

        pattern = [move.lower() for move in pattern]

        self.walk_patterns[name] = pattern
        success = self.save_custom_patterns()

        if success:
            return True, f"Custom pattern '{name}' added successfully"
        else:
            return False, "Failed to save custom pattern"

    def delete_custom_pattern(self, name):
        built_in_patterns = {'circle', 'figure_8', 'random', 'forward_back', 'left_right'}

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
        built_in_patterns = {'circle', 'figure_8', 'random', 'forward_back', 'left_right'}
        pattern_info = {}

        for name, pattern in self.walk_patterns.items():
            pattern_info[name] = {
                'pattern': pattern,
                'type': 'built-in' if name in built_in_patterns else 'custom',
                'length': len(pattern)
            }

        return pattern_info

    def start_recording_pattern(self):
        self.is_recording = True
        self.recorded_pattern = []
        self.recording_start_time = time.time()
        self.start_recording_keyboard_listener()
        print("Started recording pattern")
        return True

    def start_recording_keyboard_listener(self):
        try:
            import keyboard

            def on_key_press(event):
                if self.is_recording and event.event_type == keyboard.KEY_DOWN:
                    key = event.name.lower()
                    if key in ['w', 'a', 's', 'd']:
                        self.record_movement(key)

            self.recording_hook = keyboard.hook(on_key_press)

        except Exception as e:
            self.recording_hook = None
            pass

    def stop_recording_pattern(self):
        self.is_recording = False

        try:
            import keyboard
            if hasattr(self, 'recording_hook') and self.recording_hook:
                keyboard.unhook(self.recording_hook)
                self.recording_hook = None
        except Exception as e:
            print(f"Warning: Could not unhook specific recording listener: {e}")
            try:
                import keyboard
                if hasattr(self.dig_tool, 'apply_keybinds'):
                    self.dig_tool.root.after(100, self.dig_tool.apply_keybinds)
            except:
                pass

        pattern = self.recorded_pattern.copy()
        self.recorded_pattern = []
        print(f"Stopped recording pattern")
        return pattern

    def record_movement(self, direction):
        if self.is_recording and direction.lower() in ['w', 'a', 's', 'd']:
            self.recorded_pattern.append(direction.lower())
            return True
        return False

    def update_dig_activity(self):
        self.last_dig_time = time.time()
        self.shovel_re_equipped = False

    def update_click_activity(self):
        self.last_click_time = time.time()

    def update_target_lock_activity(self):
        self.last_target_lock_time = time.time()

    def should_re_equip_shovel(self):
        if not self.dig_tool.get_param('auto_walk_enabled'):
            return False

        if not self.dig_tool.get_param('auto_shovel_enabled'):
            return False

        if self.shovel_re_equipped:
            return False

        current_time = time.time()
        shovel_timeout = self.dig_tool.get_param('shovel_timeout') * 60

        time_since_dig = current_time - self.last_dig_time if self.last_dig_time else float('inf')
        time_since_click = current_time - self.last_click_time if self.last_click_time else float('inf')
        time_since_target = current_time - self.last_target_lock_time if self.last_target_lock_time else float('inf')

        no_recent_activity = (time_since_dig > shovel_timeout and
                              time_since_click > shovel_timeout and
                              time_since_target > shovel_timeout)

        return no_recent_activity

    def re_equip_shovel(self):
        try:
            shovel_slot = self.dig_tool.get_param('shovel_slot')
            if shovel_slot < 0 or shovel_slot > 9:
                print(f"Invalid shovel slot: {shovel_slot}")
                return False

            slot_key = str(shovel_slot) if shovel_slot > 0 else '0'
            equip_mode = self.dig_tool.get_param('shovel_equip_mode')

            print(f"Re-equipping shovel from slot {shovel_slot} (key: {slot_key}) using {equip_mode} mode")

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
            self.last_dig_time = time.time()

            mode_text = "double press" if equip_mode == "double" else "single press"
            self.dig_tool.update_status(f"Auto-equipped shovel from slot {shovel_slot} ({mode_text})")
            return True

        except Exception as e:
            print(f"Error re-equipping shovel: {e}")
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
        elif self.dig_tool.get_param('auto_walk_enabled'):
            return "AUTO WALKING"
        else:
            return "ACTIVE"

    def perform_walk_step(self, direction):
        try:
            with self.walking_lock:
                self.is_walking = True

                if self.is_recording:
                    self.record_movement(direction)
                    print(f"Recorded movement during walk: {direction}")

                self.keyboard_controller.release('w')
                self.keyboard_controller.release('a')
                self.keyboard_controller.release('s')
                self.keyboard_controller.release('d')
                time.sleep(0.05)

                walk_duration = self.dig_tool.get_param('walk_duration') / 1000.0
                self.keyboard_controller.press(direction)
                time.sleep(walk_duration)
                self.keyboard_controller.release(direction)
                
                time.sleep(0.05)

            self.is_walking = False
            return True

        except Exception as e:
            self.is_walking = False
            print(f"Error in walk step: {e}")
            return False

    def get_next_walk_direction(self):
        current_pattern = getattr(self.dig_tool, 'walk_pattern_var', None)
        if not current_pattern:
            pattern_name = 'circle'
        else:
            pattern_name = current_pattern.get() if hasattr(current_pattern, 'get') else 'circle'

        pattern = self.walk_patterns.get(pattern_name, self.walk_patterns['circle'])

        if pattern_name == 'random':
            import random
            return random.choice(pattern)
        else:
            direction = pattern[self.walk_pattern_index]
            return direction
    
    def advance_walk_pattern(self):
        current_pattern = getattr(self.dig_tool, 'walk_pattern_var', None)
        if not current_pattern:
            pattern_name = 'circle'
        else:
            pattern_name = current_pattern.get() if hasattr(current_pattern, 'get') else 'circle'

        pattern = self.walk_patterns.get(pattern_name, self.walk_patterns['circle'])
        
        if pattern_name != 'random':
            self.walk_pattern_index = (self.walk_pattern_index + 1) % len(pattern)

    def can_auto_sell(self):
        auto_walk_enabled = self.dig_tool.get_param('auto_walk_enabled')
        auto_sell_enabled = self.dig_tool.get_param('auto_sell_enabled')

        if auto_sell_enabled and not auto_walk_enabled:
            self.dig_tool.update_status("Auto-sell disabled: Auto-walk must be enabled!")
            return False

        return auto_sell_enabled and self.sell_button_position is not None

    def autoit_click(self, x, y, retries=3):
        for attempt in range(retries):
            try:
                print(f"AutoIt click attempt {attempt + 1}: Target: ({x}, {y})")

                autoit.mouse_move(x, y, speed=2)
                time.sleep(0.1)

                current_pos = autoit.mouse_get_pos()
                tolerance = 5

                if abs(current_pos[0] - x) <= tolerance and abs(current_pos[1] - y) <= tolerance:
                    autoit.mouse_click("left", x, y, speed=2)
                    time.sleep(0.1)
                    print(f"AutoIt click successful at {current_pos}")
                    return True
                else:
                    print(f"AutoIt position verification: Expected ({x}, {y}), Got {current_pos}")
                    if attempt < retries - 1:
                        time.sleep(0.2)
                        continue

            except Exception as e:
                print(f"AutoIt click attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(0.2)
                    continue

        print("All AutoIt click attempts failed")
        return False

    def perform_auto_sell(self):
        try:
            if not self.can_auto_sell():
                return

            self.is_selling = True
            self.dig_tool.update_status("Auto-selling...")

            autoit.send("g")
            time.sleep(0.3)

            sell_delay = max(self.dig_tool.get_param('sell_delay') / 1000.0, 2.5)
            time.sleep(sell_delay)

            x, y = self.sell_button_position

            print(f"Performing AutoIt click at sell button: {x}, {y}")
            success = self.autoit_click(x, y)

            if success:
                print("Sell click successful")
                time.sleep(2.5)
                autoit.send("g")
                time.sleep(1.0)
                self.sell_count += 1
                self.dig_tool.update_status(f"Auto-sell #{self.sell_count} completed")
            else:
                self.dig_tool.update_status("Auto-sell failed: AutoIt click error")

            self.is_selling = False

        except Exception as e:
            self.is_selling = False
            print(f"Error in auto-sell: {e}")
            self.dig_tool.update_status(f"Auto-sell failed: {e}")

    def test_sell_button_click(self):
        if not self.sell_button_position:
            self.dig_tool.update_status("Sell button not set!")
            return

        threading.Thread(target=self._test_sell_click_with_delay, daemon=True).start()

    def _test_sell_click_with_delay(self):
        x, y = self.sell_button_position
        print(f"Testing AutoIt click at position: {x}, {y}")

        for i in range(5, 0, -1):
            self.dig_tool.update_status(f"Test click in {i} seconds... Position: ({x}, {y})")
            time.sleep(1.0)

        self.dig_tool.update_status("Performing AutoIt test click...")
        print(f"Executing AutoIt test click at: {x}, {y}")

        success = self.autoit_click(x, y)

        if success:
            self.dig_tool.update_status("AutoIt test click completed successfully!")
        else:
            self.dig_tool.update_status("AutoIt test click failed!")

    def test_shovel_equip(self):
        if not self.dig_tool.get_param('auto_shovel_enabled'):
            self.dig_tool.update_status("Auto-shovel is disabled!")
            return

        shovel_slot = self.dig_tool.get_param('shovel_slot')
        equip_mode = self.dig_tool.get_param('shovel_equip_mode')
        mode_text = "double press" if equip_mode == "double" else "single press"

        self.dig_tool.update_status(f"Testing shovel equip from slot {shovel_slot} ({mode_text})...")

        threading.Thread(target=self._test_shovel_equip_with_delay, daemon=True).start()

    def _test_shovel_equip_with_delay(self):
        for i in range(3, 0, -1):
            self.dig_tool.update_status(f"Equipping shovel in {i} seconds...")
            time.sleep(1.0)

        success = self.re_equip_shovel()

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
            print(f"Key press failed: {e}")
            return False

    def get_mouse_position(self):
        try:
            return self.mouse_controller.position
        except Exception as e:
            print(f"Get mouse position failed: {e}")
            return (0, 0)