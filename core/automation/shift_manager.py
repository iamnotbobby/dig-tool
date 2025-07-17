import time
from pynput.keyboard import Key
from utils.debug_logger import logger


class ShiftManager:
    
    def __init__(self, keyboard_controller):
        self.keyboard_controller = keyboard_controller
        self.shiftlock_state = {
            "shift": False,
            "right_shift": False,
            "was_active_before_sell": False
        }
    
    def update_shiftlock_state(self, key, is_pressed):
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

    def is_shift_key(self, key):
        key = key.lower().strip()
        return key in ["shift", "left shift", "right shift"]

    def toggle_shiftlock_on_shift_press(self, key):
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
