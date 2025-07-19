import tkinter as tk
from utils.debug_logger import logger
from utils.system_utils import measure_system_latency_for_instance


def initialize_default_param_vars(dig_tool_instance):
    settings_manager = dig_tool_instance.settings_manager
    
    for key, default_value in settings_manager.default_params.items():
        var_type = settings_manager.get_param_type(key)
        dig_tool_instance.param_vars[key] = var_type(value=default_value)
        dig_tool_instance.last_known_good_params[key] = default_value

    for key, default_value in settings_manager.default_keybinds.items():
        dig_tool_instance.keybind_vars[key] = tk.StringVar(value=default_value)


def check_and_enable_buttons(dig_tool_instance):
    if (
        dig_tool_instance.game_area
        and hasattr(dig_tool_instance, "preview_btn")
        and hasattr(dig_tool_instance, "debug_btn")
    ):
        dig_tool_instance.preview_btn.config(state=tk.NORMAL)
        dig_tool_instance.debug_btn.config(state=tk.NORMAL)

        if (
            not dig_tool_instance.main_loop_thread
            or not dig_tool_instance.main_loop_thread.is_alive()
        ):
            dig_tool_instance.start_threads()


def perform_initial_latency_measurement(dig_tool_instance):
    try:
        logger.info("Performing initial system latency measurement...")
        measured_latency = measure_system_latency_for_instance(dig_tool_instance)
        dig_tool_instance._cached_latency = measured_latency
        logger.info(f"System latency measured: {measured_latency}ms")
        return measured_latency
    except Exception as e:
        logger.warning(f"Could not measure system latency automatically: {e}")
        default_latency = 50
        dig_tool_instance._cached_latency = default_latency
        return default_latency
