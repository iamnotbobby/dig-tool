import threading
import time
import ctypes
import tkinter as tk
from tkinter import Label
import keyboard
from interface.components import GameOverlay, AutoWalkOverlay
from utils.debug_logger import logger, save_debug_screenshot, log_click_debug, ensure_debug_directory
from utils.config_management import get_param, validate_keybind
from utils.system_utils import send_click


def perform_click_action(
    delay, running, use_custom_cursor, cursor_position, click_lock
):
    if delay > 0:
        time.sleep(float(delay))
        
    if not running:
        return

    if use_custom_cursor and cursor_position:
        try:
            ctypes.windll.user32.SetCursorPos(*cursor_position)
        except:
            pass

    send_click()
    if click_lock.locked():
        click_lock.release()


def cleanup_click_threads(dig_tool_instance):
    dig_tool_instance._click_thread_pool = [
        t for t in dig_tool_instance._click_thread_pool if t.is_alive()
    ]


def perform_click(dig_tool_instance, delay=0):
    perform_click_action(
        delay,
        dig_tool_instance.running,
        get_param(dig_tool_instance, "use_custom_cursor"),
        dig_tool_instance.cursor_position,
        dig_tool_instance.click_lock,
    )
    dig_tool_instance.click_count += 1


def perform_instant_click(dig_tool_instance):
    cleanup_click_threads(dig_tool_instance)
    if len(dig_tool_instance._click_thread_pool) < dig_tool_instance._max_click_threads:
        click_thread = threading.Thread(
            target=lambda: _instant_click(dig_tool_instance), daemon=True
        )
        dig_tool_instance._click_thread_pool.append(click_thread)
        click_thread.start()


def _instant_click(dig_tool_instance):
    if not dig_tool_instance.running:
        return
    if get_param(dig_tool_instance, "use_custom_cursor") and dig_tool_instance.cursor_position:
        try:
            ctypes.windll.user32.SetCursorPos(*dig_tool_instance.cursor_position)
        except:
            pass
    from utils.system_utils import send_click
    send_click()
    dig_tool_instance.click_count += 1


def save_debug_screenshot_wrapper(
    dig_tool_instance,
    screenshot,
    line_pos,
    sweet_spot_start,
    sweet_spot_end,
    zone_y2_cached,
    velocity,
    acceleration,
    prediction_used=False,
    confidence=0.0,
):
    if not get_param(dig_tool_instance, "debug_clicks_enabled"):
        return
    ensure_debug_directory(dig_tool_instance.debug_dir)
    filename = save_debug_screenshot(
        screenshot,
        line_pos,
        sweet_spot_start,
        sweet_spot_end,
        zone_y2_cached,
        velocity,
        acceleration,
        prediction_used,
        confidence,
        dig_tool_instance.click_count,
        dig_tool_instance.debug_dir,
        dig_tool_instance.smoothed_zone_x,
        dig_tool_instance.smoothed_zone_w,
    )
    if filename:
        log_click_debug(
            dig_tool_instance.click_count + 1,
            line_pos,
            velocity,
            acceleration,
            sweet_spot_start,
            sweet_spot_end,
            prediction_used,
            confidence,
            filename,
            dig_tool_instance.debug_log_path,
        )


def apply_keybinds(instance):
    logger.info("Applying keybinds...")
    
    time.sleep(0.1)
    
    try:
        keyboard.unhook_all()
        logger.debug("Previous hotkeys unhooked")
    except Exception as e:
        logger.warning(f"Warning: Could not unhook previous hotkeys: {e}")
    
    if not instance.keybind_vars:
        logger.error("Error: Keybind variables not initialized")
        instance.update_status("Error: Keybind variables not initialized")
        return False
    
    try:
        keybinds_applied = 0
        
        for key_name, var in instance.keybind_vars.items():
            key_value = var.get()
            if not key_value:
                logger.warning(f"Warning: Empty keybind for {key_name}")
                continue
            
            is_valid, msg = validate_keybind(key_name, key_value)
            if not is_valid:
                logger.error(
                    f"Error: Invalid keybind for {key_name}: {key_value} - {msg}"
                )
                continue
            
            logger.debug(f"  Applying {key_name}: {key_value}")
            
            if key_name == "toggle_bot":
                keyboard.add_hotkey(key_value, instance.toggle_detection)
            elif key_name == "toggle_gui":
                keyboard.add_hotkey(key_value, lambda: toggle_gui(instance))
            elif key_name == "toggle_overlay":
                keyboard.add_hotkey(key_value, lambda: toggle_overlay(instance))
            elif key_name == "toggle_autowalk_overlay":
                keyboard.add_hotkey(key_value, lambda: toggle_autowalk_overlay(instance))
            else:
                logger.warning(f"Warning: Unknown keybind {key_name}")
                continue
            
            keybinds_applied += 1
        
        from utils.ui_management import update_main_button_text
        update_main_button_text(instance)
        success_msg = f"Successfully applied {keybinds_applied} keybinds"
        instance.update_status(success_msg)
        logger.info(success_msg)
        
        instance.root.after_idle(
            lambda: instance.settings_manager.auto_save_setting("keybinds")
        )
        
        return True
        
    except Exception as e:
        error_msg = f"Error applying keybinds: {e}"
        instance.update_status(error_msg)
        logger.error(error_msg)
        from utils.ui_management import update_main_button_text
        update_main_button_text(instance)
        return False


def run_hotkey_listener(instance):
    logger.info("Hotkey listener thread started")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            instance.root.after(0, lambda: apply_keybinds(instance))
            logger.debug(f"Keybind application scheduled (attempt {attempt + 1})")
            break
        except Exception as e:
            logger.error(
                f"Failed to schedule keybind application (attempt {attempt + 1}): {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(1)
    
    while instance.preview_active:
        time.sleep(0.5)


def start_area_selection(dig_tool_instance):
    dig_tool_instance.root.iconify()
    dig_tool_instance.selection_overlay = tk.Toplevel()
    dig_tool_instance.selection_overlay.attributes(
        "-fullscreen", True, "-alpha", 0.3, "-topmost", True
    )
    dig_tool_instance.selection_overlay.configure(bg="#1a1a1a", cursor="crosshair")
    
    dig_tool_instance.selection_rect = tk.Frame(
        dig_tool_instance.selection_overlay,
        highlightthickness=2,
        highlightbackground="#00ff88",
        highlightcolor="#00ff88",
        bd=0,
        relief="solid"
    )
    dig_tool_instance.selection_rect.configure(highlightthickness=2)
    
    dig_tool_instance.selection_overlay.bind("<Button-1>", lambda e: on_drag_start(dig_tool_instance, e))
    dig_tool_instance.selection_overlay.bind("<B1-Motion>", lambda e: on_drag_motion(dig_tool_instance, e))
    dig_tool_instance.selection_overlay.bind("<ButtonRelease-1>", lambda e: on_drag_end(dig_tool_instance, e))


def on_drag_start(dig_tool_instance, event):
    dig_tool_instance.drag_start = (event.x_root, event.y_root)
    dig_tool_instance.selection_rect.place(x=event.x, y=event.y, width=1, height=1)


def on_drag_motion(dig_tool_instance, event):
    x1, y1 = dig_tool_instance.drag_start
    x2, y2 = event.x_root, event.y_root
    x, y = (
        dig_tool_instance.selection_overlay.winfo_rootx(),
        dig_tool_instance.selection_overlay.winfo_rooty(),
    )
    
    dig_tool_instance.selection_rect.place(
        x=min(x1, x2) - x,
        y=min(y1, y2) - y,
        width=abs(x1 - x2),
        height=abs(y1 - y2),
    )


def on_drag_end(dig_tool_instance, event):
    x1, y1 = dig_tool_instance.drag_start
    x2, y2 = event.x_root, event.y_root
    dig_tool_instance.game_area = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    dig_tool_instance.selection_overlay.destroy()
    dig_tool_instance.root.deiconify()
    dig_tool_instance.update_status("Game area set. Press Start to begin.")
    dig_tool_instance.preview_btn.config(state=tk.NORMAL)
    dig_tool_instance.debug_btn.config(state=tk.NORMAL)
    
    if hasattr(dig_tool_instance, 'main_window') and dig_tool_instance.main_window:
        dig_tool_instance.main_window.update_status_with_area_indicator()
    else:
        dig_tool_instance.update_status("Game area set. Press Start to begin.")
    
    dig_tool_instance.start_threads()

    dig_tool_instance.root.after_idle(
        lambda: dig_tool_instance.settings_manager.auto_save_setting("coordinates")
    )


def start_sell_button_selection(dig_tool_instance):
    dig_tool_instance.root.iconify()
    dig_tool_instance.sell_selection_overlay = tk.Toplevel()
    dig_tool_instance.sell_selection_overlay.attributes(
        "-fullscreen", True, "-alpha", 0.3, "-topmost", True
    )
    dig_tool_instance.sell_selection_overlay.configure(bg="#1a1a1a", cursor="crosshair")

    dig_tool_instance.sell_selection_overlay.bind("<Button-1>", lambda e: on_sell_button_click(dig_tool_instance, e))


def on_sell_button_click(dig_tool_instance, event):
    dig_tool_instance.automation_manager.sell_button_position = (event.x_root, event.y_root)
    dig_tool_instance.sell_selection_overlay.destroy()
    dig_tool_instance.root.deiconify()
    dig_tool_instance.update_status(f"Sell button set at ({event.x_root}, {event.y_root})")
    
    from utils.ui_management import update_sell_info
    update_sell_info(dig_tool_instance)
    dig_tool_instance.root.after_idle(
        lambda: dig_tool_instance.settings_manager.auto_save_setting("coordinates")
    )


def start_cursor_position_selection(dig_tool_instance):
    dig_tool_instance.root.iconify()
    dig_tool_instance.cursor_selection_overlay = tk.Toplevel()
    dig_tool_instance.cursor_selection_overlay.attributes(
        "-fullscreen", True, "-alpha", 0.3, "-topmost", True
    )
    dig_tool_instance.cursor_selection_overlay.configure(bg="#1a1a1a", cursor="crosshair")

    dig_tool_instance.cursor_selection_overlay.bind("<Button-1>", lambda e: on_cursor_position_click(dig_tool_instance, e))


def on_cursor_position_click(dig_tool_instance, event):
    dig_tool_instance.cursor_position = (event.x_root, event.y_root)
    dig_tool_instance.cursor_selection_overlay.destroy()
    dig_tool_instance.root.deiconify()
    dig_tool_instance.update_status(f"Cursor position set at ({event.x_root}, {event.y_root})")
    
    from utils.ui_management import update_cursor_info
    update_cursor_info(dig_tool_instance)

    dig_tool_instance.root.after_idle(
        lambda: dig_tool_instance.settings_manager.auto_save_setting("coordinates")
    )


def toggle_overlay(dig_tool_instance):
    if not dig_tool_instance.root.winfo_exists():
        return
    dig_tool_instance.root.after_idle(lambda: _toggle_overlay_thread_safe(dig_tool_instance))


def _toggle_overlay_thread_safe(dig_tool_instance):
    try:
        if not dig_tool_instance.overlay_enabled:
            if not dig_tool_instance.game_area:
                dig_tool_instance.update_status("Select game area first")
                return
            dig_tool_instance.overlay = GameOverlay(dig_tool_instance)
            dig_tool_instance.overlay.create_overlay()
            dig_tool_instance.overlay_enabled = True
            logger.debug("Overlay enabled")
        else:
            if dig_tool_instance.overlay:
                dig_tool_instance.overlay.destroy_overlay()
            dig_tool_instance.overlay = None
            dig_tool_instance.overlay_enabled = False
            logger.debug("Overlay disabled")
        
        from utils.ui_management import update_main_button_text
        update_main_button_text(dig_tool_instance)
    except Exception as e:
        logger.error(f"Error toggling overlay: {e}")
        dig_tool_instance.overlay_enabled = False
        dig_tool_instance.overlay = None


def toggle_autowalk_overlay(dig_tool_instance):
    dig_tool_instance.root.after_idle(lambda: _toggle_autowalk_overlay_thread_safe(dig_tool_instance))


def _toggle_autowalk_overlay_thread_safe(dig_tool_instance):
    try:
        if not dig_tool_instance.autowalk_overlay_enabled:
            if not get_param(dig_tool_instance, "auto_walk_enabled"):
                dig_tool_instance.update_status(
                    "Auto Walk overlay requires Auto Walk to be enabled"
                )
                return

            dig_tool_instance.autowalk_overlay = AutoWalkOverlay(dig_tool_instance)
            dig_tool_instance.autowalk_overlay.create_overlay()
            dig_tool_instance.autowalk_overlay_enabled = True
            logger.debug("Auto Walk overlay enabled")
        else:
            if dig_tool_instance.autowalk_overlay:
                dig_tool_instance.autowalk_overlay.destroy_overlay()
            dig_tool_instance.autowalk_overlay = None
            dig_tool_instance.autowalk_overlay_enabled = False
            logger.debug("Auto Walk overlay disabled")
    except Exception as e:
        logger.error(f"Error toggling auto walk overlay: {e}")


def toggle_color_modules_overlay(dig_tool_instance):
    dig_tool_instance.root.after_idle(lambda: _toggle_color_modules_overlay_thread_safe(dig_tool_instance))


def _toggle_color_modules_overlay_thread_safe(dig_tool_instance):
    try:
        if not dig_tool_instance.color_modules_overlay_enabled:
            from interface.components import ColorModulesOverlay
            dig_tool_instance.color_modules_overlay = ColorModulesOverlay(dig_tool_instance)
            dig_tool_instance.color_modules_overlay.create_overlay()
            dig_tool_instance.color_modules_overlay_enabled = True
            logger.debug("Color modules overlay enabled")
        else:
            if dig_tool_instance.color_modules_overlay:
                dig_tool_instance.color_modules_overlay.destroy_overlay()
            dig_tool_instance.color_modules_overlay = None
            dig_tool_instance.color_modules_overlay_enabled = False
            logger.debug("Color modules overlay disabled")
    except Exception as e:
        logger.error(f"Error toggling color modules overlay: {e}")


def toggle_gui(dig_tool_instance):
    dig_tool_instance.root.after(0, lambda: _toggle_gui_thread_safe(dig_tool_instance))


def _toggle_gui_thread_safe(dig_tool_instance):
    if dig_tool_instance.root.winfo_exists():
        if dig_tool_instance.root.state() == "normal":
            dig_tool_instance.root.withdraw()
        else:
            dig_tool_instance.root.deiconify()
            dig_tool_instance.root.lift()
