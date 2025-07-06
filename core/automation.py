import time
import threading
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController


class AutomationManager:
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance
        self.keyboard_controller = KeyboardController()
        self.walk_pattern_index = 0
        self.walk_patterns = {
            'circle': ['d', 'd', 'd', 'w', 'w', 'w', 'a', 'a', 'a', 's', 's', 's'],
            'figure_8': ['d', 'w', 'd', 'w', 'a', 's', 'a', 's'],
            'random': ['w', 'a', 's', 'd'],
            'forward_back': ['w', 'w', 's', 's'],
            'left_right': ['a', 'a', 'd', 'd']
        }
        self.sell_button_position = None
        self.sell_count = 0
        self.is_selling = False
        self.is_walking = False
        self.current_status = "STOPPED"

    def get_current_status(self):
        if not self.dig_tool.running:
            return "STOPPED"
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
            self.is_walking = True
            walk_duration = self.dig_tool.get_param('walk_duration') / 1000.0
            self.keyboard_controller.press(direction)
            time.sleep(walk_duration)
            self.keyboard_controller.release(direction)
            self.is_walking = False
        except Exception as e:
            self.is_walking = False
            print(f"Error in walk step: {e}")

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
            self.walk_pattern_index = (self.walk_pattern_index + 1) % len(pattern)
            return direction

    def can_auto_sell(self):
        auto_walk_enabled = self.dig_tool.get_param('auto_walk_enabled')
        auto_sell_enabled = self.dig_tool.get_param('auto_sell_enabled')

        if auto_sell_enabled and not auto_walk_enabled:
            self.dig_tool.update_status("Auto-sell disabled: Auto-walk must be enabled!")
            return False

        return auto_sell_enabled and self.sell_button_position is not None


    def perform_auto_sell(self):
        try:
            if not self.can_auto_sell():
                return

            self.is_selling = True
            self.dig_tool.update_status("Auto-selling...")

            self.send_key('g')
            time.sleep(0.3)

            sell_delay = max(self.dig_tool.get_param('sell_delay') / 1000.0, 2.5)
            time.sleep(sell_delay)

            x, y = self.sell_button_position

            self.mouse_controller.position = (x, y)
            time.sleep(0.1)
            self.mouse_controller.click(Button.left)
            time.sleep(0.1)
            
            time.sleep(2.5)
            self.send_key('g')
            time.sleep(1.0)
            self.sell_count += 1
            self.dig_tool.update_status(f"Auto-sell #{self.sell_count} completed")

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
        

        for i in range(5, 0, -1):
            self.dig_tool.update_status(f"Test click in {i} seconds... Position: ({x}, {y})")
            time.sleep(1.0)

        self.dig_tool.update_status("Performing AutoIt test click...")
        

        self.mouse_controller.position = (x, y)
        time.sleep(0.1)
        self.mouse_controller.click(Button.left)
        time.sleep(0.1)
        self.dig_tool.update_status("Test click completed.")

    def send_key(self, key, duration=0.1):
        try:
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