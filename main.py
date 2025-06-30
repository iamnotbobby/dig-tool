import warnings
import os

from utils.system_utils import check_dependencies

check_dependencies()

try:
    import ctypes

    PROCESS_PER_MONITOR_DPI_AWARE = 2
    ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
except:
    pass

import cv2
import numpy as np
import tkinter as tk
from tkinter import Label, Frame, TclError
import threading
import time
from PIL import Image, ImageTk
import keyboard
import queue

from interface.components import GameOverlay
from interface.main_window import MainWindow
from interface.settings import SettingsManager
from utils.screen_capture import ScreenCapture
from utils.system_utils import send_click, check_display_scale
from core.detection import find_line_position, VelocityCalculator
from core.automation import AutomationManager
from core.notifications import DiscordNotifier

warnings.filterwarnings("ignore")
check_display_scale()


class DigTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dig Tool")

        try:
            if os.path.exists("assets/icon.ico"):
                self.root.wm_iconbitmap("assets/icon.ico")
        except:
            pass

        self.base_height = 570
        self.width = 450
        self.root.geometry(f"{self.width}x{self.base_height}")
        self.root.minsize(self.width, self.base_height)

        self.param_vars = {}
        self.keybind_vars = {}
        self.last_known_good_params = {}

        self.settings_manager = SettingsManager(self)
        self.automation_manager = AutomationManager(self)
        self.discord_notifier = DiscordNotifier()
        self.main_window = MainWindow(self)

        self.game_area = None
        self.cursor_position = None
        self.running = False
        self.preview_active = True
        self.overlay = None
        self.overlay_enabled = False
        self.overlay_position = None
        self.screen_grabber = ScreenCapture()
        self.click_count = 0
        self.dig_count = 0
        self.click_lock = threading.Lock()
        self.velocity_calculator = VelocityCalculator()
        self.blind_until = 0
        self.frames_since_last_zone_detection = 0
        self.smoothed_zone_x = None
        self.smoothed_zone_w = None
        self.is_color_locked = False
        self.locked_color_hsv = None
        self.locked_color_hex = None
        self.is_low_sat_lock = False
        self.preview_window = None
        self.debug_window = None
        self.preview_label = None
        self.debug_label = None
        self.color_swatch_label = None
        self.main_loop_thread = None
        self.hotkey_thread = None
        self.results_queue = queue.Queue(maxsize=1)
        self.debug_dir = "debug_clicks"
        self.debug_log_path = os.path.join(self.debug_dir, "click_log.txt")

        self.last_milestone_notification = 0
        self.milestone_interval = 100

        self.main_window.create_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(50, self.update_gui_from_queue)

    def ensure_debug_dir(self):
        if self.get_param('debug_clicks_enabled') and not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)

    def on_closing(self):
        if self.running:
            try:
                webhook_url = self.param_vars.get('webhook_url', tk.StringVar()).get()
                user_id = self.param_vars.get('user_id', tk.StringVar()).get()
                if webhook_url:
                    self.discord_notifier.set_webhook_url(webhook_url)
                    self.discord_notifier.send_shutdown_notification(user_id if user_id else None)
            except:
                pass

        self.preview_active = False
        self.running = False
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.update_status("Shutting down...")
        self.root.after(100, self._check_shutdown)

    def _check_shutdown(self):
        hotkey_alive = self.hotkey_thread and self.hotkey_thread.is_alive()
        main_loop_alive = self.main_loop_thread and self.main_loop_thread.is_alive()
        if hotkey_alive or main_loop_alive:
            self.root.after(100, self._check_shutdown)
        else:
            try:
                keyboard.unhook_all()
                self.screen_grabber.close()
            except Exception as e:
                print(f"Error during final cleanup: {e}")
            finally:
                self.root.destroy()

    def start_threads(self):
        if self.hotkey_thread is None:
            self.hotkey_thread = threading.Thread(target=self.hotkey_listener, daemon=True)
            self.hotkey_thread.start()
        if self.main_loop_thread is None:
            self.main_loop_thread = threading.Thread(target=self.run_main_loop, daemon=True)
            self.main_loop_thread.start()

    def hotkey_listener(self):
        self.root.after(0, self.apply_keybinds)
        while self.preview_active:
            time.sleep(0.5)

    def apply_keybinds(self):
        keyboard.unhook_all()
        try:
            keyboard.add_hotkey(self.keybind_vars['toggle_bot'].get(), self.toggle_detection)
            keyboard.add_hotkey(self.keybind_vars['toggle_gui'].get(), self.toggle_gui)
            keyboard.add_hotkey(self.keybind_vars['toggle_overlay'].get(), self.toggle_overlay)
            keyboard.add_hotkey(self.keybind_vars['toggle_auto_walk'].get(), self.toggle_auto_walk)
            keyboard.add_hotkey(self.keybind_vars['toggle_auto_sell'].get(), self.toggle_auto_sell)
            keyboard.add_hotkey(self.keybind_vars['panic_key'].get(), self.panic)
            self.update_main_button_text()
            self.update_status("Keybinds applied successfully.")
        except (ValueError, TclError, Exception) as e:
            self.update_status(f"Error: Invalid keybind - {e}")
            self.update_main_button_text()

    def toggle_gui(self):
        self.root.after(0, self._toggle_gui_thread_safe)

    def _toggle_gui_thread_safe(self):
        if self.root.winfo_exists():
            if self.root.state() == 'normal':
                self.root.withdraw()
            else:
                self.root.deiconify()
                self.root.lift()

    def toggle_overlay(self):
        self.root.after(0, self._toggle_overlay_thread_safe)

    def _toggle_overlay_thread_safe(self):
        if not self.overlay_enabled:
            if not self.game_area: self.update_status("Select game area first"); return
            self.overlay = GameOverlay(self)
            self.overlay.create_overlay()
            self.overlay_enabled = True
        else:
            if self.overlay:
                self.overlay.destroy_overlay()
            self.overlay = None
            self.overlay_enabled = False
        self.update_main_button_text()

    def toggle_auto_walk(self):
        self.root.after(0, self._toggle_auto_walk_thread_safe)

    def _toggle_auto_walk_thread_safe(self):
        current_state = self.param_vars['auto_walk_enabled'].get()
        self.param_vars['auto_walk_enabled'].set(not current_state)
        self.update_status(f"Auto-walk {'enabled' if not current_state else 'disabled'}")

    def toggle_auto_sell(self):
        self.root.after(0, self._toggle_auto_sell_thread_safe)

    def _toggle_auto_sell_thread_safe(self):
        current_state = self.param_vars['auto_sell_enabled'].get()
        self.param_vars['auto_sell_enabled'].set(not current_state)
        self.update_status(f"Auto-sell {'enabled' if not current_state else 'disabled'}")

    def panic(self):
        self.root.after(0, self.on_closing)

    def get_param(self, key):
        return self.settings_manager.get_param(key)

    def update_main_button_text(self):
        if not self.root.winfo_exists(): return
        try:
            current_state = "Stop" if self.running else "Start"
            self.start_stop_btn.config(text=f"{current_state} ({self.keybind_vars['toggle_bot'].get().upper()})")
            self.toggle_gui_btn.config(text=f"Show/Hide ({self.keybind_vars['toggle_gui'].get().upper()})")
            overlay_status = "ON" if self.overlay_enabled else "OFF"
            self.overlay_btn.config(
                text=f"Overlay: {overlay_status} ({self.keybind_vars['toggle_overlay'].get().upper()})")
        except (TclError, AttributeError):
            pass

    def resize_for_content(self):
        self.root.update_idletasks()
        open_pane = next((p for p in self.accordion.panes if p.is_open.get()), None)
        content_height = open_pane.sub_frame.winfo_reqheight() if open_pane else 0
        new_height = self.base_height + content_height + (10 if open_pane else 0)
        self.root.geometry(f"{self.width}x{new_height}")

    def update_area_info(self):
        if self.game_area:
            x1, y1, x2, y2 = self.game_area
            width, height = x2 - x1, y2 - y1
            area_text = f"Game Area: {width}x{height} at ({x1}, {y1})"
        else:
            area_text = "Game Area: Not set"
        self.area_info_label.config(text=area_text)

    def update_sell_info(self):
        if self.automation_manager.sell_button_position:
            x, y = self.automation_manager.sell_button_position
            sell_text = f"Sell Button: Set at ({x}, {y})"
        else:
            sell_text = "Sell Button: Not set"
        self.sell_info_label.config(text=sell_text)

    def update_cursor_info(self):
        if hasattr(self, 'cursor_position') and self.cursor_position:
            x, y = self.cursor_position
            cursor_text = f"Cursor Position: Set at ({x}, {y})"
        else:
            cursor_text = "Cursor Position: Not set"
        self.cursor_info_label.config(text=cursor_text)

    def start_area_selection(self):
        self.root.iconify()
        self.selection_overlay = tk.Toplevel()
        self.selection_overlay.attributes('-fullscreen', True, '-alpha', 0.2, '-topmost', True)
        self.selection_overlay.configure(bg='blue', cursor='crosshair')
        self.selection_rect = tk.Frame(self.selection_overlay, bg='red', highlightthickness=1,
                                       highlightbackground='white')
        self.selection_overlay.bind('<Button-1>', self.on_drag_start)
        self.selection_overlay.bind('<B1-Motion>', self.on_drag_motion)
        self.selection_overlay.bind('<ButtonRelease-1>', self.on_drag_end)

    def on_drag_start(self, event):
        self.drag_start = (event.x_root, event.y_root)
        self.selection_rect.place(x=event.x, y=event.y, width=1, height=1)

    def on_drag_motion(self, event):
        x1, y1 = self.drag_start;
        x2, y2 = event.x_root, event.y_root
        x, y = self.selection_overlay.winfo_rootx(), self.selection_overlay.winfo_rooty()
        self.selection_rect.place(x=min(x1, x2) - x, y=min(y1, y2) - y, width=abs(x1 - x2), height=abs(y1 - y2))

    def on_drag_end(self, event):
        x1, y1 = self.drag_start;
        x2, y2 = event.x_root, event.y_root
        self.game_area = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        self.selection_overlay.destroy()
        self.root.deiconify()
        self.update_status("Game area set. Press Start to begin.")
        self.preview_btn.config(state=tk.NORMAL)
        self.debug_btn.config(state=tk.NORMAL)
        self.update_area_info()
        self.start_threads()

    def start_sell_button_selection(self):
        self.root.iconify()
        self.sell_selection_overlay = tk.Toplevel()
        self.sell_selection_overlay.attributes('-fullscreen', True, '-alpha', 0.3, '-topmost', True)
        self.sell_selection_overlay.configure(bg='red', cursor='crosshair')

        instruction_label = Label(self.sell_selection_overlay,
                                  text="FIRST: Press 'G' to open your inventory\nTHEN: Click on the SELL BUTTON",
                                  font=("Arial", 20, "bold"), bg='red', fg='white')
        instruction_label.pack(pady=100)

        self.sell_selection_overlay.bind('<Button-1>', self.on_sell_button_click)

    def on_sell_button_click(self, event):
        self.automation_manager.sell_button_position = (event.x_root, event.y_root)
        self.sell_selection_overlay.destroy()
        self.root.deiconify()
        self.update_status(f"Sell button set at ({event.x_root}, {event.y_root})")
        self.update_sell_info()

    def start_cursor_position_selection(self):
        self.root.iconify()
        self.cursor_selection_overlay = tk.Toplevel()
        self.cursor_selection_overlay.attributes('-fullscreen', True, '-alpha', 0.3, '-topmost', True)
        self.cursor_selection_overlay.configure(bg='blue', cursor='crosshair')

        instruction_label = Label(self.cursor_selection_overlay,
                                  text="Click to set cursor position for clicking",
                                  font=("Arial", 20, "bold"), bg='blue', fg='white')
        instruction_label.pack(pady=100)

        self.cursor_selection_overlay.bind('<Button-1>', self.on_cursor_position_click)

    def on_cursor_position_click(self, event):
        self.cursor_position = (event.x_root, event.y_root)
        self.cursor_selection_overlay.destroy()
        self.root.deiconify()
        self.update_status(f"Cursor position set at ({event.x_root}, {event.y_root})")
        self.update_cursor_info()

    def test_sell_button_click(self):
        """Delegate to AutomationManager's test method"""
        self.automation_manager.test_sell_button_click()

    def test_discord_ping(self):
        try:
            webhook_url = self.param_vars.get('webhook_url', tk.StringVar()).get()
            user_id = self.param_vars.get('user_id', tk.StringVar()).get()

            if not webhook_url:
                self.update_status("Webhook URL not set!")
                return

            self.update_status("Testing Discord ping...")
            self.discord_notifier.set_webhook_url(webhook_url)

            success = self.discord_notifier.test_webhook(user_id if user_id else None)

            if success:
                self.update_status("Discord ping test completed successfully!")
            else:
                self.update_status("Discord ping test failed!")

        except Exception as e:
            self.update_status(f"Discord ping test error: {e}")

    def check_milestone_notifications(self):
        try:
            webhook_url = self.param_vars.get('webhook_url', tk.StringVar()).get()
            user_id = self.param_vars.get('user_id', tk.StringVar()).get()
            milestone_interval = self.param_vars.get('milestone_interval', tk.IntVar()).get()

            if not webhook_url or milestone_interval <= 0:
                return

            if (self.dig_count > 0 and
                    self.dig_count % milestone_interval == 0 and
                    self.dig_count != self.last_milestone_notification):
                self.discord_notifier.set_webhook_url(webhook_url)
                self.discord_notifier.send_milestone_notification(
                    self.dig_count,
                    self.click_count,
                    user_id if user_id else None
                )
                self.last_milestone_notification = self.dig_count

        except Exception as e:
            print(f"Error sending milestone notification: {e}")

    def toggle_main_on_top(self, *args):
        self.root.attributes('-topmost', self.param_vars['main_on_top'].get())

    def toggle_preview_on_top(self, *args):
        if self.preview_window: self.preview_window.attributes('-topmost', self.param_vars['preview_on_top'].get())

    def toggle_debug_on_top(self, *args):
        if self.debug_window: self.debug_window.attributes('-topmost', self.param_vars['debug_on_top'].get())

    def toggle_preview_window(self):
        if self.preview_window is None:
            self.preview_window = tk.Toplevel(self.root)
            self.preview_window.title("Live Preview")
            self.preview_window.geometry("800x200")

            try:
                if os.path.exists("assets/icon.ico"):
                    self.preview_window.wm_iconbitmap("assets/icon.ico")
            except:
                pass

            self.preview_label = Label(self.preview_window, bg='black')
            self.preview_label.pack(fill=tk.BOTH, expand=True)
            self.preview_window.protocol("WM_DELETE_WINDOW", self.toggle_preview_window)
            self.toggle_preview_on_top()
        else:
            self.preview_window.destroy()
            self.preview_window = None
            self.preview_label = None

    def toggle_debug_window(self):
        if self.debug_window is None:
            self.debug_window = tk.Toplevel(self.root)
            self.debug_window.title("Debug Mask")
            self.debug_window.geometry("800x230")
            self.debug_window.configure(bg='black')

            try:
                if os.path.exists("assets/icon.ico"):
                    self.debug_window.wm_iconbitmap("assets/icon.ico")
            except:
                pass

            self.debug_label = Label(self.debug_window, bg='black')
            self.debug_label.pack(fill=tk.BOTH, expand=True)
            color_frame = Frame(self.debug_window, bg='black', pady=5)
            Label(color_frame, text="Locked Color:", font=("Segoe UI", 9), bg='black', fg='white').pack(side='left',
                                                                                                        padx=5)
            self.color_swatch_label = Label(color_frame, text="", bg='black', relief='solid', bd=1, width=15)
            self.color_swatch_label.pack(side='left', ipady=5, padx=5)
            color_frame.pack(fill='x')
            self.debug_window.protocol("WM_DELETE_WINDOW", self.toggle_debug_window)
            self.toggle_debug_on_top()
        else:
            self.debug_window.destroy()
            self.debug_window = None
            self.debug_label = None
            self.color_swatch_label = None

    def update_gui_from_queue(self):
        try:
            preview_array, debug_mask, overlay_info = self.results_queue.get_nowait()
            if self.preview_window and self.preview_label:
                pw, ph = self.preview_label.winfo_width(), self.preview_label.winfo_height()
                if pw > 20 and ph > 20:
                    img = Image.fromarray(cv2.cvtColor(preview_array, cv2.COLOR_BGR2RGB))
                    img.thumbnail((pw, ph), Image.Resampling.NEAREST)
                    photo = ImageTk.PhotoImage(image=img)
                    self.preview_label.configure(image=photo)
                    self.preview_label.image = photo
            if self.debug_window and self.debug_label and debug_mask is not None:
                dw, dh = self.debug_label.winfo_width(), self.debug_label.winfo_height()
                if dw > 20 and dh > 20:
                    debug_bgr = cv2.cvtColor(debug_mask, cv2.COLOR_GRAY2BGR)
                    debug_img = Image.fromarray(cv2.cvtColor(debug_bgr, cv2.COLOR_BGR2RGB))
                    debug_img.thumbnail((dw, dh), Image.Resampling.NEAREST)
                    debug_photo = ImageTk.PhotoImage(image=debug_img)
                    self.debug_label.configure(image=debug_photo)
                    self.debug_label.image = debug_photo
            locked_color = overlay_info.get('locked_color_hex')
            if self.color_swatch_label:
                self.color_swatch_label.config(bg=locked_color if locked_color else '#000000')
            if self.overlay_enabled and self.overlay: self.overlay.update_info(**overlay_info)
        except (queue.Empty, RuntimeError, TclError):
            pass
        finally:
            if self.preview_active:
                self.root.after(50, self.update_gui_from_queue)

    def toggle_detection(self):
        self.root.after(0, self._toggle_detection_thread_safe)

    def _toggle_detection_thread_safe(self):
        if not self.running:
            if not self.game_area: self.update_status("Select game area first"); return

            self.running = True
            self.update_status("Bot Started...")
            self.click_count = 0
            self.dig_count = 0
            self.velocity_calculator = VelocityCalculator()
            self.automation_manager.walk_pattern_index = 0
            if self.get_param('debug_clicks_enabled'):
                self.init_debug_log()
            if self.click_lock.locked(): self.click_lock.release()

            try:
                webhook_url = self.param_vars.get('webhook_url', tk.StringVar()).get()
                user_id = self.param_vars.get('user_id', tk.StringVar()).get()
                if webhook_url:
                    self.discord_notifier.set_webhook_url(webhook_url)
                    self.discord_notifier.send_startup_notification(user_id if user_id else None)
            except:
                pass

        else:
            self.running = False
            self.update_status("Stopped")

            try:
                webhook_url = self.param_vars.get('webhook_url', tk.StringVar()).get()
                user_id = self.param_vars.get('user_id', tk.StringVar()).get()
                if webhook_url:
                    self.discord_notifier.set_webhook_url(webhook_url)
                    self.discord_notifier.send_shutdown_notification(user_id if user_id else None)
            except:
                pass

        self.update_main_button_text()

    def init_debug_log(self):
        try:
            self.ensure_debug_dir()
            with open(self.debug_log_path, 'w') as f:
                f.write("Dig Tool Debug Log\n")
                f.write("==================\n")
                f.write(f"Session started at timestamp: {int(time.time())}\n")
                f.write(
                    "Format: Click# | Timestamp | Line_Pos | Velocity | Acceleration | Sweet_Spot_Range | Click_Type | Confidence | Screenshot_File\n")
                f.write("-" * 120 + "\n")
        except Exception as e:
            print(f"Error creating debug log: {e}")

    def log_click_debug(self, click_num, line_pos, velocity, acceleration, sweet_spot_start, sweet_spot_end,
                        prediction_used, confidence, screenshot_filename):
        if not self.get_param('debug_clicks_enabled'):
            return
        try:
            timestamp = int(time.time())
            click_type = "PREDICTION" if prediction_used else "DIRECT"
            if sweet_spot_start is not None and sweet_spot_end is not None:
                sweet_spot_range = f"{int(sweet_spot_start)}-{int(sweet_spot_end)}"
            else:
                sweet_spot_range = "N/A"

            log_entry = f"{click_num:03d} | {timestamp} | {line_pos:4d} | {velocity:6.1f} | {acceleration:6.1f} | {sweet_spot_range:>10} | {click_type:>10} | {confidence:4.2f} | {screenshot_filename}\n"

            with open(self.debug_log_path, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error logging click debug: {e}")

    def update_status(self, text):
        if self.root.winfo_exists():
            self.status_label.config(text=f"Status: {text}")

    def perform_click(self, delay=0):
        if delay > 0: time.sleep(delay)
        if not self.running:
            self.click_lock.release()
            return

        if self.get_param('use_custom_cursor') and self.cursor_position:
            try:
                current_pos = self.cursor_position
                ctypes.windll.user32.SetCursorPos(*current_pos)
                time.sleep(0.01)
            except Exception as e:
                print(f"Error setting cursor position: {e}")

        send_click()
        self.last_click_time = time.time() * 1000
        self.click_count += 1
        self.click_lock.release()

    def save_debug_screenshot(self, screenshot, line_pos, sweet_spot_start, sweet_spot_end, zone_y2_cached, velocity,
                              acceleration, prediction_used=False, confidence=0.0):
        if not self.get_param('debug_clicks_enabled'):
            return

        try:
            self.ensure_debug_dir()
            debug_img = screenshot.copy()
            height = debug_img.shape[0]

            if self.smoothed_zone_x is not None:
                cv2.rectangle(debug_img, (int(self.smoothed_zone_x), 0),
                              (int(self.smoothed_zone_x + self.smoothed_zone_w), zone_y2_cached), (0, 255, 0), 3)

            if sweet_spot_start is not None and sweet_spot_end is not None:
                cv2.rectangle(debug_img, (int(sweet_spot_start), 0), (int(sweet_spot_end), zone_y2_cached),
                              (0, 255, 255), 3)

            if line_pos != -1:
                cv2.line(debug_img, (line_pos, 0), (line_pos, height), (0, 0, 255), 4)

            filename = f"click_{self.click_count + 1:03d}_{int(time.time())}.jpg"
            filepath = os.path.join(self.debug_dir, filename)
            cv2.imwrite(filepath, debug_img)

            self.log_click_debug(self.click_count + 1, line_pos, velocity, acceleration, sweet_spot_start,
                                 sweet_spot_end,
                                 prediction_used, confidence, filename)
        except Exception as e:
            print(f"Error saving debug screenshot: {e}")

    def run_main_loop(self):
        target_fps = 120
        target_delay = 1.0 / target_fps
        final_mask = None
        height_80_cached = None
        zone_y2_cached = None
        kernel = np.ones((5, 15), np.uint8)

        auto_walk_state = "move"
        move_completed_time = 0
        wait_for_target_start = 0
        dig_completed_time = 0
        max_wait_time = 3000
        post_dig_delay = 2000

        while self.preview_active:
            start_time = time.perf_counter()
            current_time_ms = time.time() * 1000

            if self.game_area is None:
                time.sleep(target_delay)
                continue

            screenshot = self.screen_grabber.capture(bbox=self.game_area)
            if screenshot is None:
                time.sleep(target_delay)
                continue

            height, width = screenshot.shape[:2]
            if height_80_cached is None or height_80_cached != int(height * 0.80):
                height_80_cached = int(height * 0.80)
                zone_y2_cached = height_80_cached

            zone_detection_area = screenshot[:height_80_cached, :]
            hsv = cv2.cvtColor(zone_detection_area, cv2.COLOR_BGR2HSV)

            if not self.is_color_locked:
                saturation = hsv[:, :, 1]
                _, final_mask = cv2.threshold(saturation, self.get_param('saturation_threshold'), 255,
                                              cv2.THRESH_BINARY)
            elif self.is_low_sat_lock:
                hsv_color = self.locked_color_hsv
                v_range = 40
                lower_bound = np.array([0, 0, max(0, hsv_color[2] - v_range)], dtype=np.uint8)
                upper_bound = np.array([179, 50, min(255, hsv_color[2] + v_range)], dtype=np.uint8)
                final_mask = cv2.inRange(hsv, lower_bound, upper_bound)
            else:
                hsv_color = self.locked_color_hsv
                h_range, s_range, v_range = 10, 70, 70
                lower_bound = np.array(
                    [max(0, hsv_color[0] - h_range), max(0, hsv_color[1] - s_range), max(0, hsv_color[2] - v_range)],
                    dtype=np.uint8)
                upper_bound = np.array([min(179, hsv_color[0] + h_range), min(255, hsv_color[1] + s_range),
                                        min(255, hsv_color[2] + v_range)], dtype=np.uint8)
                final_mask = cv2.inRange(hsv, lower_bound, upper_bound)

            final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            raw_zone_x, raw_zone_w = None, None
            if contours:
                main_contour = max(contours, key=cv2.contourArea)
                x_temp, y_temp, w_temp, h_temp = cv2.boundingRect(main_contour)
                zone_min_width = self.get_param('zone_min_width')
                max_zone_width = width * (self.get_param('max_zone_width_percent') / 100.0)
                min_zone_height = height_80_cached * (self.get_param('min_zone_height_percent') / 100.0)

                if w_temp > zone_min_width and w_temp < max_zone_width and h_temp >= min_zone_height:
                    raw_zone_x, raw_zone_w = x_temp, w_temp
                    if not self.is_color_locked:
                        mask = np.zeros(hsv.shape[:2], dtype="uint8")
                        cv2.drawContours(mask, [main_contour], -1, 255, -1)
                        mean_hsv = cv2.mean(hsv, mask=mask)
                        self.locked_color_hsv = mean_hsv[:3]
                        self.is_color_locked = True
                        bgr_color = cv2.cvtColor(np.uint8([[self.locked_color_hsv]]), cv2.COLOR_HSV2BGR)[0][0]
                        self.locked_color_hex = f'#{bgr_color[2]:02x}{bgr_color[1]:02x}{bgr_color[0]:02x}'
                        self.is_low_sat_lock = self.locked_color_hsv[1] < 25

            if raw_zone_x is not None:
                self.frames_since_last_zone_detection = 0
                smoothing_factor = self.get_param('zone_smoothing_factor')
                if self.smoothed_zone_x is None:
                    self.smoothed_zone_x, self.smoothed_zone_w = raw_zone_x, raw_zone_w
                else:
                    self.smoothed_zone_x = smoothing_factor * raw_zone_x + (1 - smoothing_factor) * self.smoothed_zone_x
                    self.smoothed_zone_w = smoothing_factor * raw_zone_w + (1 - smoothing_factor) * self.smoothed_zone_w
            else:
                self.frames_since_last_zone_detection += 1

            if self.frames_since_last_zone_detection > 20:
                self.is_color_locked = False
                self.locked_color_hsv = None
                self.locked_color_hex = None
                self.smoothed_zone_x = None

            gray_line_area = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            line_pos = find_line_position(gray_line_area, self.get_param('line_sensitivity'),
                                          self.get_param('line_min_height') / 100.0)

            current_time = time.time()
            velocity = self.velocity_calculator.add_position(line_pos, current_time)
            acceleration = self.velocity_calculator.get_acceleration()

            sweet_spot_center, sweet_spot_start, sweet_spot_end = None, None, None
            if self.smoothed_zone_x is not None:
                sweet_spot_center = self.smoothed_zone_x + self.smoothed_zone_w / 2
                sweet_spot_width = self.smoothed_zone_w * (self.get_param('sweet_spot_width_percent') / 100.0)
                sweet_spot_start = sweet_spot_center - sweet_spot_width / 2
                sweet_spot_end = sweet_spot_center + sweet_spot_width / 2

            if self.running and self.get_param('auto_walk_enabled') and not self.automation_manager.is_selling:

                if auto_walk_state == "move":
                    if (self.get_param('auto_sell_enabled') and self.automation_manager.sell_button_position and
                            self.dig_count > 0 and self.dig_count % self.get_param('sell_every_x_digs') == 0 and
                            dig_completed_time > 0 and current_time_ms - dig_completed_time >= post_dig_delay):
                        threading.Thread(target=self.automation_manager.perform_auto_sell, daemon=True).start()
                        dig_completed_time = 0
                        while self.automation_manager.is_selling and self.running:
                            time.sleep(0.1)

                    if not self.automation_manager.is_selling:
                        direction = self.automation_manager.get_next_walk_direction()
                        threading.Thread(target=self.automation_manager.perform_walk_step, args=(direction,),
                                         daemon=True).start()

                        auto_walk_state = "click_to_start"
                        move_completed_time = current_time_ms + self.get_param('walk_duration') + 300

                elif auto_walk_state == "click_to_start" and current_time_ms >= move_completed_time and not self.automation_manager.is_selling:
                    if not self.click_lock.locked():
                        self.click_lock.acquire()
                        threading.Thread(target=self.perform_click, args=(0,)).start()
                        auto_walk_state = "wait_for_target"
                        wait_for_target_start = current_time_ms

                elif auto_walk_state == "wait_for_target" and not self.automation_manager.is_selling:
                    if raw_zone_x is not None and sweet_spot_center is not None:
                        auto_walk_state = "digging"
                    elif current_time_ms - wait_for_target_start > max_wait_time:
                        auto_walk_state = "move"

                elif auto_walk_state == "digging":
                    pass

            should_allow_clicking = True
            if self.get_param('auto_walk_enabled'):
                should_allow_clicking = auto_walk_state == "digging" and not self.automation_manager.is_selling

            if (self.running and should_allow_clicking and current_time_ms >= self.blind_until and
                    sweet_spot_center is not None and not self.click_lock.locked()):

                should_click, click_delay, prediction_used, confidence = False, 0, False, 0.0

                line_in_sweet_spot = sweet_spot_start <= line_pos <= sweet_spot_end

                if self.get_param('prediction_enabled') and line_pos != -1:
                    min_velocity = self.get_param('min_velocity_threshold')
                    confidence_threshold = self.get_param('prediction_confidence_threshold')

                    if abs(velocity) >= min_velocity:
                        is_moving_towards = (line_pos < sweet_spot_center and velocity > 0) or (
                                line_pos > sweet_spot_center and velocity < 0)

                        if is_moving_towards:
                            max_pred_time = self.get_param('max_prediction_time') / 1000.0
                            predicted_pos = self.velocity_calculator.predict_position(line_pos, sweet_spot_center,
                                                                                      current_time, max_pred_time)

                            distance_to_center = abs(predicted_pos - sweet_spot_center)
                            sweet_spot_radius = (sweet_spot_end - sweet_spot_start) / 2

                            if distance_to_center <= sweet_spot_radius:
                                confidence = max(0.0, 1.0 - (distance_to_center / sweet_spot_radius))

                                if confidence >= confidence_threshold:
                                    dist = sweet_spot_center - line_pos
                                    time_to_arrival = dist / velocity

                                    if 0 < time_to_arrival <= max_pred_time:
                                        sleep_duration = time_to_arrival - (self.get_param('system_latency') / 1000.0)
                                        if sleep_duration > 0:
                                            should_click, click_delay, prediction_used = True, sleep_duration, True

                if not should_click and line_in_sweet_spot:
                    should_click = True
                    confidence = 1.0

                if should_click:
                    if self.get_param('debug_clicks_enabled'):
                        self.save_debug_screenshot(screenshot, line_pos, sweet_spot_start, sweet_spot_end,
                                                   zone_y2_cached,
                                                   velocity, acceleration, prediction_used, confidence)
                    self.blind_until = current_time_ms + self.get_param('post_click_blindness')
                    self.click_lock.acquire()
                    threading.Thread(target=self.perform_click, args=(click_delay,)).start()

            if (self.get_param('auto_walk_enabled') and auto_walk_state == "digging" and
                    raw_zone_x is None and self.frames_since_last_zone_detection > 30):
                self.dig_count += 1
                dig_completed_time = current_time_ms
                auto_walk_state = "move"
                self.check_milestone_notifications()

            if self.results_queue.empty():
                preview_img = screenshot.copy()
                if sweet_spot_center is not None:
                    cv2.rectangle(preview_img, (int(self.smoothed_zone_x), 0),
                                  (int(self.smoothed_zone_x + self.smoothed_zone_w), zone_y2_cached), (0, 255, 0), 2)
                    cv2.rectangle(preview_img, (int(sweet_spot_start), 0), (int(sweet_spot_end), zone_y2_cached),
                                  (0, 255, 255), 2)
                if line_pos != -1:
                    cv2.line(preview_img, (line_pos, 0), (line_pos, height), (0, 0, 255), 3)
                h, w = preview_img.shape[:2]
                thumbnail = cv2.resize(preview_img, (150, int(150 * h / w)), interpolation=cv2.INTER_NEAREST)

                overlay_info = {
                    'sweet_spot_center': sweet_spot_center,
                    'velocity': velocity,
                    'click_count': self.click_count,
                    'locked_color_hex': self.locked_color_hex,
                    'preview_thumbnail': thumbnail,
                    'dig_count': self.dig_count,
                    'automation_status': self.automation_manager.get_current_status(),
                    'sell_count': self.automation_manager.sell_count
                }
                try:
                    self.results_queue.put_nowait((preview_img, final_mask, overlay_info))
                except queue.Full:
                    pass

            elapsed = time.perf_counter() - start_time
            if target_delay > elapsed: time.sleep(target_delay - elapsed)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = DigTool()
    app.run()