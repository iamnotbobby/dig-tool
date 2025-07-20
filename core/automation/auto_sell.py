import time
import threading
import autoit
from pynput.keyboard import Key
from utils.debug_logger import logger
from utils.config_management import get_param
from utils.system_utils import find_and_focus_roblox_window


class AutoSellManager:

    def __init__(self, dig_tool, keyboard_controller, shift_manager):
        self.dig_tool = dig_tool
        self.keyboard_controller = keyboard_controller
        self.shift_manager = shift_manager
        

        self.sell_button_position = None
        self.sell_count = 0
        self.is_selling = False
        
     
        self.items_sold_total = 0
        self.engagement_monitoring_thread = None
        self.stop_engagement_monitoring = False

    def is_auto_sell_ready(self):
        if not self.dig_tool.running or not get_param(self.dig_tool, "auto_sell_enabled") or self.is_selling:
            return False

        auto_sell_method = get_param(self.dig_tool, "auto_sell_method")
        if auto_sell_method == "button_click":
            return self.sell_button_position is not None
        elif auto_sell_method == "ui_navigation":
            return True
        else:
            logger.warning(f"Unknown auto_sell_method: {auto_sell_method}")
            return False

    def can_auto_sell(self):
        try:
            auto_sell_enabled = get_param(self.dig_tool, "auto_sell_enabled")
            if not auto_sell_enabled:
                return False
                
            return self.is_auto_sell_ready()
        except Exception as e:
            logger.error(f"Error checking auto-sell availability: {e}")
            return False

    def autoit_click(self, x, y, retries=3):
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            logger.error(f"Invalid click coordinates: x={x}, y={y}")
            return False
            
        for attempt in range(retries):
            try:
                autoit.mouse_move(x, y, speed=2)
                time.sleep(0.1)

                current_pos = autoit.mouse_get_pos()
                tolerance = 5

                if (abs(current_pos[0] - x) <= tolerance and abs(current_pos[1] - y) <= tolerance):
                    autoit.mouse_click("left", int(x), int(y), speed=2)
                    time.sleep(0.1)
                    return True
                else:
                    logger.warning(f"Mouse position mismatch: expected ({x}, {y}), got {current_pos}")
                    if attempt < retries - 1:
                        time.sleep(0.2)
                        continue

            except (OSError, WindowsError, Exception) as com_error:
                logger.warning(f"AutoIt error attempt {attempt + 1}: {com_error}")
                try:
                    from utils.system_utils import send_click
                    send_click()
                    return True
                except Exception as fallback_error:
                    logger.warning(f"Fallback click also failed: {fallback_error}")
                    if attempt < retries - 1:
                        time.sleep(0.2)
                        continue

        logger.error("All AutoIt click attempts failed")
        return False

    def _process_sell_completion(self, method_name=""):
        try:
            restored_shifts = self.shift_manager.restore_shifts_after_sell()
            if restored_shifts:
                logger.info(f"Restored shift keys after auto-sell: {restored_shifts}")
                time.sleep(0.1)
        except Exception as e:
            logger.warning(f"Failed to restore shifts after sell completion: {e}")

        self.sell_count += 1

        try:
            sell_every_x_digs = get_param(self.dig_tool, "sell_every_x_digs")
            if sell_every_x_digs and int(sell_every_x_digs) > 0:
                items_sold = min(self.dig_tool.dig_count, int(sell_every_x_digs))
                
                # Update sold items tracking for walkspeed calculations
                self.items_sold_total += items_sold
                
                logger.info(f"Auto-sell completed: sold {items_sold} items, total dig_count: {self.dig_tool.dig_count}, total sold: {self.items_sold_total}")
        except (ValueError, TypeError) as e:
            logger.warning(f"Error processing sell_every_x_digs parameter: {e}")

        method_suffix = f" ({method_name})" if method_name else ""
        status_message = f"Auto-sell #{self.sell_count} completed{method_suffix}"
        
        try:
            self.dig_tool.update_status(status_message)
            logger.info(f"Auto-sell #{self.sell_count} completed successfully{method_suffix}")
        except Exception as e:
            logger.error(f"Failed to update status after sell completion: {e}")

    def get_walkspeed_dig_count(self):
        try:
            if not hasattr(self.dig_tool, 'dig_count'):
                logger.warning("dig_tool.dig_count not available")
                return 0
            return max(0, self.dig_tool.dig_count - self.items_sold_total)
        except (TypeError, AttributeError) as e:
            logger.error(f"Error calculating walkspeed dig count: {e}")
            return 0

    def perform_auto_sell(self):
     
        auto_sell_method = get_param(self.dig_tool, "auto_sell_method")
        
        if auto_sell_method == "button_click":
            return self._perform_auto_sell_button_click()
        elif auto_sell_method == "ui_navigation":
            return self._perform_auto_sell_ui_navigation()
        else:
            logger.error(f"Unknown auto_sell_method: {auto_sell_method}")
            return False

    def _restore_shifts_on_error(self):
        try:
            restored_shifts = self.shift_manager.restore_shifts_after_sell()
            if restored_shifts:
                logger.info(f"Restored shift keys after auto-sell exception: {restored_shifts}")
        except Exception as restore_error:
            logger.warning(f"Failed to restore shifts after auto-sell exception: {restore_error}")

    def _perform_auto_sell_button_click(self):
        try:
            if self.is_selling:
                logger.warning("Auto-sell already in progress, skipping")
                return

            if not get_param(self.dig_tool, "auto_sell_enabled") or not self.sell_button_position or not self.dig_tool.running:
                logger.warning("Auto-sell aborted: disabled, no button position, or tool not running")
                return

            logger.info(f"Starting auto-sell sequence #{self.sell_count + 1}")
            self.is_selling = True
            self.dig_tool.update_status("Auto-selling...")

            time.sleep(0.1)

            walking_lock = getattr(self.dig_tool.automation_manager, 'walking_lock', None)
            lock_context = walking_lock if walking_lock else self._dummy_context()

            with lock_context:
                disabled_shifts = self.shift_manager.disable_active_shifts_for_sell()
                if disabled_shifts:
                    logger.info(f"Disabled shift keys for auto-sell: {disabled_shifts}")
                    time.sleep(0.2)

                try:
                    autoit.send("g")
                except (OSError, WindowsError, Exception) as e:
                    logger.warning(f"AutoIt send 'g' failed, using keyboard fallback: {e}")
                    self.keyboard_controller.press_and_release("g")

                time.sleep(0.5)
                
                if not self.sell_button_position or len(self.sell_button_position) != 2:
                    logger.error("Auto-sell failed: no sell button position set or invalid format")
                    self.dig_tool.update_status("Auto-sell failed: no sell button position")
                    self.is_selling = False
                    self._restore_shifts_on_error()
                    return
                
                x = self.sell_button_position[0]
                y = self.sell_button_position[1]
                sell_delay = get_param(self.dig_tool, "sell_delay") or 1000
                sell_delay_seconds = sell_delay / 1000.0
                time.sleep(sell_delay_seconds)

                success = self.autoit_click(x, y)

                if success:
                    logger.info("Sell click successful")
                    time.sleep(2.5)
                    try:
                        autoit.send("g")
                    except (OSError, WindowsError, Exception) as e:
                        logger.warning(f"AutoIt send 'g' failed, using keyboard fallback: {e}")
                        self.keyboard_controller.press("g")
                        self.keyboard_controller.release("g")
                    time.sleep(1.0)

                    self._process_sell_completion()
                else:
                    logger.error("Auto-sell failed: AutoIt click error")
                    self.dig_tool.update_status("Auto-sell failed: AutoIt click error")
                    
                    try:
                        autoit.send("g")
                        logger.info("Closed inventory after failed sell click")
                    except (OSError, WindowsError, Exception) as e:
                        logger.warning(f"AutoIt send 'g' failed after click failure, using keyboard fallback: {e}")
                        self.keyboard_controller.press("g")
                        self.keyboard_controller.release("g")
                    time.sleep(0.5)

            self.is_selling = False
            
            if get_param(self.dig_tool, "auto_walk_enabled"):
                self._monitor_post_sell_engagement()
            else:
                logger.debug("Skipping post-sell engagement monitoring (auto-walk disabled)")
            return

        except Exception as e:
            self.is_selling = False
            self._restore_shifts_on_error()
            error_msg = f"Error in auto-sell: {e}"
            logger.error(error_msg)
            self.dig_tool.update_status(f"Auto-sell failed: {e}")

    def _perform_auto_sell_ui_navigation(self):
        try:
            if self.is_selling:
                logger.warning("Auto-sell already in progress, skipping")
                return False

            if not get_param(self.dig_tool, "auto_sell_enabled") or not self.dig_tool.running:
                logger.warning("Auto-sell aborted: disabled or tool not running")
                return False

            logger.info(f"Starting UI navigation auto-sell sequence #{self.sell_count + 1}")
            self.is_selling = True
            self.dig_tool.update_status("Auto-selling (UI Navigation)...")

            time.sleep(0.1)

            walking_lock = getattr(self.dig_tool.automation_manager, 'walking_lock', None)
            lock_context = walking_lock if walking_lock else self._dummy_context()

            with lock_context:
                if not find_and_focus_roblox_window():
                    logger.warning("Could not focus Roblox window for UI navigation auto-sell")
                
                disabled_shifts = self.shift_manager.disable_active_shifts_for_sell()
                if disabled_shifts:
                    logger.info(f"Disabled shift keys for auto-sell: {disabled_shifts}")
                    time.sleep(0.2)

                inventory_key = "g"
                user_sequence = get_param(self.dig_tool, "auto_sell_ui_sequence") or "down,up,enter"
                sell_sequence = f"\\,{user_sequence},\\"
                step_delay = 0.5
                sell_delay = get_param(self.dig_tool, "sell_delay") or 1000
                sell_delay_seconds = sell_delay / 1000.0
                inventory_open_delay = 0.9
                inventory_close_delay = 0.8

                logger.info(f"Using sequence: '{sell_sequence}' (user: '{user_sequence}')")

                self._send_key_safe(inventory_key)
                time.sleep(inventory_open_delay)

                if sell_sequence:
                    sequence_steps = [step.strip() for step in sell_sequence.split(',') if step.strip()]
                    
                    for step in sequence_steps:
                        if not self.dig_tool.running or not self.is_selling:
                            logger.info("Auto-sell aborted: tool stopped or selling flag cleared")
                            break
                        if step:
                            if step.lower() == "enter":
                                time.sleep(sell_delay_seconds)
                            
                            logger.info(f"Sending '{step}' key")
                            self._send_key_safe(step)
                            time.sleep(step_delay)
                else:
                    logger.warning("No sell sequence found in config!")

                time.sleep(3.0)
                self._send_key_safe(inventory_key)
                time.sleep(inventory_close_delay)

                self._process_sell_completion("UI Nav")

            self.is_selling = False
            
            if get_param(self.dig_tool, "auto_walk_enabled"):
                self._monitor_post_sell_engagement()
            else:
                logger.debug("Skipping post-sell engagement monitoring (auto-walk disabled)")
            return True

        except Exception as e:
            self.is_selling = False
            self._restore_shifts_on_error()
            error_msg = f"Error in UI navigation auto-sell: {e}"
            logger.error(error_msg)
            self.dig_tool.update_status(f"Auto-sell failed: {e}")
            return False

    def _monitor_post_sell_engagement(self):
        self.stop_engagement_monitoring = True
        
        if self.engagement_monitoring_thread and self.engagement_monitoring_thread.is_alive():
            logger.debug("Stopping previous engagement monitoring thread")
            self.engagement_monitoring_thread.join(timeout=0.5)
        
        self.stop_engagement_monitoring = False
        
        self.engagement_monitoring_thread = threading.Thread(
            target=self._engagement_monitoring_worker, 
            daemon=True
        )
        self.engagement_monitoring_thread.start()
    
    def _engagement_monitoring_worker(self):
        try:
            engagement_enabled = get_param(self.dig_tool, "auto_sell_target_engagement_enabled")
            if not engagement_enabled:
                logger.debug("Post-sell engagement monitoring disabled by user setting")
                return
                
            target_engagement_timeout = get_param(self.dig_tool, "auto_sell_target_engagement_timeout") or 5.0
            
            if target_engagement_timeout <= 0:
                logger.debug("Post-sell engagement monitoring disabled (timeout <= 0)")
                return
                
            target_check_interval = 0.1
            engagement_start_time = time.time()
            
            logger.info(f"Monitoring target engagement for {target_engagement_timeout}s after auto-sell")
            
            checks_performed = 0
            while time.time() - engagement_start_time < target_engagement_timeout:
                if not self.dig_tool.running or self.stop_engagement_monitoring:
                    if self.stop_engagement_monitoring:
                        logger.debug("Post-sell engagement monitoring stopped (new auto-sell started)")
                    else:
                        logger.info("Post-sell engagement monitoring aborted: tool stopped")
                    return
                    
                try:
                    target_engaged = hasattr(self.dig_tool, 'target_engaged') and self.dig_tool.target_engaged
                    checks_performed += 1
                    
                    if target_engaged:
                        logger.info(f"Target engagement detected after {time.time() - engagement_start_time:.1f}s")
                        return
                except Exception as e:
                    logger.warning(f"Error checking target engagement: {e}")
                
                time.sleep(target_check_interval)
            
            if not self.stop_engagement_monitoring:
                logger.warning(f"No target engagement detected after {target_engagement_timeout}s, applying fallback")
                self._apply_auto_sell_fallback()
            
        except Exception as e:
            logger.error(f"Error in post-sell engagement monitoring: {e}")
            if not self.stop_engagement_monitoring:
                try:
                    self._apply_auto_sell_fallback()
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")

    def _apply_auto_sell_fallback(self):
        try:
            logger.info("Auto-sell fallback: Re-closing inventory to ensure proper state")
            self._send_key_safe("g")
            time.sleep(0.8)
            
            if hasattr(self.dig_tool, 'automation_manager') and get_param(self.dig_tool, "auto_walk_enabled"):
                logger.info("Auto-sell fallback: Advancing walk pattern")
                self.dig_tool.automation_manager.advance_walk_pattern()
        except Exception as e:
            logger.error(f"Error in auto-sell fallback: {e}")

    def _send_key_safe(self, key):
        if not key:
            logger.warning("Empty key provided to _send_key_safe")
            return
            
        key_name = str(key).lower().strip()
        
        special_keys = {
            "down": ("{DOWN}", Key.down), "↓": ("{DOWN}", Key.down),
            "up": ("{UP}", Key.up), "↑": ("{UP}", Key.up),
            "left": ("{LEFT}", Key.left), "←": ("{LEFT}", Key.left),
            "right": ("{RIGHT}", Key.right), "→": ("{RIGHT}", Key.right),
            "enter": ("{ENTER}", Key.enter), "return": ("{ENTER}", Key.enter),
        }
        
        try:
            if key_name in special_keys:
                autoit_cmd, key_obj = special_keys[key_name]
                autoit.send(autoit_cmd)
                logger.debug(f"Sent special key via AutoIt: {key_name}")
            else:
                autoit.send(key)
                logger.debug(f"Sent key via AutoIt: {key}")
        except (OSError, WindowsError, Exception) as e:
            logger.warning(f"AutoIt send failed for key '{key}', using keyboard fallback: {e}")
            try:
                if key_name in special_keys:
                    _, key_obj = special_keys[key_name]
                    self.keyboard_controller.press(key_obj)
                    self.keyboard_controller.release(key_obj)
                else:
                    if hasattr(Key, key_name):
                        key_obj = getattr(Key, key_name)
                        self.keyboard_controller.press(key_obj)
                        self.keyboard_controller.release(key_obj)
                    else:
                        self.keyboard_controller.press(key)
                        self.keyboard_controller.release(key)
                logger.debug(f"Sent key via keyboard fallback: {key}")
            except Exception as fallback_error:
                logger.error(f"Both AutoIt and keyboard fallback failed for key '{key}': {fallback_error}")

    def _countdown_with_status(self, message_format, seconds=5):
        for i in range(seconds, 0, -1):
            self.dig_tool.update_status(message_format.format(i))
            time.sleep(1.0)

    def test_sell_button_click(self):
        auto_sell_method = get_param(self.dig_tool, "auto_sell_method")
        
        if auto_sell_method == "button_click":
            if not self.sell_button_position:
                self.dig_tool.update_status("Sell button not set!")
                return
            threading.Thread(target=self._test_sell_click_with_delay, daemon=True).start()
        elif auto_sell_method == "ui_navigation":
            threading.Thread(target=self._test_ui_navigation_with_delay, daemon=True).start()
        else:
            self.dig_tool.update_status(f"Unknown auto-sell method: {auto_sell_method}")

    def _test_ui_navigation_with_delay(self):
        logger.info("Testing UI navigation auto-sell sequence")
        
        self._countdown_with_status("UI navigation test in {} seconds...")
        self.dig_tool.update_status("Testing UI navigation sequence...")

        try:
            if not find_and_focus_roblox_window():
                logger.warning("Could not focus Roblox window for UI navigation test")
            
            inventory_key = "g"
            user_sequence = get_param(self.dig_tool, "auto_sell_ui_sequence") or "down,up,enter"
            sell_sequence = f"\\,{user_sequence},\\"
            step_delay = 0.3
            inventory_open_delay = 0.7
            inventory_close_delay = 0.8

            logger.info(f"Using sequence: '{sell_sequence}' (user: '{user_sequence}')")
            
            self._send_key_safe(inventory_key)
            time.sleep(inventory_open_delay)

            if sell_sequence:
                sequence_steps = [step.strip() for step in sell_sequence.split(',') if step.strip()]
                logger.info(f"Parsed sequence steps: {sequence_steps}")
                
                for i, step in enumerate(sequence_steps):
                    if step:
                        logger.info(f"STEP {i+1}/{len(sequence_steps)}: Sending '{step}' key")
                        self._send_key_safe(step)
                        time.sleep(step_delay)
            else:
                logger.warning("No sell sequence found in config!")

            self._send_key_safe(inventory_key)
            time.sleep(inventory_close_delay)

            self.dig_tool.update_status("UI navigation test completed successfully!")
            logger.info("UI navigation test sequence completed")

        except Exception as e:
            error_msg = f"UI navigation test failed: {e}"
            logger.error(error_msg)
            self.dig_tool.update_status(error_msg)

    def _test_sell_click_with_delay(self):
        if not self.sell_button_position or len(self.sell_button_position) != 2:
            logger.error("Cannot test sell click: no sell button position set or invalid format")
            self.dig_tool.update_status("Test failed: no sell button position set")
            return
            
        x = self.sell_button_position[0]
        y = self.sell_button_position[1]
        logger.info(f"Testing AutoIt click at position: {x}, {y}")

        self._countdown_with_status(f"Test click in {{}} seconds... Position: ({x}, {y})")
        self.dig_tool.update_status("Performing AutoIt test click...")

        success = self.autoit_click(x, y)
        status = "AutoIt test click completed successfully!" if success else "AutoIt test click failed!"
        self.dig_tool.update_status(status)

    def _dummy_context(self):
    
        class DummyContext:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                return False
        return DummyContext()
