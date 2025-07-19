import time
import threading
from utils.debug_logger import logger
from utils.config_management import get_param
from utils.system_utils import find_and_focus_roblox_window


class AutoShovelManager:
    
    def __init__(self, dig_tool, keyboard_controller):
        self.dig_tool = dig_tool
        self.keyboard_controller = keyboard_controller
        
        self.last_dig_time = None
        self.last_click_time = None
        self.last_target_lock_time = None
        self.shovel_re_equipped = False
        self.shovel_re_equipped_time = None

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
        if not get_param(self.dig_tool, "auto_shovel_enabled"):
            return False

        current_time = time.time()
        shovel_timeout = get_param(self.dig_tool, "shovel_timeout") * 60

        # Check fallback timeout for stuck state
        if self.shovel_re_equipped and self.shovel_re_equipped_time:
            time_since_reequip = current_time - self.shovel_re_equipped_time
            fallback_timeout = shovel_timeout * 2

            if time_since_reequip > fallback_timeout:
                logger.warning(
                    f"Auto-shovel fallback triggered: No successful digs for "
                    f"{time_since_reequip:.0f}s after shovel re-equip. Resetting flag."
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
                f"Auto-shovel triggered: No item pickups for {time_since_last_dig:.0f}s "
                f"(timeout: {shovel_timeout:.0f}s)"
            )

        return no_recent_pickup

    def re_equip_shovel(self, is_test=False, walking_lock=None):
        try:
            if not is_test and not self.dig_tool.running:
                return False

            if not find_and_focus_roblox_window():
                logger.warning("Could not focus Roblox window for shovel equip")

            shovel_slot = get_param(self.dig_tool, "shovel_slot")
            if shovel_slot < 0 or shovel_slot > 9:
                logger.warning(f"Invalid shovel slot: {shovel_slot}")
                return False

            slot_key = str(shovel_slot) if shovel_slot > 0 else "0"
            equip_mode = get_param(self.dig_tool, "shovel_equip_mode")

            logger.info(
                f"Re-equipping shovel from slot {shovel_slot} (key: {slot_key}) "
                f"using {equip_mode} mode"
            )

            # Use walking lock if provided (for thread safety)
            lock_context = walking_lock if walking_lock else self._dummy_context()
            
            with lock_context:
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
                f"Auto-shovel completed: Equipped shovel from slot {shovel_slot} "
                f"using {mode_text}"
            )
            return True

        except Exception as e:
            logger.error(f"Error re-equipping shovel: {e}")
            return False

    def get_auto_shovel_status(self):
        if not get_param(self.dig_tool, "auto_shovel_enabled"):
            return "Auto-shovel disabled"

        if not self.dig_tool.running:
            return "Auto-shovel (waiting for tool to start)"

        if self.shovel_re_equipped:
            return "Shovel recently re-equipped"

        current_time = time.time()
        shovel_timeout = get_param(self.dig_tool, "shovel_timeout") * 60

        time_since_last_dig = (
            current_time - self.last_dig_time if self.last_dig_time else float("inf")
        )

        if time_since_last_dig >= shovel_timeout:
            return "Ready to re-equip shovel"
        else:
            remaining_time = shovel_timeout - time_since_last_dig
            return f"Auto-shovel in {remaining_time:.0f}s"

    def perform_shovel_action(self):
        try:
            if not find_and_focus_roblox_window():
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

    def test_shovel_equip(self):
        if not get_param(self.dig_tool, "auto_shovel_enabled"):
            self.dig_tool.update_status("Auto-shovel is disabled!")
            return

        shovel_slot = get_param(self.dig_tool, "shovel_slot")
        equip_mode = get_param(self.dig_tool, "shovel_equip_mode")
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
        focus_success = find_and_focus_roblox_window()

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

    def _dummy_context(self):
        class DummyContext:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                return False
        return DummyContext()
