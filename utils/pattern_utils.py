def get_step_colors(step):
    step_lower = step.lower()

    if "w" in step_lower and "a" in step_lower:
        # Forward-left - purple theme
        return "#f3e5f5", "#7b1fa2", "#9c27b0", "#e1bee7"
    elif "w" in step_lower and "d" in step_lower:
        # Forward-right - teal theme
        return "#e0f2f1", "#00695c", "#009688", "#b2dfdb"
    elif "s" in step_lower and "a" in step_lower:
        # Back-left - brown theme
        return "#efebe9", "#5d4037", "#795548", "#d7ccc8"
    elif "s" in step_lower and "d" in step_lower:
        # Back-right - pink theme
        return "#fce4ec", "#c2185b", "#e91e63", "#f8bbd9"
    elif "w" in step_lower or "up" in step_lower:
        # Forward/Up - green theme
        return "#e8f5e8", "#2e7d32", "#4caf50", "#c8e6c9"
    elif "s" in step_lower or "down" in step_lower:
        # Back/Down - red theme
        return "#ffebee", "#c62828", "#f44336", "#ffcdd2"
    elif "a" in step_lower or "left" in step_lower:
        # Left - blue theme
        return "#e3f2fd", "#1976d2", "#2196f3", "#bbdefb"
    elif "d" in step_lower or "right" in step_lower:
        # Right - orange theme
        return "#fff3e0", "#f57c00", "#ff9800", "#ffe0b2"
    elif "shift" in step_lower:
        # Shift - purple theme
        return "#f3e5f5", "#7b1fa2", "#9c27b0", "#e1bee7"
    elif "ctrl" in step_lower:
        # Control - dark blue theme
        return "#e1f5fe", "#01579b", "#03a9f4", "#b3e5fc"
    elif "alt" in step_lower:
        # Alt - indigo theme
        return "#e8eaf6", "#283593", "#3f51b5", "#c5cae9"
    elif "space" in step_lower:
        # Space - cyan theme
        return "#e0f7fa", "#00838f", "#00bcd4", "#b2ebf2"
    else:
        # Default - gray theme
        return "#f5f5f5", "#424242", "#757575", "#e0e0e0"


def format_step_text(step):
    if "+" in step:
        return step.upper()
    elif len(step) > 1:
        single_keys = [
            "shift",
            "ctrl",
            "alt",
            "space",
            "enter",
            "tab",
            "backspace",
            "delete",
            "up",
            "down",
            "left",
            "right",
            "escape",
            "home",
            "end",
            "insert",
            "page up",
            "page down",
            "left shift",
            "right shift",
            "left ctrl",
            "right ctrl",
            "left alt",
            "right alt",
        ]

        if step.lower() in single_keys:
            return step.upper()
        else:
            # legacy
            if all(c.lower() in "wasd" for c in step):
                chars = list(step.upper())
                return "+".join(chars)
            else:
                return step.upper()
    else:
        return step.upper()


def validate_step_input(step):
    if not step or not step.strip():
        return False

    keys = [key.strip().lower() for key in step.split("+")]

    valid_special_keys = {
        "space",
        "shift",
        "ctrl",
        "alt",
        "tab",
        "enter",
        "esc",
        "escape",
        "up",
        "down",
        "left",
        "right",
        "home",
        "end",
        "pageup",
        "pagedown",
    }

    for key in keys:
        if not (key.isalnum() or key in valid_special_keys):
            return False

    return True


def safe_schedule_ui_update(window, delay, callback):
    if window:
        try:
            window.after(delay, callback)
        except:
            pass


def check_button_cooldown(last_click_time, cooldown_duration):
    import time

    current_time = time.time()
    if current_time - last_click_time < cooldown_duration:
        return False, current_time
    return True, current_time


def validate_pattern_data(pattern_data, show_error_callback=None):
    if not isinstance(pattern_data, dict):
        if show_error_callback:
            show_error_callback("Invalid pattern file format.")
        return False

    required_fields = ["name", "pattern"]
    missing_fields = [field for field in required_fields if field not in pattern_data]
    if missing_fields:
        missing_str = ", ".join(missing_fields)
        if show_error_callback:
            show_error_callback(f"Missing required fields: {missing_str}")
        return False

    pattern = pattern_data["pattern"]
    if not isinstance(pattern, list) or not pattern:
        if show_error_callback:
            show_error_callback("Invalid pattern data.")
        return False

    for i, step in enumerate(pattern):
        if isinstance(step, dict):
            if "key" not in step:
                if show_error_callback:
                    show_error_callback(
                        f"Step {i+1}: Missing 'key' field in pattern step."
                    )
                return False
            key_value = str(step["key"]).strip()
            if not key_value:
                if show_error_callback:
                    show_error_callback(f"Step {i+1}: Key cannot be empty.")
                return False
        elif isinstance(step, str):
            if not step.strip():
                if show_error_callback:
                    show_error_callback(f"Step {i+1}: Key cannot be empty.")
                return False
        else:
            step_type = type(step).__name__
            if show_error_callback:
                show_error_callback(
                    f"Step {i+1}: Invalid step format. Expected string or dict with 'key' field, got {step_type}."
                )
            return False

    return True


def is_single_pattern(data):
    return isinstance(data, dict) and "name" in data and "pattern" in data


def clean_pattern_data(pattern_data):
    clean_data = {}
    for key, value in pattern_data.items():
        if key not in ["exported_from", "version", "type"]:
            clean_data[key] = value
    return clean_data


def process_pattern_steps(raw_pattern):
    pattern = []
    for i, move in enumerate(raw_pattern):
        if isinstance(move, dict) and "key" in move:
            key_value = str(move["key"]).upper().strip()
            if not key_value:
                return False, f"Step {i+1}: Key cannot be empty"
            clean_step = {
                "key": key_value,
                "duration": move.get("duration", None),
                "click": move.get("click", True),
            }
            pattern.append(clean_step)
        elif isinstance(move, str):
            key_value = move.upper().strip()
            if not key_value:
                return False, f"Step {i+1}: Key cannot be empty"
            pattern.append({"key": key_value, "duration": None, "click": True})
        else:
            step_type = type(move).__name__
            return (
                False,
                f"Step {i+1}: Invalid step format. Expected string or dict with 'key' field, got {step_type}",
            )

    return True, pattern


def open_custom_pattern_manager(dig_tool_instance):
    if dig_tool_instance.custom_pattern_window is None:
        from interface.custom_pattern_window import CustomPatternWindow
        dig_tool_instance.custom_pattern_window = CustomPatternWindow(
            dig_tool_instance, dig_tool_instance.automation_manager
        )
    dig_tool_instance.custom_pattern_window.show_window()

def update_walk_pattern_dropdown(dig_tool_instance):
    if hasattr(dig_tool_instance.main_window, "walk_pattern_combo"):
        current_value = dig_tool_instance.main_window.walk_pattern_combo.get()
        pattern_info = dig_tool_instance.automation_manager.get_pattern_list()
        pattern_names = list(pattern_info.keys())

        dig_tool_instance.main_window.walk_pattern_combo["values"] = pattern_names

        if current_value in pattern_names:
            dig_tool_instance.main_window.walk_pattern_combo.set(current_value)
        elif pattern_names:
            dig_tool_instance.main_window.walk_pattern_combo.set(pattern_names[0])

    if dig_tool_instance.autowalk_overlay and dig_tool_instance.autowalk_overlay.visible:
        dig_tool_instance.autowalk_overlay.update_path_visualization()

def on_walk_pattern_changed(dig_tool_instance, *args):
    if (
        hasattr(dig_tool_instance, "autowalk_overlay")
        and dig_tool_instance.autowalk_overlay
        and dig_tool_instance.autowalk_overlay.visible
    ):
        dig_tool_instance.autowalk_overlay.update_pattern_name()
        dig_tool_instance.autowalk_overlay.update_path_visualization()

    dig_tool_instance.root.after_idle(
        lambda: dig_tool_instance.settings_manager.auto_save_setting("coordinates")
    )
