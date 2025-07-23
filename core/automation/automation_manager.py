# TODO: remove unnecessary wrapper functions

import threading
import time
import gc
from pynput.keyboard import Controller as KeyboardController
from utils.debug_logger import logger

from .shift_manager import ShiftManager
from .movement import MovementManager
from .auto_shovel import AutoShovelManager
from .pattern_manager import PatternManager
from .auto_sell import AutoSellManager


class AutomationManager:
    
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance
        self.keyboard_controller = KeyboardController()
        
        self.shift_manager = ShiftManager(self.keyboard_controller)
        self.movement_manager = MovementManager(dig_tool_instance, self.keyboard_controller, self.shift_manager)
        self.auto_shovel_manager = AutoShovelManager(dig_tool_instance, self.keyboard_controller)
        self.pattern_manager = PatternManager(dig_tool_instance, self.keyboard_controller, self.shift_manager)
        self.auto_sell_manager = AutoSellManager(dig_tool_instance, self.keyboard_controller, self.shift_manager)
        
        self.last_successful_direction = None
        
        self.recording_start_time = None
        
       
        self.walking_lock = threading.Lock()
        self._is_walking = False 


    @property 
    def is_walking(self):
        
        return self.movement_manager.is_walking
    
    @is_walking.setter
    def is_walking(self, value):
        
        self.movement_manager.is_walking = value
        self._is_walking = value 

    @property
    def sell_button_position(self):
     
        return self.auto_sell_manager.sell_button_position
    
    @sell_button_position.setter
    def sell_button_position(self, value):
 
        self.auto_sell_manager.sell_button_position = value

    @property
    def sell_count(self):
       
        return self.auto_sell_manager.sell_count
    
    @sell_count.setter
    def sell_count(self, value):
      
        self.auto_sell_manager.sell_count = value

    @property
    def is_selling(self):
      
        return self.auto_sell_manager.is_selling
    
    @is_selling.setter
    def is_selling(self, value):
    
        self.auto_sell_manager.is_selling = value

    @property
    def is_recording(self):
    
        return self.pattern_manager.is_recording
    
    @is_recording.setter
    def is_recording(self, value):
      
        self.pattern_manager.is_recording = value

    @property
    def recorded_pattern(self):
      
        return self.pattern_manager.recorded_pattern
    
    @recorded_pattern.setter
    def recorded_pattern(self, value):
    
        self.pattern_manager.recorded_pattern = value

    @property
    def _preview_active(self):
      
        return self.pattern_manager._preview_active
    
    @_preview_active.setter
    def _preview_active(self, value):
       
        self.pattern_manager._preview_active = value

    @property
    def _stop_preview(self):
       
        return self.pattern_manager._stop_preview
    
    @_stop_preview.setter
    def _stop_preview(self, value):
  
        self.pattern_manager._stop_preview = value

    @property
    def allow_custom_keys(self):
      
        return self.pattern_manager.allow_custom_keys
    
    @allow_custom_keys.setter
    def allow_custom_keys(self, value):
       
        self.pattern_manager.allow_custom_keys = value

    @property
    def record_click_enabled(self):
   
        return self.pattern_manager.record_click_enabled
    
    @record_click_enabled.setter
    def record_click_enabled(self, value):
    
        self.pattern_manager.record_click_enabled = value

    @property
    def walk_patterns(self):
    
        return self.pattern_manager.walk_patterns
    
    @property
    def walk_pattern_index(self):
 
        return self.movement_manager.walk_pattern_index
    
    @walk_pattern_index.setter
    def walk_pattern_index(self, value):
    
        self.movement_manager.walk_pattern_index = value

    def load_custom_patterns(self):
      
        return self.pattern_manager.load_custom_patterns()

    def save_custom_patterns(self):
       
        return self.pattern_manager.save_custom_patterns()

    def add_custom_pattern(self, name, pattern):
       
        return self.pattern_manager.add_custom_pattern(name, pattern)

    def delete_custom_pattern(self, name):
     
        return self.pattern_manager.delete_custom_pattern(name)

    def get_pattern_list(self):
    
        return self.pattern_manager.get_pattern_list()

    def start_recording_pattern(self, allow_custom_keys=False, click_enabled=True):
     
        return self.pattern_manager.start_recording_pattern(allow_custom_keys, click_enabled)

    def stop_recording_pattern(self):

        return self.pattern_manager.stop_recording_pattern()

    def record_movement(self, direction):
     
        return self.pattern_manager.record_movement(direction)

    def auto_load_patterns(self):
      
        return self.pattern_manager.auto_load_patterns()

    def preview_pattern(self, pattern_name):
      
        return self.pattern_manager.preview_pattern(pattern_name)

    def preview_recorded_pattern(self, pattern):
     
        return self.pattern_manager.preview_recorded_pattern(pattern)

    def stop_preview(self):
       
        self._stop_preview = True
        logger.info("Pattern preview stop requested")
        return True, "Preview stopped"

    def is_preview_active(self):
     
        return self._preview_active

    def save_pattern(self, name, pattern):
       
        return self.pattern_manager.save_pattern(name, pattern)

    def perform_walk_step(self, direction):
        return self.movement_manager.perform_walk_step(
            direction, 
            record_movement_callback=self.record_movement if self.is_recording else None
        )

    def get_next_walk_direction(self):
     
        return self.movement_manager.get_next_walk_direction(self.walk_patterns)

    def get_current_walk_step(self):
   
        return self.movement_manager.get_current_walk_step(self.walk_patterns)

    def advance_walk_pattern(self):
      
        return self.movement_manager.advance_walk_pattern(self.walk_patterns)

    def send_key(self, key, duration=0.1):
        return self.movement_manager.send_key(key, duration)

    def _execute_movement_with_duration(self, direction, duration):
        return self.movement_manager._execute_movement_with_duration(direction, duration)

    def calculate_walkspeed_multiplier(self, items_collected):
      
        return self.movement_manager.calculate_walkspeed_multiplier(items_collected)

    def update_dig_activity(self):
   
        return self.auto_shovel_manager.update_dig_activity()

    def update_click_activity(self):
   
        return self.auto_shovel_manager.update_click_activity()

    def update_target_lock_activity(self):
     
        return self.auto_shovel_manager.update_target_lock_activity()

    def should_re_equip_shovel(self):
       
        return self.auto_shovel_manager.should_re_equip_shovel()

    def re_equip_shovel(self, is_test=False):
        return self.auto_shovel_manager.re_equip_shovel(is_test, self.walking_lock)

    def get_auto_shovel_status(self):
        return self.auto_shovel_manager.get_auto_shovel_status()

    def perform_shovel_action(self):
        return self.auto_shovel_manager.perform_shovel_action()

    def test_shovel_equip(self):
        return self.auto_shovel_manager.test_shovel_equip()

    def is_auto_sell_ready(self):
        return self.auto_sell_manager.is_auto_sell_ready()

    def can_auto_sell(self):
        return self.auto_sell_manager.can_auto_sell()

    def perform_auto_sell(self):
        return self.auto_sell_manager.perform_auto_sell()

    def test_sell_button_click(self):
        return self.auto_sell_manager.test_sell_button_click()

    def get_walkspeed_dig_count(self):
        return self.auto_sell_manager.get_walkspeed_dig_count()

    def autoit_click(self, x, y, retries=3):
        return self.auto_sell_manager.autoit_click(x, y, retries)

    def get_shiftlock_state(self):
        return self.shift_manager.get_shiftlock_state()

    def is_any_shift_active(self):
        return self.shift_manager.is_any_shift_active()

    def disable_active_shifts_for_sell(self):
        return self.shift_manager.disable_active_shifts_for_sell()

    def restore_shifts_after_sell(self):

        return self.shift_manager.restore_shifts_after_sell()

    def disable_active_shifts(self):
        return self.shift_manager.disable_active_shifts()

    def find_and_focus_roblox_window(self):
        from utils.system_utils import find_and_focus_roblox_window
        return find_and_focus_roblox_window()

    def focus_roblox_window(self):
        from utils.system_utils import focus_roblox_window_legacy
        return focus_roblox_window_legacy()

    def get_current_status(self):
        if not self.dig_tool.running:
            return "STOPPED"
        elif self.is_recording:
            return f"RECORDING ({len(self.recorded_pattern)} moves)"
        elif self.is_selling:
            return "AUTO SELLING"
        elif self.is_walking:
            return "WALKING"
        elif hasattr(self.dig_tool, 'param_vars') and self.dig_tool.param_vars.get("auto_walk_enabled", {}).get():
            auto_shovel_status = self.get_auto_shovel_status()
            if "disabled" not in auto_shovel_status.lower():
                return f"AUTO WALKING ({auto_shovel_status})"
            else:
                return "AUTO WALKING"
        else:
            return "ACTIVE"

    def restart_automation(self, reason="Manual restart"):
        logger.info(f"Restarting automation: {reason}")
        try:
            if hasattr(self.dig_tool, 'running') and self.dig_tool.running:
                self.dig_tool.running = False
                if hasattr(self.dig_tool, 'update_status'):
                    self.dig_tool.update_status("Restarting...")
                time.sleep(0.5)
            
            self.dig_tool.running = True
            self.dig_tool.click_count = 0
            self.dig_tool.dig_count = 0
            self.walk_pattern_index = 0
            self.sell_count = 0
            self.is_walking = False
            self.is_selling = False
            
            if hasattr(self.dig_tool, 'velocity_calculator'):
                self.dig_tool.velocity_calculator.reset()
            if hasattr(self.dig_tool, 'item_counts_since_startup'):
                self.dig_tool.item_counts_since_startup = {'junk': 0, 'common': 0, 'unusual': 0, 'scarce': 0, 'legendary': 0, 'mythical': 0, 'divine': 0, 'prismatic': 0}
            if hasattr(self.dig_tool, 'manual_dig_target_disengaged_time'):
                self.dig_tool.manual_dig_target_disengaged_time = 0
                self.dig_tool.manual_dig_was_engaged = False
            if hasattr(self.dig_tool, 'startup_time'):
                self.dig_tool.startup_time = time.time() * 1000
                self.dig_tool._startup_grace_ended = False
            if hasattr(self.dig_tool, 'click_lock') and self.dig_tool.click_lock.locked():
                self.dig_tool.click_lock.release()
            if hasattr(self.dig_tool, 'target_engaged'):
                self.dig_tool.target_engaged = False
            if hasattr(self.dig_tool, 'line_moving_history'):
                self.dig_tool.line_moving_history = []
            
            self.shiftlock_state = {"shift": False, "right_shift": False}
            
            if hasattr(self.dig_tool, 'update_status'):
                self.dig_tool.update_status("Bot Started...")
            from utils.ui_management import update_main_button_text
            update_main_button_text(self.dig_tool)
            logger.info(f"Automation restarted successfully: {reason}")
        except Exception as e:
            logger.error(f"Error during automation restart: {e}")
            if hasattr(self.dig_tool, 'update_status'):
                self.dig_tool.update_status("Restart failed")

    def get_mouse_position(self):
        try:
            from pynput.mouse import Controller as MouseController
            mouse_controller = MouseController()
            return mouse_controller.position
        except Exception as e:
            logger.error(f"Get mouse position failed: {e}")
            return (0, 0)

    def update_custom_keys_setting(self, allow_custom_keys):
        self.allow_custom_keys = allow_custom_keys
        logger.info(f"Updated custom keys setting to: {allow_custom_keys}")

    def update_record_click_setting(self, click_enabled):
   
        self.record_click_enabled = click_enabled
        logger.info(f"Updated record click setting to: {click_enabled}")

    def cleanup(self):
       
        try:
            if self.is_recording:
                self.stop_recording_pattern()

            self.sell_button_position = None
            self.is_selling = False
            self.movement_manager.is_walking = False

            if hasattr(self, "keyboard_controller"):
                try:
                    del self.keyboard_controller
                except:
                    pass
                self.keyboard_controller = None

            if hasattr(self.pattern_manager, 'cleanup'):
                self.pattern_manager.cleanup()

            for _ in range(3):
                gc.collect()

            logger.debug("AutomationManager cleanup completed")

        except Exception as e:
            logger.debug(f"Error during AutomationManager cleanup: {e}")

    @property
    def shiftlock_state(self):
     
        return self.shift_manager.shiftlock_state

    @shiftlock_state.setter
    def shiftlock_state(self, value):
       
        self.shift_manager.shiftlock_state = value
