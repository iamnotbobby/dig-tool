import tkinter as tk
from tkinter import Label, Frame, messagebox, ttk
import cv2
import os


def update_area_info(dig_tool_instance):
    if not hasattr(dig_tool_instance, "area_info_label"):
        return
    if dig_tool_instance.game_area:
        x1, y1, x2, y2 = dig_tool_instance.game_area
        width, height = x2 - x1, y2 - y1
        area_text = f"Game Area: {width}x{height} at ({x1}, {y1})"
    else:
        area_text = "Game Area: Not set"
    dig_tool_instance.area_info_label.config(text=area_text)


def update_sell_info(dig_tool_instance):
    if not hasattr(dig_tool_instance, "sell_info_label"):
        return
    if dig_tool_instance.automation_manager.sell_button_position:
        x, y = dig_tool_instance.automation_manager.sell_button_position
        sell_text = f"Sell Button: Set at ({x}, {y})"
    else:
        sell_text = "Sell Button: Not set"
    dig_tool_instance.sell_info_label.config(text=sell_text)


def update_cursor_info(dig_tool_instance):
    if not hasattr(dig_tool_instance, "cursor_info_label"):
        return
    if hasattr(dig_tool_instance, "cursor_position") and dig_tool_instance.cursor_position:
        x, y = dig_tool_instance.cursor_position
        cursor_text = f"Cursor Position: Set at ({x}, {y})"
    else:
        cursor_text = "Cursor Position: Not set"
    dig_tool_instance.cursor_info_label.config(text=cursor_text)


def test_sell_button_click(dig_tool_instance):
    dig_tool_instance.automation_manager.test_sell_button_click()


def show_settings_info(dig_tool_instance):
    success = dig_tool_instance.settings_manager.open_settings_directory()
    if not success:
        settings_info = dig_tool_instance.settings_manager.get_settings_info()
        messagebox.showerror(
            "Error",
            f"Could not open settings directory:\n{settings_info['settings_directory']}",
        )


def show_debug_console(dig_tool_instance):
    from utils.debug_logger import logger
    logger.show_console()


def create_preview_window(dig_tool_instance):
    dig_tool_instance.preview_window = tk.Toplevel(dig_tool_instance.root)
    dig_tool_instance.preview_window.title("Preview")
    
    preview_width = int(dig_tool_instance.width * 1.8)
    preview_height = int(dig_tool_instance.base_height * 0.42)
    dig_tool_instance.preview_window.geometry(f"{preview_width}x{preview_height}")
    dig_tool_instance.preview_window.configure(bg="black")

    try:
        if os.path.exists("assets/icon.ico"):
            dig_tool_instance.preview_window.wm_iconbitmap("assets/icon.ico")
    except:
        pass

    dig_tool_instance.preview_label = Label(dig_tool_instance.preview_window, bg="black")
    dig_tool_instance.preview_label.pack(fill=tk.BOTH, expand=True)

    velocity_frame = Frame(dig_tool_instance.preview_window, bg="black", pady=5)
    dig_tool_instance.velocity_info_label = Label(
        velocity_frame,
        text="Velocity: -- px/s | Acceleration: -- px/s²",
        font=("Segoe UI", 9),
        bg="black",
        fg="white",
        anchor="center",
    )
    dig_tool_instance.velocity_info_label.pack(expand=True)
    velocity_frame.pack(fill="x")

    dig_tool_instance.preview_window.protocol("WM_DELETE_WINDOW", lambda: toggle_preview_window(dig_tool_instance))
    toggle_preview_on_top(dig_tool_instance)


def toggle_preview_window(dig_tool_instance):
    if dig_tool_instance.preview_window is None:
        create_preview_window(dig_tool_instance)
    else:
        dig_tool_instance.preview_window.destroy()
        dig_tool_instance.preview_window = None
        dig_tool_instance.preview_label = None
        dig_tool_instance.velocity_info_label = None


def toggle_preview_on_top(dig_tool_instance):
    if dig_tool_instance.preview_window:
        dig_tool_instance.preview_window.attributes(
            "-topmost", dig_tool_instance.param_vars["preview_on_top"].get()
        )


def create_debug_window(dig_tool_instance):
    dig_tool_instance.debug_window = tk.Toplevel(dig_tool_instance.root)
    dig_tool_instance.debug_window.title("Debug Mask & Detection Info")
    
    debug_width = int(dig_tool_instance.width * 1.8)
    debug_height = int(dig_tool_instance.base_height * 0.53)
    dig_tool_instance.debug_window.geometry(f"{debug_width}x{debug_height}")
    dig_tool_instance.debug_window.configure(bg="black")

    try:
        if os.path.exists("assets/icon.ico"):
            dig_tool_instance.debug_window.wm_iconbitmap("assets/icon.ico")
    except:
        pass

    dig_tool_instance.debug_label = Label(dig_tool_instance.debug_window, bg="black")
    dig_tool_instance.debug_label.pack(fill=tk.BOTH, expand=True)

    color_frame = Frame(dig_tool_instance.debug_window, bg="black", pady=5)
    Label(
        color_frame,
        text="Locked Color:",
        font=("Segoe UI", 9),
        bg="black",
        fg="white",
    ).pack(side="left", padx=5)
    dig_tool_instance.color_swatch_label = Label(
        color_frame, text="", bg="black", relief="solid", bd=1, width=15
    )
    dig_tool_instance.color_swatch_label.pack(side="left", ipady=5, padx=5)
    color_frame.pack(fill="x")

    detection_frame = Frame(dig_tool_instance.debug_window, bg="black", pady=5)
    Label(
        detection_frame,
        text="Detection Method:",
        font=("Segoe UI", 9, "bold"),
        bg="black",
        fg="white",
    ).pack(anchor="w", padx=5)
    dig_tool_instance.detection_info_label = Label(
        detection_frame,
        text="Method: Unknown",
        font=("Segoe UI", 8),
        bg="black",
        fg="lightgray",
        justify="left",
    )
    dig_tool_instance.detection_info_label.pack(anchor="w", padx=10)
    detection_frame.pack(fill="x")

    dig_tool_instance.debug_window.protocol("WM_DELETE_WINDOW", lambda: toggle_debug_window(dig_tool_instance))
    toggle_debug_on_top(dig_tool_instance)


def toggle_debug_window(dig_tool_instance):
    if dig_tool_instance.debug_window is None:
        create_debug_window(dig_tool_instance)
    else:
        dig_tool_instance.debug_window.destroy()
        dig_tool_instance.debug_window = None
        dig_tool_instance.debug_label = None
        dig_tool_instance.color_swatch_label = None
        dig_tool_instance.detection_info_label = None


def toggle_debug_on_top(dig_tool_instance):
    if dig_tool_instance.debug_window:
        dig_tool_instance.debug_window.attributes(
            "-topmost", dig_tool_instance.param_vars["debug_on_top"].get()
        )


def toggle_main_on_top(dig_tool_instance, *args):
    dig_tool_instance.root.attributes("-topmost", dig_tool_instance.param_vars["main_on_top"].get())


def resize_for_content(dig_tool_instance):
    try:
        dig_tool_instance.root.update_idletasks()
        
        required_height = dig_tool_instance.controls_panel.winfo_reqheight()
      
        base_height = dig_tool_instance.base_height
        content_height = required_height + 80  
        
    
        if content_height > base_height + 100:  
            target_height = min(content_height, base_height + 200) 
        else:
            target_height = max(base_height, content_height)
        
      
        screen_height = dig_tool_instance.root.winfo_screenheight()
        max_height = int(screen_height * 0.85)
        target_height = min(target_height, max_height)
        
   
        dig_tool_instance.root.geometry(f"{dig_tool_instance.width}x{target_height}")
        dig_tool_instance.root.update_idletasks()
        
    except Exception as e:
    
        dig_tool_instance.root.geometry(f"{dig_tool_instance.width}x{dig_tool_instance.base_height}")
        dig_tool_instance.root.update_idletasks()


def setup_dropdown_resize_handling(dig_tool_instance):
    def on_dropdown_open(event):
        dig_tool_instance.root.after(10, lambda: resize_for_content(dig_tool_instance))
    
    def on_dropdown_close(event):

        dig_tool_instance.root.after(10, lambda: resize_for_content(dig_tool_instance))
    
   
    def bind_combobox_events(widget):
        if isinstance(widget, ttk.Combobox):
            widget.bind('<Button-1>', on_dropdown_open)
            widget.bind('<FocusOut>', on_dropdown_close)
            widget.bind('<Return>', on_dropdown_close)
            widget.bind('<Escape>', on_dropdown_close)
        
   
        try:
            for child in widget.winfo_children():
                bind_combobox_events(child)
        except:
            pass
    
   
    try:
        bind_combobox_events(dig_tool_instance.root)
    except:
        pass


def update_main_button_text(dig_tool_instance):
    if not dig_tool_instance.root.winfo_exists():
        return
    try:
        current_state = "Stop" if dig_tool_instance.running else "Start"
        dig_tool_instance.start_stop_btn.config(
            text=f"{current_state} ({dig_tool_instance.keybind_vars['toggle_bot'].get().upper()})"
        )
        dig_tool_instance.toggle_gui_btn.config(
            text=f"Show/Hide ({dig_tool_instance.keybind_vars['toggle_gui'].get().upper()})"
        )
        overlay_status = "ON" if dig_tool_instance.overlay_enabled else "OFF"
        dig_tool_instance.overlay_btn.config(
            text=f"Overlay: {overlay_status} ({dig_tool_instance.keybind_vars['toggle_overlay'].get().upper()})"
        )
    except (tk.TclError, AttributeError):
        pass



def save_debug_screenshot(dig_tool_instance):

    from utils.debug_logger import logger
    from utils.screen_capture import capture_region
    import numpy as np

    if not dig_tool_instance.game_area:
        logger.log("No game area set, cannot take debug screenshot")
        return

    screenshot = capture_region(dig_tool_instance.game_area)
    if screenshot is None:
        logger.log("Failed to capture game area")
        return

    screenshot_cv = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2HSV)

    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    if dig_tool_instance.automation_manager.locked_color:
        lower_bound, upper_bound = dig_tool_instance.automation_manager.hsv_bounds
        mask = cv2.inRange(hsv, lower_bound, upper_bound)

    overlay = screenshot_cv.copy()
    overlay[mask > 0] = [0, 255, 0]
    result = cv2.addWeighted(screenshot_cv, 0.7, overlay, 0.3, 0)

    if dig_tool_instance.game_area:
        x1, y1, x2, y2 = dig_tool_instance.game_area
        detect_x1 = int((x2 - x1) * 0.15)
        detect_y1 = int((y2 - y1) * 0.15)
        detect_x2 = int((x2 - x1) * 0.85)
        detect_y2 = int((y2 - y1) * 0.85)
        cv2.rectangle(result, (detect_x1, detect_y1), (detect_x2, detect_y2), (255, 0, 0), 2)

    import time
    timestamp = int(time.time())
    filename = f"debug_screenshot_{timestamp}.png"
    cv2.imwrite(filename, result)
    logger.log(f"Debug screenshot saved as {filename}")


def update_automation_info(dig_tool_instance):
    update_area_info(dig_tool_instance)
    update_sell_info(dig_tool_instance)
    update_cursor_info(dig_tool_instance)


def update_gui_from_queue(instance):
    import cv2
    import numpy as np
    import queue
    from tkinter import TclError
    from PIL import Image, ImageTk
    
    try:
        preview_array, debug_mask, overlay_info = instance.results_queue.get_nowait()
        
        if instance.preview_window and instance.preview_label:
            pw, ph = (
                instance.preview_label.winfo_width(),
                instance.preview_label.winfo_height(),
            )
            if pw > 20 and ph > 20:
                img = Image.fromarray(
                    cv2.cvtColor(preview_array, cv2.COLOR_BGR2RGB)
                )
                img.thumbnail((pw, ph), Image.Resampling.NEAREST)
                photo = ImageTk.PhotoImage(image=img)
                instance.preview_label.configure(image=photo)
                instance.preview_label.image = photo

            if hasattr(instance, "velocity_info_label") and instance.velocity_info_label:
                velocity = overlay_info.get("velocity", 0)
                acceleration = overlay_info.get("acceleration", 0)
                line_detected = overlay_info.get("line_detected", False)

                velocity_text = f"Velocity: {velocity:.1f} px/s | Acceleration: {acceleration:.1f} px/s²"
                if not line_detected:
                    velocity_text += " | Line: NOT DETECTED"
                else:
                    velocity_text += " | Line: DETECTED"

                instance.velocity_info_label.config(text=velocity_text)
        
        if instance.debug_window and instance.debug_label and debug_mask is not None:
            dw, dh = instance.debug_label.winfo_width(), instance.debug_label.winfo_height()
            if dw > 20 and dh > 20:
                debug_bgr = cv2.cvtColor(debug_mask, cv2.COLOR_GRAY2BGR)
                debug_img = Image.fromarray(
                    cv2.cvtColor(debug_bgr, cv2.COLOR_BGR2RGB)
                )
                debug_img.thumbnail((dw, dh), Image.Resampling.NEAREST)
                debug_photo = ImageTk.PhotoImage(image=debug_img)
                instance.debug_label.configure(image=debug_photo)
                instance.debug_label.image = debug_photo
        
        locked_color = overlay_info.get("locked_color_hex")
        if instance.color_swatch_label:
            instance.color_swatch_label.config(
                bg=locked_color if locked_color else "#000000"
            )

        if instance.detection_info_label and overlay_info.get("detection_info"):
            detection_info = overlay_info["detection_info"]
            method = detection_info.get("method", "Unknown")
            threshold = detection_info.get("threshold", "N/A")

            info_text = f"Method: {method}\nThreshold: {threshold}"

            if "Otsu" in method:
                if "min_area" in detection_info:
                    info_text += f"\nMin Area: {detection_info['min_area']} px"
                if "max_area" in detection_info:
                    info_text += f"\nMax Area: {detection_info['max_area']}"
                if "area_percentile" in detection_info:
                    info_text += f"\nArea %: {detection_info['area_percentile']}"
                if "morph_kernel" in detection_info:
                    info_text += f"\nMorph Kernel: {detection_info['morph_kernel']}"
            elif "Color Picker" in method:
                if "target_color" in detection_info:
                    info_text += f"\nTarget Color: {detection_info['target_color']}"
                if "tolerance" in detection_info:
                    info_text += f"\nTolerance: {detection_info['tolerance']}"
                if "target_hsv" in detection_info:
                    info_text += f"\nTarget HSV: {detection_info['target_hsv']}"

            instance.detection_info_label.config(text=info_text)

        if instance.overlay_enabled and instance.overlay:
            instance.overlay.update_info(**overlay_info)
        if instance.autowalk_overlay_enabled and instance.autowalk_overlay:
            instance.autowalk_overlay.update_info(**overlay_info)
        if instance.color_modules_overlay_enabled and instance.color_modules_overlay:
            instance.color_modules_overlay.update_info(**overlay_info)
            
    except (queue.Empty, RuntimeError, TclError):
        pass
    finally:
        if instance.preview_active:
            instance.root.after(50, lambda: update_gui_from_queue(instance))
