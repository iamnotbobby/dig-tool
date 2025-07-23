import json
import tkinter as tk
from tkinter import Label, Button, Frame, Checkbutton, ttk
try:
    from tkinterdnd2 import DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    DND_FILES = None
from interface.components import CollapsiblePane, AccordionManager, Tooltip
from utils.debug_logger import logger
from utils.pattern_utils import (
    open_custom_pattern_manager,
    on_walk_pattern_changed,
)
from utils.input_management import (
    apply_keybinds,
)
from utils.ui_management import (
    test_sell_button_click,
    show_settings_info,
    show_debug_console,
    toggle_preview_window,
    toggle_debug_window,
    toggle_main_on_top,
    toggle_preview_on_top,
    toggle_debug_on_top,
)
from utils.input_management import (
    start_area_selection,
    start_sell_button_selection,
    start_cursor_position_selection,
    toggle_gui,
    toggle_overlay,
    toggle_autowalk_overlay,
    toggle_color_modules_overlay,
)
import os
from core.notifications import test_discord_ping
from utils.input_management import select_money_area, test_money_ocr, select_item_area, test_item_ocr


class DisabledTooltip:
    def __init__(self, widget, disabled_text, original_tooltip=None):
        self.widget = widget
        self.disabled_text = disabled_text
        self.original_tooltip = original_tooltip
        self.tooltip_window = None
        self.is_disabled = False
        self.widget_type = None

        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<Motion>", self.on_motion)

    def set_disabled(self, disabled, reason=None):
        self.is_disabled = disabled
        if reason: self.disabled_text = reason

    def on_motion(self, event=None):
        if self.tooltip_window: self.update_position()

    def show_tooltip(self, event=None):
        if self.tooltip_window: return
        if self.is_disabled and str(self.widget.cget('state')) == 'disabled':
            text = self.disabled_text
        elif self.original_tooltip:
            text = self.original_tooltip
        else:
            return
        self.create_tooltip(text)

    def create_tooltip(self, text):
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes('-topmost', True)
        bg_color = "#ffcccc" if self.is_disabled and str(
            self.widget.cget('state')) == 'disabled' else "#ffffe0"  # Light red for disabled, light yellow for normal
        label = tk.Label(self.tooltip_window, text=text, justify='left', background=bg_color, relief='solid',
                         borderwidth=1, font=("Segoe UI", 9, "normal"), wraplength=300, padx=8, pady=6)
        label.pack()
        self.update_position()

    def update_position(self):
        if not self.tooltip_window: return
        try:
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 25
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except tk.TclError:
                pass
            self.tooltip_window = None


class StatusTooltip:
    def __init__(self, widget, not_set_text, set_text, status_check_func):
        self.widget = widget
        self.not_set_text = not_set_text
        self.set_text = set_text
        self.status_check_func = status_check_func
        self.tooltip_window = None

        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<Motion>", self.on_motion)

    def on_motion(self, event=None):
        if self.tooltip_window: self.update_position()

    def show_tooltip(self, event=None):
        if self.tooltip_window: return
        is_set = self.status_check_func()
        text = self.set_text if is_set else self.not_set_text
        self.create_tooltip(text, is_set)

    def create_tooltip(self, text, is_set):
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes('-topmost', True)
        bg_color = "#ffffe0"
        label = tk.Label(self.tooltip_window, text=text, justify='left', background=bg_color, relief='solid',
                         borderwidth=1, font=("Segoe UI", 9, "normal"), wraplength=300, padx=8, pady=6)
        label.pack()
        self.update_position()

    def update_position(self):
        if not self.tooltip_window: return
        try:
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 25
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except tk.TclError:
                pass
            self.tooltip_window = None


class CollapsibleSubsection:
    def __init__(self, parent, title, bg_color="#f0f0f0"):  # Light gray default background
        self.parent = parent
        self.title = title
        self.bg_color = bg_color
        self.is_open = tk.BooleanVar(value=False)

        self.container = Frame(parent, bg=parent.cget('bg'))
        self.container.pack(fill='x', pady=(1, 0), padx=4)  

        self.header = Frame(self.container, bg=bg_color, relief='raised', bd=1)
        self.header.pack(fill='x')

        self.toggle_btn = Button(self.header, text=f"▶ {title}", font=("Segoe UI", 8, 'bold'),
                                 bg=bg_color, fg="#333333", relief='flat', anchor='w',  # Dark gray text
                                 command=self.toggle, pady=0, padx=4)  
        self.toggle_btn.pack(fill='x')

        self.content = Frame(self.container, bg=bg_color, relief='sunken', bd=1)

    def toggle(self):
        if self.is_open.get():
            self.content.pack_forget()
            self.toggle_btn.config(text=f"▶ {self.title}")
            self.is_open.set(False)
        else:
            self.content.pack(fill='x', pady=(0, 1))
            self.toggle_btn.config(text=f"▼ {self.title}")
            self.is_open.set(True)


class MainWindow:
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance
        self.walk_pattern_combo = None
        self.auto_shovel_checkbox = None
        self.auto_sell_checkbox = None
        self.use_cursor_checkbox = None
        self._prev_auto_walk_enabled = False  # Track previous auto walk state for key cleanup
        self.shovel_dependent_widgets = []
        self.sell_dependent_widgets = []
        self.cursor_dependent_widgets = []
        self.velocity_dependent_widgets = []
        self.otsu_dependent_widgets = []
        self.color_picker_dependent_widgets = []
        self.engagement_timeout_dependent_widgets = []
        self.money_detection_dependent_widgets = []
        self.item_detection_dependent_widgets = []
        self.walkspeed_dependent_widgets = []
        self.money_test_button = None
        self.item_test_button = None
        self.disabled_tooltips = []
        self.status_tooltips = []

    def validate_on_focus_out(self, var_key, value):
        if value == "" or (hasattr(value, 'strip') and value.strip() == ""):
            self.dig_tool.root.after_idle(lambda: self._restore_default_value(var_key))
            return False
        
        try:
            if not self.dig_tool.settings_manager.validate_param_value(var_key, value):
                self.dig_tool.root.after_idle(lambda: self._restore_default_value(var_key))
                return False
            else:
                self.dig_tool.root.after_idle(lambda: self._save_param_value(var_key, value))
        except:
            self.dig_tool.root.after_idle(lambda: self._restore_default_value(var_key))
            return False
        
        return True
    
    def _save_param_value(self, var_key, value):
        try:
            if hasattr(self.dig_tool.settings_manager, 'save_param_value'):
                self.dig_tool.settings_manager.save_param_value(var_key, value)
            elif hasattr(self.dig_tool.settings_manager, 'save_settings'):
                self.dig_tool.settings_manager.save_settings()
        except:
            pass
    
    def _restore_default_value(self, var_key):
        try:
            default_value = self.dig_tool.settings_manager.get_default_value(var_key)
            if var_key in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key].set(default_value)
        except:
            pass

    def validate_cursor_position_toggle(self, *args):
        if not hasattr(self.dig_tool, 'cursor_position') or not self.dig_tool.cursor_position:
            if self.dig_tool.param_vars['use_custom_cursor'].get():
                self.dig_tool.param_vars['use_custom_cursor'].set(False)
                self.dig_tool.update_status("Error: Set cursor position first before enabling custom cursor!")

    def validate_velocity_toggle(self, *args):
        self.dig_tool.root.after_idle(self.update_dependent_widgets_state)

    def validate_otsu_toggle(self, *args):
        if self.dig_tool.param_vars['use_otsu_detection'].get():
            self.dig_tool.param_vars['use_color_picker_detection'].set(False)
        self.dig_tool.root.after_idle(self.update_dependent_widgets_state)

    def validate_color_picker_toggle(self, *args):
        if self.dig_tool.param_vars['use_color_picker_detection'].get():
            self.dig_tool.param_vars['use_otsu_detection'].set(False)
        self.dig_tool.root.after_idle(self.update_dependent_widgets_state)

    def validate_money_detection_toggle(self, *args):
        if self.dig_tool.param_vars['enable_money_detection'].get():
            if not self.is_money_area_set():
                self.dig_tool.param_vars['enable_money_detection'].set(False)
                self.dig_tool.update_status("Error: Set money area first before enabling money detection!")
                return
        self.dig_tool.root.after_idle(self.update_dependent_widgets_state)

    def validate_item_detection_toggle(self, *args):
        if self.dig_tool.param_vars['enable_item_detection'].get():
            if not self.is_item_area_set():
                self.dig_tool.param_vars['enable_item_detection'].set(False)
                self.dig_tool.update_status("Error: Set item area first before enabling item detection!")
                return
        self.dig_tool.root.after_idle(self.update_dependent_widgets_state)

    def validate_auto_sell_toggle(self, *args):
        if hasattr(self, '_validating_auto_sell') and self._validating_auto_sell:
            return
        
        if self.dig_tool.param_vars['auto_sell_enabled'].get():
            if not self.dig_tool.automation_manager.sell_button_position:
                self.dig_tool.param_vars['auto_sell_enabled'].set(False)
                self.dig_tool.update_status("Error: Set sell button first before enabling auto-sell!")
                return

            auto_walk_enabled = self.dig_tool.param_vars.get('auto_walk_enabled', tk.BooleanVar()).get()
            if not auto_walk_enabled:
                self._validating_auto_sell = True
                try:
                    import tkinter.messagebox as messagebox
                    result = messagebox.askyesno(
                        "Auto-Sell Warning",
                        "Enabling auto-sell without the usage of auto-walk MAY cause problems!\n\n"
                        "Only enable this if you are automating Dig Tool through another way or will not interfere with the auto-sell process.\n\n"
                        "Are you sure you want to enable auto-sell?",
                        icon='warning'
                    )
                    if not result:
                        self.dig_tool.root.after_idle(lambda: self.dig_tool.param_vars['auto_sell_enabled'].set(False))
                        return
                finally:
                    self._validating_auto_sell = False

    def is_sell_button_set(self):
        return self.dig_tool.automation_manager.sell_button_position is not None

    def is_cursor_position_set(self):
        return hasattr(self.dig_tool, 'cursor_position') and self.dig_tool.cursor_position is not None

    def is_money_area_set(self):
        return hasattr(self.dig_tool, 'money_ocr') and self.dig_tool.money_ocr.money_area is not None

    def is_item_area_set(self):
        return hasattr(self.dig_tool, 'item_ocr') and self.dig_tool.item_ocr.item_area is not None

    def pick_color_from_screen(self):
        import time
        import pyautogui
        import numpy as np
        from core.detection import rgb_to_hsv_single
        
        self.dig_tool.root.iconify()
        
        try:
            overlay = tk.Toplevel()
            overlay.attributes('-topmost', True)
            overlay.attributes('-alpha', 0.3)
            overlay.configure(bg='#1a1a1a', cursor='crosshair')
            overlay.overrideredirect(True)
            overlay.geometry(f"{overlay.winfo_screenwidth()}x{overlay.winfo_screenheight()}+0+0")
            
            start_pos = None
            selection_rect = None
            is_dragging = False
            picked_color = None
            
            def on_button_press(event):
                nonlocal start_pos, selection_rect, is_dragging
                start_pos = (event.x_root, event.y_root)
                is_dragging = True
                
                if selection_rect:
                    selection_rect.destroy()
                selection_rect = tk.Frame(overlay, highlightthickness=2, highlightbackground='#ff9500', highlightcolor='#ff9500', relief='solid', bd=0)
                selection_rect.configure(highlightthickness=2)
                selection_rect.place(x=event.x, y=event.y, width=1, height=1)
            
            def on_motion(event):
                nonlocal start_pos, selection_rect, is_dragging
                if not is_dragging or not start_pos or not selection_rect:
                    return
                
                x1, y1 = start_pos
                x2, y2 = event.x_root, event.y_root
                
                overlay_x = overlay.winfo_rootx()
                overlay_y = overlay.winfo_rooty()
                
                rect_x = min(x1, x2) - overlay_x
                rect_y = min(y1, y2) - overlay_y
                rect_w = abs(x2 - x1)
                rect_h = abs(y2 - y1)
                
                selection_rect.place(x=rect_x, y=rect_y, width=rect_w, height=rect_h)
            
            def on_button_release(event):
                nonlocal start_pos, selection_rect, is_dragging, picked_color
                if not is_dragging or not start_pos:
                    return
                
                is_dragging = False
                
                x1, y1 = start_pos
                x2, y2 = event.x_root, event.y_root
                
                min_x, max_x = min(x1, x2), max(x1, x2)
                min_y, max_y = min(y1, y2), max(y1, y2)
                
                area_width = max_x - min_x
                area_height = max_y - min_y
                
                if area_width < 10 or area_height < 10:
                    picked_color = "CANCELLED"
                    return
                
                try:
                    overlay.withdraw()
                    time.sleep(0.1)
                    
                    screenshot = pyautogui.screenshot(region=(min_x, min_y, area_width, area_height))
                    screenshot_array = np.array(screenshot)
                    
                    logger.debug(f"Screenshot shape: {screenshot_array.shape}, dtype: {screenshot_array.dtype}")
                    logger.debug(f"Sample pixel [0,0]: {screenshot_array[0, 0] if screenshot_array.size > 0 else 'Empty'}")
                    
                    sample_step = max(1, min(area_width, area_height) // 20)
                    colors = []
                    
                    for y in range(0, area_height, sample_step):
                        for x in range(0, area_width, sample_step):
                            if y < screenshot_array.shape[0] and x < screenshot_array.shape[1]:
                                pixel_color = screenshot_array[y, x]
                                if len(pixel_color) >= 3:
                                    rgb = [int(pixel_color[0]), int(pixel_color[1]), int(pixel_color[2])]
                                    colors.append(rgb)
                    
                    logger.debug(f"Sampled {len(colors)} color points")
                    
                    if colors:
                        colors_array = np.array(colors, dtype=np.float64)
                        median_color = np.median(colors_array, axis=0).astype(int)
                        
                        median_color = np.clip(median_color, 0, 255)
                        
                        picked_color = "#{:02x}{:02x}{:02x}".format(
                            int(median_color[0]), int(median_color[1]), int(median_color[2])
                        )
                        
                        logger.debug(f"Median color RGB: {median_color}")
                        logger.debug(f"Final hex color: {picked_color}")
                        
                        try:
                            hex_clean = picked_color[1:]
                            rgb_int = int(hex_clean, 16)
                            test_hsv = rgb_to_hsv_single(rgb_int)
                            logger.debug(f"Converted to HSV: H={test_hsv[0]}, S={test_hsv[1]}, V={test_hsv[2]}")
                        except Exception as conv_e:
                            logger.debug(f"HSV conversion test failed: {conv_e}")
                            
                    else:
                        logger.debug("No colors sampled")
                        picked_color = "CANCELLED"
                        
                except Exception as e:
                    logger.error(f"Error sampling area: {e}")
                    picked_color = "CANCELLED"
            
            def on_escape_key(event):
                nonlocal picked_color
                picked_color = "CANCELLED"

            overlay.focus_set()
            overlay.bind('<Button-1>', on_button_press)
            overlay.bind('<B1-Motion>', on_motion)
            overlay.bind('<ButtonRelease-1>', on_button_release)
            overlay.bind('<Key-Escape>', on_escape_key)
            overlay.bind('<KeyPress-Escape>', on_escape_key)
            overlay.bind('<Escape>', on_escape_key)
            
            overlay.grab_set()
            overlay.update()
            overlay.focus_force()
            
            while picked_color is None:
                time.sleep(0.05)
                try:
                    overlay.update()
                    if overlay.winfo_exists():
                        overlay.focus_force()
                except tk.TclError:
                    picked_color = "CANCELLED"
                    break
            
            try:
                if overlay.winfo_exists():
                    overlay.grab_release()
                overlay.destroy()
            except tk.TclError:
                pass 
            
            self.dig_tool.root.deiconify()
            
            logger.debug(f"picked_color = {picked_color!r}") 
            
            if picked_color and picked_color != "CANCELLED":
                logger.debug(f"Setting picked_color_rgb to {picked_color}")  
                try:
                    self.dig_tool.param_vars['picked_color_rgb'].set(picked_color)
                    logger.debug(f"Parameter set successfully")
                    
                    retrieved_color = self.dig_tool.param_vars['picked_color_rgb'].get()
                    logger.debug(f"Retrieved color after setting: {retrieved_color}")
                    
                    self.dig_tool.param_vars['use_color_picker_detection'].set(True)
                    logger.debug("Enabled color picker detection")  
                    
                    if hasattr(self, 'picked_color_display') and self.picked_color_display:
                        self.picked_color_display.config(bg=picked_color, text="")
                        
                        if hasattr(self, 'picked_color_text') and self.picked_color_text:
                            hex_clean = picked_color[1:]
                            r = int(hex_clean[0:2], 16)
                            g = int(hex_clean[2:4], 16) 
                            b = int(hex_clean[4:6], 16)
                            
                            text_color = "black"
                            
                            self.picked_color_text.config(text=picked_color, fg=text_color)
                        
                        logger.debug("Updated color display widget")
                    else:
                        logger.debug("Color display widget not found")
                    
                    self.dig_tool.update_status(f"Area sampled - Color: {picked_color}")
                    
                except Exception as e:
                    logger.error(f"Error setting parameter: {e}")
                    self.dig_tool.update_status(f"Error setting color: {e}")
            else:
                logger.debug(f"Color sampling was cancelled or failed") 
                self.dig_tool.update_status("Color sampling cancelled")
                
        except Exception as e:
            self.dig_tool.root.deiconify()
            self.dig_tool.update_status(f"Error sampling colors: {e}")

    def _update_multi_checkbox_param(self, var_key, options, checkbox_vars):
        selected_options = []
        for option, var in checkbox_vars.items():
            if var.get():
                selected_options.append(option)
        
        self.dig_tool.param_vars[var_key].set(json.dumps(selected_options))
        self.dig_tool.last_known_good_params[var_key] = selected_options

    def _update_multi_checkbox_display(self, var_key, options, checkbox_vars):
        try:
            current_value = self.dig_tool.param_vars[var_key].get()
            if current_value:
                selected_options = json.loads(current_value) if isinstance(current_value, str) else current_value
            else:
                selected_options = self.dig_tool.settings_manager.get_default_value(var_key)
        except (json.JSONDecodeError, KeyError):
            selected_options = self.dig_tool.settings_manager.get_default_value(var_key)
        
        for option, var in checkbox_vars.items():
            var.set(option in selected_options)

    def update_dependent_widgets_state(self, *args):
        auto_walk_enabled = self.dig_tool.param_vars.get('auto_walk_enabled', tk.BooleanVar()).get()
        
        self._prev_auto_walk_enabled = auto_walk_enabled

        if self.auto_shovel_checkbox:
            if auto_walk_enabled:
                self.auto_shovel_checkbox.config(state='normal', fg="#000000")  # Black text when enabled
            else:
                self.auto_shovel_checkbox.config(state='disabled', fg="#666666")  # Gray text when disabled
                self.dig_tool.param_vars['auto_shovel_enabled'].set(False)

        shovel_enabled = auto_walk_enabled and self.dig_tool.param_vars.get('auto_shovel_enabled',
                                                                            tk.BooleanVar()).get()
        for widget in self.shovel_dependent_widgets:
            widget.config(state='normal' if shovel_enabled else 'disabled')

        if self.auto_sell_checkbox:
            self.auto_sell_checkbox.config(state='normal', fg="#000000")

        sell_enabled = self.dig_tool.param_vars.get('auto_sell_enabled', tk.BooleanVar()).get()
        for widget in self.sell_dependent_widgets:
            widget.config(state='normal' if sell_enabled else 'disabled')

        cursor_enabled = self.dig_tool.param_vars.get('use_custom_cursor', tk.BooleanVar()).get()
        has_cursor_pos = hasattr(self.dig_tool, 'cursor_position') and self.dig_tool.cursor_position
        for widget in self.cursor_dependent_widgets:
            widget.config(state='normal' if cursor_enabled and has_cursor_pos else 'disabled')

        velocity_enabled = self.dig_tool.param_vars.get('velocity_based_width_enabled', tk.BooleanVar()).get()
        for widget in self.velocity_dependent_widgets:
            widget.config(state='normal' if velocity_enabled else 'disabled')

        otsu_enabled = self.dig_tool.param_vars.get('use_otsu_detection', tk.BooleanVar()).get()
        for widget in self.otsu_dependent_widgets:
            widget.config(state='normal' if otsu_enabled else 'disabled')

        color_picker_enabled = self.dig_tool.param_vars.get('use_color_picker_detection', tk.BooleanVar()).get()
        for widget in self.color_picker_dependent_widgets:
            widget.config(state='normal' if color_picker_enabled else 'disabled')

        engagement_enabled = self.dig_tool.param_vars.get('auto_sell_target_engagement_enabled', tk.BooleanVar()).get()
        sell_enabled = self.dig_tool.param_vars.get('auto_sell_enabled', tk.BooleanVar()).get()
        engagement_timeout_enabled = sell_enabled and engagement_enabled
        for widget in self.engagement_timeout_dependent_widgets:
            widget.config(state='normal' if engagement_timeout_enabled else 'disabled')

        # Money detection widgets
        money_detection_enabled = self.dig_tool.param_vars.get('enable_money_detection', tk.BooleanVar()).get()
        for widget in self.money_detection_dependent_widgets:
            if hasattr(widget, 'config'):
                widget.config(state='normal' if money_detection_enabled else 'disabled')
            else:
                logger.warning(f"Widget in money_detection_dependent_widgets has no config method: {type(widget)}")

        # Item detection widgets
        item_detection_enabled = self.dig_tool.param_vars.get('enable_item_detection', tk.BooleanVar()).get()
        for widget in self.item_detection_dependent_widgets:
            if hasattr(widget, 'config'):
                widget.config(state='normal' if item_detection_enabled else 'disabled')
            else:
                logger.warning(f"Widget in item_detection_dependent_widgets has no config method: {type(widget)}")

        # Walkspeed dependent widgets
        walkspeed_enabled = self.dig_tool.param_vars.get('dynamic_walkspeed_enabled', tk.BooleanVar()).get()
        for widget in self.walkspeed_dependent_widgets:
            if hasattr(widget, 'config'):
                widget.config(state='normal' if walkspeed_enabled else 'disabled')

        for tooltip in self.disabled_tooltips:
            if hasattr(tooltip, 'widget_type'):
                if tooltip.widget_type == 'shovel':
                    tooltip.set_disabled(not auto_walk_enabled, "Disabled: Auto-walk must be enabled first.")
                elif tooltip.widget_type == 'sell':
                    if not sell_enabled:
                        tooltip.set_disabled(True, "Disabled: Auto-sell must be enabled first.")
                    else:
                        sell_button_set = self.dig_tool.automation_manager.sell_button_position is not None
                        tooltip.set_disabled(not sell_button_set, "Disabled: Set sell button position first.")
                elif tooltip.widget_type == 'cursor':
                    tooltip.set_disabled(not has_cursor_pos, "Disabled: Set cursor position first.")
                elif tooltip.widget_type == 'velocity':
                    tooltip.set_disabled(not velocity_enabled, "Disabled: Enable Velocity-Based Width first.")
                elif tooltip.widget_type == 'engagement_timeout':
                    if not sell_enabled:
                        tooltip.set_disabled(True, "Disabled: Auto-sell must be enabled first.")
                    elif not engagement_enabled:
                        tooltip.set_disabled(True, "Disabled: Enable Post-Sell Engagement Monitoring first.")
                    else:
                        tooltip.set_disabled(False, "")

        if self.money_test_button:
            money_area_set = self.is_money_area_set()
            if money_area_set:
                self.money_test_button.config(state='normal', fg="#000000")
            else:
                self.money_test_button.config(state='disabled', fg="#666666")

        if self.item_test_button:
            item_area_set = self.is_item_area_set()
            if item_area_set:
                self.item_test_button.config(state='normal', fg="#000000")
            else:
                self.item_test_button.config(state='disabled', fg="#666666")

    def create_ui(self):
        BG_COLOR = "#f0f0f0"  # Light gray main background
        FRAME_BG = "#ffffff"  # White frame background
        TEXT_COLOR = "#000000"  # Black text
        BTN_BG = "#e1e1e1"  # Light gray button background
        FONT_FAMILY = "Segoe UI"
        SECTION_PADY = 3  
        PARAM_PADY = 2    
        PARAM_PADX = 6    
        ENTRY_WIDTH = 18
        BUTTON_PADY = 5   
        LABEL_WIDTH = 25

        self.dig_tool.root.configure(bg=BG_COLOR)
        
      
        main_container = Frame(self.dig_tool.root, bg=BG_COLOR)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
      
        canvas = tk.Canvas(main_container, bg=BG_COLOR, highlightthickness=0)
        canvas.pack(fill='both', expand=True)
        
        
        self.dig_tool.controls_panel = Frame(canvas, bg=BG_COLOR)
        
        
        canvas_window = canvas.create_window((0, 0), window=self.dig_tool.controls_panel, anchor="nw")
        
        
        def _on_mousewheel(event):
            scroll_region = canvas.cget("scrollregion")
            if scroll_region:
                x1, y1, x2, y2 = map(float, scroll_region.split())
                content_height = y2 - y1
                canvas_height = canvas.winfo_height()
                
                if content_height > canvas_height:
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)
        
       
        def _configure_canvas(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas_width = canvas.winfo_width()
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        self.dig_tool.controls_panel.bind('<Configure>', _configure_canvas)
        canvas.bind('<Configure>', _configure_canvas)

        main_title = Label(self.dig_tool.controls_panel, text="Dig Tool", font=(FONT_FAMILY, 16, 'bold'), 
                          bg=BG_COLOR, fg="#2c3e50")
        main_title.pack(pady=(0, 8), anchor='center')

        status_title_frame = Frame(self.dig_tool.controls_panel, bg=BG_COLOR)
        status_title_frame.pack(fill=tk.X, pady=(0, 3), padx=5)
        
        status_title = Label(status_title_frame, text="Status", font=(FONT_FAMILY, 10, 'bold'), 
                            bg=BG_COLOR, fg="#2c3e50")
        status_title.pack(anchor='w')
        
        separator = Frame(status_title_frame, height=1, bg="#cccccc")
        separator.pack(fill=tk.X, pady=(2, 0))

        status_outer_frame = Frame(self.dig_tool.controls_panel, bg="#b8b8b8", relief='solid', bd=1)
        status_outer_frame.pack(fill=tk.X, pady=(0, 5), padx=2)
        
        status_frame = Frame(status_outer_frame, bg="#e8e8e8", relief='flat', bd=0)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        from tkinter import Text
        self.dig_tool.status_text = Text(status_frame, height=3, font=(FONT_FAMILY, 9), bg="#e8e8e8", 
                                        fg=TEXT_COLOR, wrap=tk.WORD, relief='flat', bd=0, state='disabled',
                                        cursor='arrow', highlightthickness=0)
        self.dig_tool.status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        self.dig_tool.status_text.config(state='normal')
        self.dig_tool.status_text.delete(1.0, tk.END)
        self.dig_tool.status_text.insert(1.0, "Select a game area to begin.")
        self.dig_tool.status_text.config(state='disabled')
        
        indicator_frame = Frame(self.dig_tool.controls_panel, bg=BG_COLOR)
        indicator_frame.pack(fill=tk.X, pady=(0, 10), padx=2)
        
        self.dig_tool.game_area_indicator = Label(indicator_frame, text="✗ Game Area: Not Set", 
                                                 font=(FONT_FAMILY, 9), bg=BG_COLOR, fg="#cc0000")
        self.dig_tool.game_area_indicator.pack(anchor='w', padx=5)

        actions_frame = Frame(self.dig_tool.controls_panel, bg=BG_COLOR)
        actions_frame.pack(fill=tk.X, pady=(0, SECTION_PADY))

        button_style = {'font': (FONT_FAMILY, 9), 'bg': BTN_BG, 'fg': TEXT_COLOR, 'relief': 'solid', 'borderwidth': 1,
                        'pady': 6}

        for i, (text, command) in enumerate(
                [("Select Area", lambda: start_area_selection(self.dig_tool)), ("Start", self.dig_tool.toggle_detection),
                 ("Show/Hide", lambda: toggle_gui(self.dig_tool)), ("Overlay", lambda: toggle_overlay(self.dig_tool))]):
            btn = Button(actions_frame, text=text, command=command, **button_style)
            if text == "Start":
                self.dig_tool.start_stop_btn = btn
            elif text == "Show/Hide":
                self.dig_tool.toggle_gui_btn = btn
            elif text == "Overlay":
                self.dig_tool.overlay_btn = btn
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0 if i == 0 else 2, 2 if i < 3 else 0))

        actions_frame2 = Frame(self.dig_tool.controls_panel, bg=BG_COLOR)
        actions_frame2.pack(fill=tk.X, pady=(SECTION_PADY, 0))

        for i, (text, command, attr) in enumerate([("Show Preview", lambda: toggle_preview_window(self.dig_tool), 'preview_btn'),
                                                   ("Show Debug", lambda: toggle_debug_window(self.dig_tool), 'debug_btn')]):
            btn = Button(actions_frame2, text=text, command=command, **button_style)
            if attr:
                setattr(self.dig_tool, attr, btn)
                btn.config(state=tk.DISABLED)
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        actions_frame3 = Frame(self.dig_tool.controls_panel, bg=BG_COLOR)
        actions_frame3.pack(fill=tk.X, pady=(SECTION_PADY, 0))

        config_frame = Frame(self.dig_tool.controls_panel, bg=BG_COLOR)
        config_frame.pack(fill='x', pady=(8, 0))

        style = ttk.Style()
        style.configure("Header.TButton", font=(FONT_FAMILY, 9, 'bold'), background="#dcdcdc",
                        relief="flat")  # Light gray header buttons
        style.map("Header.TButton", background=[('active', '#c8c8c8')])  # Darker gray on hover

        self.dig_tool.accordion = AccordionManager(self.dig_tool)

        panes_config = [
            ("Detection", "#e8f4f8"),  # Light blue - detection settings
            ("Behavior", FRAME_BG),  # White - behavior settings
            ("Auto-Walk", "#e8f0ff"),  # Light blue-purple - auto-walk settings
            ("Discord", "#f8e8f8"),  # Light pink - discord settings
            ("Window", "#f8f0e8"),  # Light orange - window settings
            ("Debug", "#f8e8e8"),  # Light red - debug settings
            ("Hotkeys", "#e8e8f8"),  # Light purple - hotkey settings
            ("Settings", "#e8f8f0")  # Light green - settings
        ]

        panes = {}
        for name, color in panes_config:
            pane = CollapsiblePane(config_frame, text=name, manager=self.dig_tool.accordion, bg_color=color)
            pane.pack(fill='x', pady=1)  
            self.dig_tool.accordion.add_pane(pane)
            panes[name.lower().replace('-', '_')] = pane

        def create_param_entry(parent, text, var_key, dependent_list=None, widget_type=None):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

            label = Label(frame, text=text, font=(FONT_FAMILY, 9), bg=parent.cget('bg'), fg=TEXT_COLOR,
                          width=LABEL_WIDTH, anchor='w')
            label.pack(side='left')

            tooltip_text = self.dig_tool.settings_manager.get_description(var_key)
            Tooltip(label, tooltip_text)

            default_value = self.dig_tool.settings_manager.get_default_value(var_key)
            var_type = self.dig_tool.settings_manager.get_param_type(var_key)

            if var_key not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key] = var_type(value=default_value)
                self.dig_tool.last_known_good_params[var_key] = default_value

            if var_type != tk.BooleanVar:
                entry = tk.Entry(frame, textvariable=self.dig_tool.param_vars[var_key], font=(FONT_FAMILY, 9),
                                 bg=FRAME_BG, fg=TEXT_COLOR, relief='solid', width=ENTRY_WIDTH, borderwidth=1)
                entry.bind('<FocusOut>', lambda event, key=var_key: self.validate_on_focus_out(key, self.dig_tool.param_vars[key].get()))
                entry.bind('<Return>', lambda event, key=var_key: self.validate_on_focus_out(key, self.dig_tool.param_vars[key].get()))
                entry.pack(side='right', ipady=3)

                if dependent_list is not None: dependent_list.append(entry)
                if widget_type:
                    disabled_tooltip = DisabledTooltip(entry, "", tooltip_text)
                    disabled_tooltip.widget_type = widget_type
                    self.disabled_tooltips.append(disabled_tooltip)
                
                return entry

        def create_dual_param_entry(parent, text1, var_key1, text2, var_key2, dependent_list=None, widget_type=None):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

            left_frame = Frame(frame, bg=parent.cget('bg'))
            left_frame.pack(side='left', fill='x', expand=True)

            label1 = Label(left_frame, text=text1, font=(FONT_FAMILY, 9), bg=parent.cget('bg'), fg=TEXT_COLOR, width=18,
                           anchor='w')
            label1.pack(side='left')

            tooltip_text1 = self.dig_tool.settings_manager.get_description(var_key1)
            Tooltip(label1, tooltip_text1)

            default_value1 = self.dig_tool.settings_manager.get_default_value(var_key1)
            var_type1 = self.dig_tool.settings_manager.get_param_type(var_key1)

            if var_key1 not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key1] = var_type1(value=default_value1)
                self.dig_tool.last_known_good_params[var_key1] = default_value1

            if var_type1 != tk.BooleanVar:
                entry1 = tk.Entry(left_frame, textvariable=self.dig_tool.param_vars[var_key1], font=(FONT_FAMILY, 9),
                                  bg=FRAME_BG, fg=TEXT_COLOR, relief='solid', width=12, borderwidth=1)
                entry1.bind('<FocusOut>', lambda event, key=var_key1: self.validate_on_focus_out(key, self.dig_tool.param_vars[key].get()))
                entry1.bind('<Return>', lambda event, key=var_key1: self.validate_on_focus_out(key, self.dig_tool.param_vars[key].get()))
                entry1.pack(side='right', ipady=3, padx=(4, 8))
                if dependent_list is not None: dependent_list.append(entry1)
                if widget_type:
                    disabled_tooltip = DisabledTooltip(entry1, "", tooltip_text1)
                    disabled_tooltip.widget_type = widget_type
                    self.disabled_tooltips.append(disabled_tooltip)

            right_frame = Frame(frame, bg=parent.cget('bg'))
            right_frame.pack(side='right', fill='x', expand=True)

            label2 = Label(right_frame, text=text2, font=(FONT_FAMILY, 9), bg=parent.cget('bg'), fg=TEXT_COLOR,
                           width=18, anchor='w')
            label2.pack(side='left')

            tooltip_text2 = self.dig_tool.settings_manager.get_description(var_key2)
            Tooltip(label2, tooltip_text2)

            default_value2 = self.dig_tool.settings_manager.get_default_value(var_key2)
            var_type2 = self.dig_tool.settings_manager.get_param_type(var_key2)

            if var_key2 not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key2] = var_type2(value=default_value2)
                self.dig_tool.last_known_good_params[var_key2] = default_value2

            if var_type2 != tk.BooleanVar:
                entry2 = tk.Entry(right_frame, textvariable=self.dig_tool.param_vars[var_key2], font=(FONT_FAMILY, 9),
                                  bg=FRAME_BG, fg=TEXT_COLOR, relief='solid', width=12, borderwidth=1)
                entry2.bind('<FocusOut>', lambda event, key=var_key2: self.validate_on_focus_out(key, self.dig_tool.param_vars[key].get()))
                entry2.bind('<Return>', lambda event, key=var_key2: self.validate_on_focus_out(key, self.dig_tool.param_vars[key].get()))
                entry2.pack(side='right', ipady=3)
                if dependent_list is not None: dependent_list.append(entry2)
                if widget_type:
                    disabled_tooltip = DisabledTooltip(entry2, "", tooltip_text2)
                    disabled_tooltip.widget_type = widget_type
                    self.disabled_tooltips.append(disabled_tooltip)

        def create_checkbox_param(parent, text, var_key, dependent_list=None, widget_type=None,
                                  validation_callback=None):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

            default_value = self.dig_tool.settings_manager.get_default_value(var_key)
            if var_key not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key] = tk.BooleanVar(value=default_value)
                self.dig_tool.last_known_good_params[var_key] = default_value

            check = Checkbutton(frame, text=text, variable=self.dig_tool.param_vars[var_key], bg=parent.cget('bg'),
                                fg=TEXT_COLOR,
                                selectcolor=BG_COLOR, activebackground=parent.cget('bg'), activeforeground=TEXT_COLOR,
                                font=(FONT_FAMILY, 9), anchor='w')
            check.pack(anchor='w', fill='x')

            tooltip_text = self.dig_tool.settings_manager.get_description(var_key)

            if widget_type:
                disabled_tooltip = DisabledTooltip(check, "", tooltip_text)
                disabled_tooltip.widget_type = widget_type
                self.disabled_tooltips.append(disabled_tooltip)
            else:
                Tooltip(check, tooltip_text)

            if validation_callback: self.dig_tool.param_vars[var_key].trace_add('write', validation_callback)
            if dependent_list is not None: dependent_list.append(check)

            return check

        def create_dropdown_param(parent, text, var_key, values, dependent_list=None, widget_type=None):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

            label = Label(frame, text=text, font=(FONT_FAMILY, 9), bg=parent.cget('bg'), fg=TEXT_COLOR,
                          width=LABEL_WIDTH, anchor='w')
            label.pack(side='left')

            tooltip_text = self.dig_tool.settings_manager.get_description(var_key)
            Tooltip(label, tooltip_text)

            default_value = self.dig_tool.settings_manager.get_default_value(var_key)
            if var_key not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key] = tk.StringVar(value=default_value)
                self.dig_tool.last_known_good_params[var_key] = default_value

            combo = ttk.Combobox(frame, textvariable=self.dig_tool.param_vars[var_key], values=values, state="readonly",
                                 width=ENTRY_WIDTH - 2, font=(FONT_FAMILY, 9), height=8)
            combo.pack(side='right', ipady=3)

            if dependent_list is not None: dependent_list.append(combo)
            if widget_type:
                disabled_tooltip = DisabledTooltip(combo, "", tooltip_text)
                disabled_tooltip.widget_type = widget_type
                self.disabled_tooltips.append(disabled_tooltip)

            return combo

        def create_section_button(parent, text, command, dependent_list=None, widget_type=None):
            btn_frame = Frame(parent, bg=parent.cget('bg'))
            btn_frame.pack(fill='x', pady=BUTTON_PADY, padx=PARAM_PADX)
            btn = Button(btn_frame, text=text, command=command, font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR,
                         relief='solid', borderwidth=1, pady=4)
            btn.pack(expand=True, fill=tk.X)

            if dependent_list is not None: dependent_list.append(btn)
            if widget_type:
                disabled_tooltip = DisabledTooltip(btn, "", f"Test button for {text.lower()}.")
                disabled_tooltip.widget_type = widget_type
                self.disabled_tooltips.append(disabled_tooltip)

            return btn

        def create_multi_checkbox_param(parent, text, var_key, options, colors=None, dependent_list=None, widget_type=None, 
                                       validation_callback=None, max_cols=2):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

            label = Label(frame, text=text, font=(FONT_FAMILY, 9), bg=parent.cget('bg'), fg=TEXT_COLOR,
                         width=LABEL_WIDTH, anchor='w')
            label.pack(side='left')

            tooltip_text = self.dig_tool.settings_manager.get_description(var_key)
            Tooltip(label, tooltip_text)

            default_value = self.dig_tool.settings_manager.get_default_value(var_key)
            if var_key not in self.dig_tool.param_vars:
                self.dig_tool.param_vars[var_key] = tk.StringVar(value=json.dumps(default_value))
                self.dig_tool.last_known_good_params[var_key] = default_value

            right_frame = Frame(frame, bg=parent.cget('bg'))
            right_frame.pack(side='right', fill='x', expand=True)
            
            checkbox_vars = {}
            checkbox_widgets = []
            row, col = 0, 0
            
            for option in options:
                var = tk.BooleanVar()
                color = colors.get(option, TEXT_COLOR) if colors else TEXT_COLOR
                
                checkbox = Checkbutton(right_frame, text=option.title(), variable=var,
                                     bg=parent.cget('bg'), fg=color, selectcolor=FRAME_BG,
                                     activebackground=parent.cget('bg'), activeforeground=color,
                                     font=(FONT_FAMILY, 9), anchor='w', width=12)
                
                checkbox.configure(command=lambda v=var_key, o=options, c=checkbox_vars: self._update_multi_checkbox_param(v, o, c))
                
                checkbox.grid(row=row, column=col, sticky='ew', padx=3, pady=1)
                checkbox_vars[option] = var
                checkbox_widgets.append(checkbox)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

            for i in range(max_cols):
                right_frame.grid_columnconfigure(i, weight=1)

            setattr(self, f'{var_key}_checkbox_vars', checkbox_vars)
            
            self._update_multi_checkbox_display(var_key, options, checkbox_vars)
            
            if dependent_list is not None:
                dependent_list.extend(checkbox_widgets)
            
            if validation_callback:
                self.dig_tool.param_vars[var_key].trace_add('write', validation_callback)

            return frame

        create_dual_param_entry(panes['detection'].sub_frame, "Line Sensitivity:", 'line_sensitivity',
                                "Line Detection Offset:", 'line_detection_offset')
        create_dual_param_entry(panes['detection'].sub_frame, "Zone Min Width:", 'zone_min_width',
                                "Zone Max Width (%):", 'max_zone_width_percent')
        create_dual_param_entry(panes['detection'].sub_frame, "Zone Min Height (%):", 'min_zone_height_percent',
                                "Saturation Threshold:", 'saturation_threshold')

        # Otsu Detection Settings (Collapsible)
        otsu_subsection = CollapsibleSubsection(panes['detection'].sub_frame, "Otsu Detection (Alternative Method)",
                                               "#fff0e6")  # Light orange for alternative detection
        create_checkbox_param(otsu_subsection.content, "Use Otsu Detection", 'use_otsu_detection',
                              validation_callback=self.validate_otsu_toggle)
        create_checkbox_param(otsu_subsection.content, "Adaptive Area Filtering", 'otsu_adaptive_area',
                              self.otsu_dependent_widgets, 'otsu')
        create_checkbox_param(otsu_subsection.content, "Disable Color Lock", 'otsu_disable_color_lock',
                              self.otsu_dependent_widgets, 'otsu')
        create_dual_param_entry(otsu_subsection.content, "Min Area (pixels):", 'otsu_min_area',
                               "Max Area (pixels):", 'otsu_max_area',
                               self.otsu_dependent_widgets, 'otsu')
        create_dual_param_entry(otsu_subsection.content, "Morph Kernel Size:", 'otsu_morph_kernel_size',
                               "Area Percentile:", 'otsu_area_percentile',
                               self.otsu_dependent_widgets, 'otsu')

        # Color Picker Detection Settings (Collapsible)
        color_picker_subsection = CollapsibleSubsection(panes['detection'].sub_frame, "Color Picker Detection (Simple Method)",
                                                        "#f0f0f0")  # Use consistent light gray background
        create_checkbox_param(color_picker_subsection.content, "Use Color Picker Detection", 'use_color_picker_detection',
                              validation_callback=self.validate_color_picker_toggle)
        
        # Initialize the picked_color_rgb parameter if it doesn't exist
        if 'picked_color_rgb' not in self.dig_tool.param_vars:
            default_color = self.dig_tool.settings_manager.get_default_value('picked_color_rgb')
            self.dig_tool.param_vars['picked_color_rgb'] = tk.StringVar(value=default_color)
            self.dig_tool.last_known_good_params['picked_color_rgb'] = default_color
        
        # Color display and pick button frame
        color_frame = Frame(color_picker_subsection.content)
        color_frame.pack(fill='x', padx=5, pady=2)
        
        Label(color_frame, text="Sampled Color:", font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        
        color_display_container = Frame(color_frame, bg=color_frame.cget('bg'))
        color_display_container.pack(side='left', padx=(0, 5))
        
        self.picked_color_display = Label(color_display_container, text="  ", bg='lightgray', relief='solid', bd=1, width=4, height=1)
        self.picked_color_display.pack()
        
        self.picked_color_text = Label(color_display_container, text="None", font=("Segoe UI", 8), bg=color_frame.cget('bg'), fg="black")
        self.picked_color_text.pack()
        
        self.pick_color_btn = Button(color_frame, text="Sample Area", command=self.pick_color_from_screen)
        self.pick_color_btn.pack(side='left', padx=(5, 0), pady=2)
        self.color_picker_dependent_widgets.append(self.pick_color_btn)
        
        create_param_entry(color_picker_subsection.content, "Color Tolerance:", 'color_tolerance',
                          self.color_picker_dependent_widgets, 'color_picker')

        create_param_entry(panes['behavior'].sub_frame, "Zone Smoothing:", 'zone_smoothing_factor')
        create_param_entry(panes['behavior'].sub_frame, "Target Width (%):", 'sweet_spot_width_percent')
        create_checkbox_param(panes['behavior'].sub_frame, "Enable Velocity-Based Width", 'velocity_based_width_enabled',
                              validation_callback=self.validate_velocity_toggle)
        create_param_entry(panes['behavior'].sub_frame, "Velocity Width Multiplier:", 'velocity_width_multiplier', 
                          self.velocity_dependent_widgets, 'velocity')
        create_param_entry(panes['behavior'].sub_frame, "Max Velocity Factor:", 'velocity_max_factor',
                          self.velocity_dependent_widgets, 'velocity')
        create_param_entry(panes['behavior'].sub_frame, "Line Exclusion Radius:", 'line_exclusion_radius')
        create_param_entry(panes['behavior'].sub_frame, "Post-Click Blindness (ms):", 'post_click_blindness')

        pred_subsection = CollapsibleSubsection(panes['behavior'].sub_frame, "Prediction Settings",
                                                "#e8f5e8")  # Light green for predictions
        create_checkbox_param(pred_subsection.content, "Enable Prediction", 'prediction_enabled')
        
        create_param_entry(pred_subsection.content, "Game FPS:", 'target_fps')
        create_param_entry(pred_subsection.content, "Prediction Confidence:", 'prediction_confidence_threshold')

        cursor_subsection = CollapsibleSubsection(panes['behavior'].sub_frame, "Cursor Settings",
                                                  "#fff0e8")  # Light orange for cursor settings
        self.use_cursor_checkbox = create_checkbox_param(cursor_subsection.content, "Use Custom Cursor Position",
                                                         'use_custom_cursor',
                                                         widget_type='cursor',
                                                         validation_callback=self.validate_cursor_position_toggle)

        cursor_pos_btn = create_section_button(cursor_subsection.content, "Set Cursor Position",
                              lambda: start_cursor_position_selection(self.dig_tool))
        StatusTooltip(cursor_pos_btn, "Click to set a custom cursor position for clicking",
                      "Cursor position is set. Click to change it.", self.is_cursor_position_set)

        # ===== AUTO-WALK PANE =====
        auto_walk_check = create_checkbox_param(panes['auto_walk'].sub_frame, "Enable Auto-Walk", 'auto_walk_enabled')
        create_param_entry(panes['auto_walk'].sub_frame, "Key Duration (ms):", 'walk_duration')
        
        # Decreased Walkspeed settings
        dynamic_walkspeed_check = create_checkbox_param(panes['auto_walk'].sub_frame, "Enable Decreased Walkspeed", 'dynamic_walkspeed_enabled')
        create_param_entry(panes['auto_walk'].sub_frame, "Initial Item Count:", 'initial_item_count', dependent_list=self.walkspeed_dependent_widgets)
        create_param_entry(panes['auto_walk'].sub_frame, "Initial Walkspeed Decrease:", 'initial_walkspeed_decrease', dependent_list=self.walkspeed_dependent_widgets)
        
        # Auto Walk Overlay button
        overlay_button_frame = Frame(panes['auto_walk'].sub_frame, bg="#e8f0ff")
        overlay_button_frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)
        
        autowalk_overlay_btn = Button(overlay_button_frame, text="Open Auto Walk Overlay", 
                                     command=lambda: toggle_autowalk_overlay(self.dig_tool),
                                     font=(FONT_FAMILY, 9), bg='#d4e6f1', fg='#2c3e50', 
                                     relief='solid', borderwidth=1, pady=4)
        autowalk_overlay_btn.pack(fill='x')
        
        Tooltip(autowalk_overlay_btn, "Open a separate overlay window showing detailed auto walk information, walkspeed calculations, and status")

        pattern_frame = Frame(panes['auto_walk'].sub_frame, bg="#e8f0ff")  # Light blue background
        pattern_frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

        Label(pattern_frame, text="Walk Pattern:", font=(FONT_FAMILY, 9), bg="#e8f0ff", fg=TEXT_COLOR,
              width=LABEL_WIDTH, anchor='w').pack(side='left')

        self.dig_tool.walk_pattern_var = tk.StringVar(value="_KC_Nugget_v1")
        self.dig_tool.walk_pattern_var.trace_add('write', lambda *args: on_walk_pattern_changed(self.dig_tool, *args))
        self.walk_pattern_combo = ttk.Combobox(pattern_frame, textvariable=self.dig_tool.walk_pattern_var,
                                               values=list(self.dig_tool.automation_manager.get_pattern_list().keys()),
                                               state="readonly", width=ENTRY_WIDTH, font=(FONT_FAMILY, 9), height=8)
        self.walk_pattern_combo.pack(side='right', ipady=3)

        custom_pattern_frame = Frame(panes['auto_walk'].sub_frame, bg="#e8f0ff")  # Light blue background
        custom_pattern_frame.pack(fill='x', pady=PARAM_PADY, padx=PARAM_PADX)

        custom_pattern_btn = Button(custom_pattern_frame, text="Manage Custom Patterns",
                                    command=lambda: open_custom_pattern_manager(self.dig_tool),
                                    font=(FONT_FAMILY, 9), bg="#4CAF50", fg="white", relief='solid', borderwidth=1,
                                    pady=4)  # Green button
        custom_pattern_btn.pack(side='left', expand=True, fill='x', padx=(0, 2))

        refresh_pattern_btn = Button(custom_pattern_frame, text="Refresh Patterns",
                                     command=self.dig_tool.settings_manager.refresh_pattern_dropdown,
                                     font=(FONT_FAMILY, 9), bg="#2196F3", fg="white", relief='solid', borderwidth=1,
                                     pady=4)  # Blue button
        refresh_pattern_btn.pack(side='left', expand=True, fill='x', padx=2)

        shovel_subsection = CollapsibleSubsection(panes['auto_walk'].sub_frame, "Shovel Management",
                                                  "#ffe8e8")  # Light red for shovel management
        self.auto_shovel_checkbox = create_checkbox_param(shovel_subsection.content, "Enable Auto-Shovel",
                                                          'auto_shovel_enabled', widget_type='shovel')
        create_dual_param_entry(shovel_subsection.content, "Shovel Slot (0-9):", 'shovel_slot', "Timeout (minutes):",
                                'shovel_timeout',
                                self.shovel_dependent_widgets, 'shovel')

        create_dropdown_param(shovel_subsection.content, "Equip Mode:", 'shovel_equip_mode', ["single", "double"],
                              self.shovel_dependent_widgets, 'shovel')

        create_section_button(shovel_subsection.content, "Test Shovel Equip",
                              self.dig_tool.automation_manager.test_shovel_equip,
                              self.shovel_dependent_widgets, 'shovel')

        # Auto-Sell subsection within Auto-Walk pane
        auto_sell_subsection = CollapsibleSubsection(panes['auto_walk'].sub_frame, "Auto-Sell Settings",
                                                    "#fff8e8")
        self.auto_sell_checkbox = create_checkbox_param(auto_sell_subsection.content, "Enable Auto-Sell",
                                                        'auto_sell_enabled',
                                                        widget_type='sell',
                                                        validation_callback=self.validate_auto_sell_toggle)
        
        sell_button_btn = create_section_button(auto_sell_subsection.content, "Set Sell Button",
                                               lambda: start_sell_button_selection(self.dig_tool))
        StatusTooltip(sell_button_btn, "Click to set the sell button position for auto-selling",
                      "Sell button position is set. Click to change it.", self.is_sell_button_set)
        
        sell_button_frame = sell_button_btn.master
        sell_button_frame.pack_forget() # type: ignore
        
        self.sell_button_widgets = [sell_button_frame]
        
        self.sell_delay_frame = tk.Frame(auto_sell_subsection.content, bg=auto_sell_subsection.content.cget('bg'))
        self.sell_delay_entry = create_param_entry(self.sell_delay_frame, "Sell Delay (ms):", 'sell_delay',
                                                  self.sell_dependent_widgets, 'sell')
        
        self.sell_delay_widgets = [self.sell_delay_frame]
        
        create_dropdown_param(auto_sell_subsection.content, "Auto-Sell Method:", 'auto_sell_method',
                             ['button_click', 'ui_navigation'],
                             self.sell_dependent_widgets, 'sell')
        
        
        self.ui_sequence_frame = tk.Frame(auto_sell_subsection.content, bg=auto_sell_subsection.content.cget('bg'))
        
        self.ui_sequence_entry = create_param_entry(self.ui_sequence_frame, "UI Navigation Sequence:", 'auto_sell_ui_sequence',
                                                   self.sell_dependent_widgets, 'sell')
        
       
        self.ui_sequence_widgets = [self.ui_sequence_frame]
        
        
        create_param_entry(auto_sell_subsection.content, "Sell Every X Digs:", 'sell_every_x_digs',
                          self.sell_dependent_widgets, 'sell')
        
        create_checkbox_param(auto_sell_subsection.content, "Enable Post-Sell Engagement Monitoring",
                             'auto_sell_target_engagement_enabled',
                             self.sell_dependent_widgets, 'sell')
        
        create_param_entry(auto_sell_subsection.content, "Post-Sell Engagement Timeout (s):", 'auto_sell_target_engagement_timeout',
                          self.engagement_timeout_dependent_widgets, 'engagement_timeout')

        self.test_sell_button = create_section_button(auto_sell_subsection.content, "Test Sell Click",
                              lambda: test_sell_button_click(self.dig_tool),
                              self.sell_dependent_widgets, 'sell')
        
        def update_test_button_text(*args):
            method = self.dig_tool.param_vars.get('auto_sell_method', tk.StringVar()).get()
            if method == "button_click":
                self.test_sell_button.config(text="Test Sell Click")
             
                for widget in self.ui_sequence_widgets:
                    widget.pack_forget()  # type: ignore
               
                for widget in self.sell_button_widgets:
                    widget.pack(fill='x', padx=10, pady=5)  # type: ignore
                
                for widget in self.sell_delay_widgets:
                    widget.pack(fill='x', padx=10, pady=2)  # type: ignore
            elif method == "ui_navigation":
                self.test_sell_button.config(text="Test UI Navigation")
             
                for widget in self.ui_sequence_widgets:
                    widget.pack(fill='x', padx=10, pady=2)  # type: ignore
            
                for widget in self.sell_delay_widgets:
                    widget.pack_forget()  # type: ignore
                
                for widget in self.sell_button_widgets:
                    widget.pack_forget()  # type: ignore
            
                for widget in self.sell_delay_widgets:
                    widget.pack_forget()  # type: ignore
            else:
                self.test_sell_button.config(text="Test Sell")
                for widget in self.ui_sequence_widgets:
                    widget.pack_forget()  # type: ignore
                for widget in self.sell_delay_widgets:
                    widget.pack_forget()  # type: ignore
                for widget in self.sell_button_widgets:
                    widget.pack_forget()  # type: ignore
                    
        self.dig_tool.param_vars['auto_sell_method'].trace('w', update_test_button_text)
        self.dig_tool.root.after_idle(update_test_button_text)

        # Auto-Rejoin subsection within Auto-Walk pane
        auto_rejoin_subsection = CollapsibleSubsection(panes['auto_walk'].sub_frame, "Auto-Rejoin Settings",
                                                      "#f0f0f8")
        rejoin_checkbox = create_checkbox_param(auto_rejoin_subsection.content, "Enable Auto-Rejoin", 'auto_rejoin_enabled')
        Tooltip(rejoin_checkbox, "Automatically rejoin Roblox servers when disconnected or kicked")
        
        create_param_entry(auto_rejoin_subsection.content, "Server Link:", 'roblox_server_link')
        
        create_param_entry(auto_rejoin_subsection.content, "Check Interval (seconds):", 'rejoin_check_interval')
        
        create_param_entry(auto_rejoin_subsection.content, "Restart Delay (seconds):", 'auto_rejoin_restart_delay')
        
        discord_notif_checkbox = create_checkbox_param(auto_rejoin_subsection.content, "Enable Discord Notifications", 'auto_rejoin_discord_notifications')
        Tooltip(discord_notif_checkbox, "Send Discord notifications for disconnections and rejoin attempts")

        # ===== DISCORD PANE =====
        create_param_entry(panes['discord'].sub_frame, "Discord User ID:", 'user_id')
        create_param_entry(panes['discord'].sub_frame, "Discord Server ID:", 'server_id')
        create_param_entry(panes['discord'].sub_frame, "Discord Webhook URL:", 'webhook_url')
        create_param_entry(panes['discord'].sub_frame, "Milestone Interval:", 'milestone_interval')
        create_checkbox_param(panes['discord'].sub_frame, "Include Screenshot in Discord Notifications",
                              'include_screenshot_in_discord')

        create_section_button(panes['discord'].sub_frame, "Test Discord Ping", lambda: test_discord_ping(self.dig_tool))

        money_detection_subsection = CollapsibleSubsection(panes['discord'].sub_frame, "Money Detection",
                                                           "#e8f8e8")
        create_checkbox_param(money_detection_subsection.content, "Enable Money Detection", 'enable_money_detection',
                              validation_callback=self.validate_money_detection_toggle)
        money_area_btn = create_section_button(money_detection_subsection.content, "Select Money Area", 
                              lambda: select_money_area(self.dig_tool))
        StatusTooltip(money_area_btn, "Click to select the money detection area",
                      "Money area is set. Click to change it.", self.is_money_area_set)
        self.money_test_button = create_section_button(money_detection_subsection.content, "Test Money OCR", 
                              lambda: test_money_ocr(self.dig_tool))
        StatusTooltip(self.money_test_button, "Money area must be set first before testing OCR.",
                      "Click to test money OCR detection.", self.is_money_area_set)

        item_detection_subsection = CollapsibleSubsection(panes['discord'].sub_frame, "Item Detection",
                                                          "#f0f8f0")
        create_checkbox_param(item_detection_subsection.content, "Enable Item Detection", 'enable_item_detection',
                              validation_callback=self.validate_item_detection_toggle)
        item_area_btn = create_section_button(item_detection_subsection.content, "Select Item Area", 
                              lambda: select_item_area(self.dig_tool))
        StatusTooltip(item_area_btn, "Click to select the item detection area",
                      "Item area is set. Click to change it.", self.is_item_area_set)
        self.item_test_button = create_section_button(item_detection_subsection.content, "Test Item OCR", 
                              lambda: test_item_ocr(self.dig_tool))
        StatusTooltip(self.item_test_button, "Item area must be set first before testing OCR.",
                      "Click to test item OCR detection.", self.is_item_area_set)

        notification_rarity_colors = {
            'scarce': "#BB68F3",
            'legendary': '#FF8C00', 
            'mythical': '#FF1493',
            'divine': "#FF0000",
            'prismatic': "#F34545"
        }
        create_multi_checkbox_param(item_detection_subsection.content, "Notification Rarities:", 'notification_rarities',
                                   ["scarce", "legendary", "mythical", "divine", "prismatic"],
                                   colors=notification_rarity_colors,
                                   dependent_list=self.item_detection_dependent_widgets, widget_type='item_detection')

        create_checkbox_param(panes['window'].sub_frame, "Main Window Always on Top", 'main_on_top')
        self.dig_tool.param_vars['main_on_top'].trace_add('write', lambda *args: toggle_main_on_top(self.dig_tool, *args))
        create_checkbox_param(panes['window'].sub_frame, "Preview Window Always on Top", 'preview_on_top')
        self.dig_tool.param_vars['preview_on_top'].trace_add('write', lambda *args: toggle_preview_on_top(self.dig_tool))
        create_checkbox_param(panes['window'].sub_frame, "Debug Window Always on Top", 'debug_on_top')
        self.dig_tool.param_vars['debug_on_top'].trace_add('write', lambda *args: toggle_debug_on_top(self.dig_tool))

        create_checkbox_param(panes['debug'].sub_frame, "Save Debug Screenshots", 'debug_enabled')
        create_param_entry(panes['debug'].sub_frame, "Screenshot FPS:", 'screenshot_fps')
        create_section_button(panes['debug'].sub_frame, "Show Debug Console", lambda: show_debug_console(self.dig_tool))

        create_section_button(panes['debug'].sub_frame, "Color Modules Overlay", 
                             lambda: toggle_color_modules_overlay(self.dig_tool))

        def create_hotkey_setter(parent, text, key_name):
            frame = Frame(parent, bg=parent.cget('bg'))
            frame.pack(fill='x', pady=BUTTON_PADY, padx=PARAM_PADX)

            label = Label(frame, text=text, font=(FONT_FAMILY, 9), bg=parent.cget('bg'), fg=TEXT_COLOR, width=22,
                          anchor='w')
            label.pack(side='left')

            tooltip_text = self.dig_tool.settings_manager.get_keybind_description(key_name)
            Tooltip(label, tooltip_text)

            default_value = self.dig_tool.settings_manager.get_default_keybind(key_name)
            
            if key_name not in self.dig_tool.keybind_vars:
                self.dig_tool.keybind_vars[key_name] = tk.StringVar(value=default_value)
            
            key_var = self.dig_tool.keybind_vars[key_name]

            def set_hotkey_thread(key_var, button):
                button.config(text="Press any key...", state=tk.DISABLED, bg="#0078D4",
                              fg="#ffffff")
                self.dig_tool.root.update_idletasks()
                try:
                    import keyboard
                    event = keyboard.read_event(suppress=True)
                    if event.event_type == keyboard.KEY_DOWN: 
                        new_key = event.name
                        if new_key and new_key.strip():
                            key_var.set(new_key)
                        else:
                            key_var.set(default_value)
                except Exception as e:
                    self.dig_tool.update_status(f"Hotkey capture failed: {e}")
                    key_var.set(default_value)
                finally:
                    current_key = key_var.get()
                    if not current_key or current_key.strip() == "":
                        key_var.set(default_value)
                    button.config(text=key_var.get().upper(), state=tk.NORMAL, bg=BTN_BG, fg=TEXT_COLOR)
                    apply_keybinds(self.dig_tool)

            hotkey_btn = Button(frame, text=key_var.get().upper(), font=(FONT_FAMILY, 9, 'bold'), bg=BTN_BG,
                                fg=TEXT_COLOR, relief='solid', borderwidth=1, width=12, pady=4)
            hotkey_btn.config(command=lambda v=key_var, b=hotkey_btn:
            __import__('threading').Thread(target=set_hotkey_thread, args=(v, b), daemon=True).start())
            hotkey_btn.pack(side='right')

        create_hotkey_setter(panes['hotkeys'].sub_frame, "Toggle Tool:", 'toggle_bot')
        create_hotkey_setter(panes['hotkeys'].sub_frame, "Toggle GUI:", 'toggle_gui')
        create_hotkey_setter(panes['hotkeys'].sub_frame, "Toggle Overlay:", 'toggle_overlay')
        create_hotkey_setter(panes['hotkeys'].sub_frame, "Toggle Auto Walk Overlay:", 'toggle_autowalk_overlay')

        settings_info_frame = Frame(panes['settings'].sub_frame, bg=panes['settings'].sub_frame.cget('bg'))
        settings_info_frame.pack(fill='x', pady=(BUTTON_PADY, 4), padx=PARAM_PADX)
        Button(settings_info_frame, text="Open Dig Tool Folder", command=lambda: show_settings_info(self.dig_tool),
               font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR, relief='solid', borderwidth=1, pady=4).pack(
            expand=True, fill=tk.X)
        Tooltip(settings_info_frame.winfo_children()[0], "Open the Dig Tool folder in Windows Explorer to view settings, debug logs, and other application files.")

        save_load_frame = Frame(panes['settings'].sub_frame, bg=panes['settings'].sub_frame.cget('bg'))
        save_load_frame.pack(fill='x', pady=(BUTTON_PADY, 4), padx=PARAM_PADX)

        Button(save_load_frame, text="Export Settings", command=self.dig_tool.settings_manager.export_settings,
               font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR, relief='solid', borderwidth=1, pady=4).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        Button(save_load_frame, text="Import Settings", command=self.dig_tool.settings_manager.import_settings,
               font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR, relief='solid', borderwidth=1, pady=4).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        reset_frame = Frame(panes['settings'].sub_frame, bg=panes['settings'].sub_frame.cget('bg'))
        reset_frame.pack(fill='x', pady=(4, BUTTON_PADY), padx=PARAM_PADX)
        Button(reset_frame, text="Reset to Defaults", command=self.dig_tool.settings_manager.reset_to_defaults,
               font=(FONT_FAMILY, 9), bg=BTN_BG, fg=TEXT_COLOR, relief='solid', borderwidth=1, pady=4).pack(expand=True,
                                                                                                            fill=tk.X)

        self.dig_tool.param_vars['auto_walk_enabled'].trace_add('write', self.update_dependent_widgets_state)
        self.dig_tool.param_vars['auto_shovel_enabled'].trace_add('write', self.update_dependent_widgets_state)
        self.dig_tool.param_vars['auto_sell_enabled'].trace_add('write', self.update_dependent_widgets_state)
        self.dig_tool.param_vars['use_custom_cursor'].trace_add('write', self.update_dependent_widgets_state)
        self.dig_tool.param_vars['use_otsu_detection'].trace_add('write', self.update_dependent_widgets_state)
        self.dig_tool.param_vars['use_color_picker_detection'].trace_add('write', self.update_dependent_widgets_state)
        self.dig_tool.param_vars['velocity_based_width_enabled'].trace_add('write', self.update_dependent_widgets_state)
        self.dig_tool.param_vars['auto_sell_target_engagement_enabled'].trace_add('write', self.update_dependent_widgets_state)
        self.dig_tool.param_vars['dynamic_walkspeed_enabled'].trace_add('write', self.update_dependent_widgets_state)

        self._prev_auto_walk_enabled = self.dig_tool.param_vars.get('auto_walk_enabled', tk.BooleanVar()).get()
        
        self.update_dependent_widgets_state()
        
        from utils.ui_management import update_main_button_text
        update_main_button_text(self.dig_tool)
        toggle_main_on_top(self.dig_tool)
        self.update_status_with_area_indicator()
        
        self.setup_drag_drop()

    def update_status_with_area_indicator(self):
        if hasattr(self.dig_tool, 'game_area') and self.dig_tool.game_area:
            base_status = "Game area set. Press Start to begin."
            if hasattr(self.dig_tool, 'game_area_indicator'):
                self.dig_tool.game_area_indicator.config(text="✓ Game Area: Set", fg="#00aa00")
        else:
            base_status = "Select a game area to begin."
            if hasattr(self.dig_tool, 'game_area_indicator'):
                self.dig_tool.game_area_indicator.config(text="✗ Game Area: Not Set", fg="#cc0000")
        
        self.dig_tool.update_status(base_status)
    
    def setup_drag_drop(self):
        if not DND_AVAILABLE:
            logger.info("tkinterdnd2 not available, drag and drop disabled")
            return
            
        try:
            self.dig_tool.root.drop_target_register(DND_FILES)
            self.dig_tool.root.dnd_bind('<<Drop>>', self.on_drop)
            logger.info("Drag and drop functionality enabled")
        except Exception as e:
            logger.warning(f"Could not set up drag and drop: {e}")
    
    def on_drop(self, event):
        try:
            file_data = event.data.strip()
            
            if file_data.startswith('{') and file_data.endswith('}'):
                file_path = file_data.strip('{}')
            else:
                if file_data.startswith('"') and '"' in file_data[1:]:
                    end_quote = file_data.find('"', 1)
                    file_path = file_data[1:end_quote]
                elif ' ' in file_data and not os.path.exists(file_data):
                    words = file_data.split()
                    for i in range(1, len(words) + 1):
                        potential_path = ' '.join(words[:i])
                        if os.path.exists(potential_path):
                            file_path = potential_path
                            break
                    else:
                        file_path = file_data
                else:
                    file_path = file_data
            
            if not file_path:
                self.dig_tool.update_status("Error: No file path found in drag and drop data")
                return
            
            if not file_path.lower().endswith('.json'):
                self.dig_tool.update_status("Error: Only JSON files are supported for drag and drop")
                return
  
            if not os.path.exists(file_path):
                self.dig_tool.update_status("Error: Dropped file does not exist")
                return
            
            try:
                with open(file_path, 'r') as f:
                    settings_data = json.load(f)
                
                if not isinstance(settings_data, dict):
                    self.dig_tool.update_status("Error: Invalid settings file format")
                    return
                
                if hasattr(self.dig_tool, 'settings_manager'):
                    self.dig_tool.settings_manager.import_settings_from_file(file_path)
                else:
                    self.dig_tool.update_status("Error: Settings manager not available")
                    
            except json.JSONDecodeError:
                self.dig_tool.update_status("Error: Invalid JSON file")
            except Exception as e:
                self.dig_tool.update_status(f"Error importing settings: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in drag and drop handler: {e}")
            self.dig_tool.update_status("Error: Failed to process dropped file")


def update_area_info(dig_tool_instance):
    if hasattr(dig_tool_instance, 'main_window') and hasattr(dig_tool_instance.main_window, 'update_status_with_area_indicator'):
        dig_tool_instance.main_window.update_status_with_area_indicator()
    if hasattr(dig_tool_instance, 'main_window') and hasattr(dig_tool_instance.main_window, 'update_dependent_widgets_state'):
        dig_tool_instance.main_window.update_dependent_widgets_state()
