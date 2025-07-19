import os
import keyboard

def ensure_debug_dir(dig_tool_instance):
    if get_param(dig_tool_instance, "debug_clicks_enabled") and not os.path.exists(
        dig_tool_instance.debug_dir
    ):
        os.makedirs(dig_tool_instance.debug_dir)


def get_param(dig_tool_instance, key):
    if key == "system_latency":
        from utils.system_utils import get_cached_system_latency
        return get_cached_system_latency(dig_tool_instance)
    
    default_value = dig_tool_instance.settings_manager.get_default_value(key)
    
    if key in dig_tool_instance.param_vars:
        try:
            value = dig_tool_instance.param_vars[key].get()
            if isinstance(value, str) and value.strip() == "":
                return default_value
            
            if default_value is not None:
                if isinstance(default_value, bool):
                    return bool(value)
                elif isinstance(default_value, int):
                    try:
                        return int(float(value)) if isinstance(value, str) else int(value)
                    except (ValueError, TypeError):
                        return default_value
                elif isinstance(default_value, float):
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return default_value
                else:
                    return value
            
            return value
        except:
            if default_value is not None:
                try:
                    dig_tool_instance.param_vars[key].set(default_value)
                except:
                    pass  # Ignore tkinter threading issues
                return default_value
    
    attr_value = getattr(dig_tool_instance, key, None)
    return attr_value if attr_value is not None else default_value


def set_param(dig_tool_instance, key, value):
    if key in dig_tool_instance.param_vars:
        try:
            if isinstance(value, str) and value.strip() == "":
                default_value = dig_tool_instance.settings_manager.get_default_value(key)
                if default_value is not None:
                    try:
                        dig_tool_instance.param_vars[key].set(default_value)
                        setattr(dig_tool_instance, key, default_value)
                    except:
                        setattr(dig_tool_instance, key, default_value)  
                    return

            if hasattr(dig_tool_instance.settings_manager, "validate_param_value"):
                if not dig_tool_instance.settings_manager.validate_param_value(key, value):
                    default_value = dig_tool_instance.settings_manager.get_default_value(key)
                    if default_value is not None:
                        try:
                            dig_tool_instance.param_vars[key].set(default_value)
                            setattr(dig_tool_instance, key, default_value)
                        except:
                            setattr(dig_tool_instance, key, default_value)  
                        return

            try:
                dig_tool_instance.param_vars[key].set(value)
            except:
                pass  # Ignore tkinter threading issues
        except:
            default_value = dig_tool_instance.settings_manager.get_default_value(key)
            if default_value is not None:
                try:
                    dig_tool_instance.param_vars[key].set(default_value)
                    setattr(dig_tool_instance, key, default_value)
                except:
                    setattr(dig_tool_instance, key, default_value) 
                return

    setattr(dig_tool_instance, key, value)


def validate_keybind(key_name, key_value):
    if not key_value or key_value.strip() == "":
        return False, "Keybind cannot be empty"

    invalid_chars = [" ", "\t", "\n", "\r"]
    if any(char in key_value for char in invalid_chars):
        return False, "Keybind cannot contain spaces or whitespace"

    try:
        keyboard.parse_hotkey(key_value)
        return True, "Valid keybind"
    except Exception as e:
        return False, f"Invalid key name: {e}"


def validate_numeric_parameter(value, param_name, min_val=None, max_val=None):
    try:
        num_value = float(value)
        if min_val is not None and num_value < min_val:
            return False, f"{param_name} must be at least {min_val}"
        if max_val is not None and num_value > max_val:
            return False, f"{param_name} must be at most {max_val}"
        return True, "Valid numeric value"
    except (ValueError, TypeError):
        return False, f"{param_name} must be a valid number"


def validate_boolean_parameter(value, param_name):
    if isinstance(value, bool):
        return True, "Valid boolean value"
    if isinstance(value, str):
        if value.lower() in ['true', 'false', '1', '0', 'yes', 'no']:
            return True, "Valid boolean value"
    return False, f"{param_name} must be a boolean value"


def validate_coordinate(value, param_name):
    try:
        coord = int(value)
        if coord < 0:
            return False, f"{param_name} must be non-negative"
        return True, "Valid coordinate"
    except (ValueError, TypeError):
        return False, f"{param_name} must be a valid integer"


def validate_color_range(value, param_name):
    try:
        color_val = int(value)
        if 0 <= color_val <= 255:
            return True, "Valid color value"
        else:
            return False, f"{param_name} must be between 0 and 255"
    except (ValueError, TypeError):
        return False, f"{param_name} must be a valid integer"


def validate_percentage(value, param_name):
    try:
        percent = float(value)
        if 0 <= percent <= 100:
            return True, "Valid percentage"
        else:
            return False, f"{param_name} must be between 0 and 100"
    except (ValueError, TypeError):
        return False, f"{param_name} must be a valid number"


def validate_timeout(value, param_name):
    try:
        timeout = float(value)
        if timeout > 0:
            return True, "Valid timeout"
        else:
            return False, f"{param_name} must be greater than 0"
    except (ValueError, TypeError):
        return False, f"{param_name} must be a valid positive number"
