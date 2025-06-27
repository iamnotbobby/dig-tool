import sys
import importlib


def check_dependencies():
    required_packages = {
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'PIL': 'Pillow',
        'keyboard': 'keyboard',
        'win32gui': 'pywin32',
        'ahk': 'ahk'
    }
    missing_packages = []
    for module, package in required_packages.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing_packages.append(package)
    if missing_packages:
        print("Missing required packages:")
        for package in missing_packages:
            print(f"  pip install {package}")
        print("\nPlease install the missing packages and try again.")
        sys.exit(1)


check_dependencies()

import cv2
import numpy as np
import tkinter as tk
from tkinter import Label, Button, Frame, Checkbutton, TclError, ttk
import threading
import time
from PIL import Image, ImageTk
import keyboard
import collections
import queue
import warnings
import os

from ui_components import GameOverlay, CollapsiblePane, AccordionManager, Tooltip
from utils import ScreenCapture, send_click
from settings import SettingsManager

warnings.filterwarnings("ignore")


def find_line_position(gray_array, sensitivity_threshold=50, min_height_ratio=0.7):
    height, width = gray_array.shape
    if width < 3:
        return -1
    left_cols = gray_array[:, :-2].astype(np.float32)
    center_cols = gray_array[:, 1:-1].astype(np.float32)
    right_cols = gray_array[:, 2:].astype(np.float32)
    gradients = np.abs(center_cols - left_cols) + np.abs(center_cols - right_cols)
    vertical_sum = np.sum(gradients, axis=0)
    best_x = -1
    max_gradient_sum = -1
    thresh = sensitivity_threshold * height * 0.2
    candidate_indices = np.where(vertical_sum > thresh)[0]
    strong_edge_threshold = sensitivity_threshold * 0.5
    min_pixels = height * min_height_ratio
    for x_idx in candidate_indices:
        x = x_idx + 1
        col_gradients = gradients[:, x_idx]
        if np.sum(col_gradients > strong_edge_threshold) >= min_pixels:
            current_sum = vertical_sum[x_idx]
            if current_sum > max_gradient_sum:
                max_gradient_sum = current_sum
                best_x = x
    return best_x


class VelocityCalculator:
    def __init__(self, history_length=10):
        self.position_history = collections.deque(maxlen=history_length)
        self.velocity_history = collections.deque(maxlen=5)

    def add_position(self, position, timestamp):
        if position == -1:
            return 0
        self.position_history.append((position, timestamp))
        return self.calculate_velocity()

    def calculate_velocity(self):
        if len(self.position_history) < 2:
            return 0

        valid_points = [(pos, t) for pos, t in self.position_history if pos != -1]
        if len(valid_points) < 2:
            return 0

        if len(valid_points) >= 3:
            velocity = self._weighted_velocity(valid_points)
        else:
            pos1, t1 = valid_points[-2]
            pos2, t2 = valid_points[-1]
            dt = t2 - t1
            velocity = (pos2 - pos1) / dt if dt > 0 else 0

        self.velocity_history.append(velocity)
        return self._smooth_velocity()

    def _weighted_velocity(self, points):
        if len(points) < 3:
            return 0

        weights = np.exp(np.linspace(-1, 0, len(points)))
        weights = weights / np.sum(weights)

        velocities = []
        for i in range(1, len(points)):
            pos1, t1 = points[i - 1]
            pos2, t2 = points[i]
            dt = t2 - t1
            if dt > 0:
                velocities.append((pos2 - pos1) / dt)

        if not velocities:
            return 0

        if len(velocities) == 1:
            return velocities[0]

        velocity_weights = weights[-len(velocities):]
        velocity_weights = velocity_weights / np.sum(velocity_weights)

        return np.average(velocities, weights=velocity_weights)

    def _smooth_velocity(self):
        if len(self.velocity_history) == 0:
            return 0
        if len(self.velocity_history) == 1:
            return self.velocity_history[-1]

        weights = np.array([0.1, 0.2, 0.3, 0.4, 0.5])[-len(self.velocity_history):]
        weights = weights / np.sum(weights)

        return np.average(list(self.velocity_history), weights=weights)

    def get_acceleration(self):
        if len(self.velocity_history) < 2:
            return 0

        recent_velocities = list(self.velocity_history)[-3:]
        if len(recent_velocities) < 2:
            return 0

        time_interval = 1.0 / 120.0
        accel = (recent_velocities[-1] - recent_velocities[0]) / (time_interval * (len(recent_velocities) - 1))
        return accel

    def predict_position(self, current_pos, target_pos, current_time, prediction_time):
        if len(self.velocity_history) == 0:
            return current_pos

        velocity = self.velocity_history[-1]
        acceleration = self.get_acceleration()

        predicted_pos = current_pos + (velocity * prediction_time) + (
                    0.5 * acceleration * prediction_time * prediction_time)

        return predicted_pos


class DigTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dig Tool")

        try:
            if os.path.exists("assets/icon.ico"):
                self.root.wm_iconbitmap("assets/icon.ico")
        except:
            pass

        self.base_height = 360
        self.width = 450
        self.root.geometry(f"{self.width}x{self.base_height}")
        self.root.minsize(self.width, self.base_height)

        self.param_vars = {}
        self.keybind_vars = {}
        self.last_known_good_params = {}
        self.settings_manager = SettingsManager(self)

        self.game_area = None
        self.running = False
        self.preview_active = True
        self.overlay = None
        self.overlay_enabled = False
        self.screen_grabber = ScreenCapture()
        self.click_count = 0
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
        if not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)
        self.debug_log_path = os.path.join(self.debug_dir, "click_log.txt")

        self.create_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(50, self.update_gui_from_queue)

    def on_closing(self):
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
            area_text = f"Area: {width}x{height} at ({x1}, {y1})"
        else:
            area_text = "Area: Not set"
        self.area_info_label.config(text=area_text)

    def create_ui(self):
        BG_COLOR = "#f0f0f0"
        FRAME_BG = "#ffffff"
        TEXT_COLOR = "#000000"
        BTN_BG = "#e1e1e1"
        FONT_FAMILY = "Segoe UI"
        self.root.configure(bg=BG_COLOR)
        self.controls_panel = Frame(self.root, bg=BG_COLOR, padx=10, pady=10)
        self.controls_panel.pack(side=tk.TOP, fill=tk.X, expand=False)
        Label(self.controls_panel, text="Dig Tool", font=(FONT_FAMILY, 14, 'bold'), bg=BG_COLOR, fg=TEXT_COLOR).pack(
            pady=(0, 5), anchor='center')
        self.status_label = Label(self.controls_panel, text="Status: Select a game area to begin.",
                                  font=(FONT_FAMILY, 9), bg=BG_COLOR, fg=TEXT_COLOR, wraplength=780, justify='left')
        self.status_label.pack(fill=tk.X, pady=(0, 5), anchor='w')
        self.area_info_label = Label(self.controls_panel, text="Area: Not set", font=(FONT_FAMILY, 8), bg=BG_COLOR,
                                     fg="#666666", wraplength=780, justify='left')
        self.area_info_label.pack(fill=tk.X, pady=(0, 10), anchor='w')
        actions_frame = Frame(self.controls_panel, bg=BG_COLOR)
        actions_frame.pack(fill=tk.X, pady=(0, 5))
        button_style = {'font': (FONT_FAMILY, 9), 'bg': BTN_BG, 'fg': TEXT_COLOR, 'relief': 'solid', 'borderwidth': 1,
                        'pady': 5}
        Button(actions_frame, text="Select Area", command=self.start_area_selection, **button_style).pack(side=tk.LEFT,
                                                                                                          expand=True,
                                                                                                          fill=tk.X,
                                                                                                          padx=(0, 2))
        self.start_stop_btn = Button(actions_frame, text="Start", command=self.toggle_detection, **button_style)
        self.start_stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.toggle_gui_btn = Button(actions_frame, text="Show/Hide", command=self.toggle_gui, **button_style)
        self.toggle_gui_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.overlay_btn = Button(actions_frame, text="Overlay", command=self.toggle_overlay, **button_style)
        self.overlay_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        preview_actions_frame = Frame(self.controls_panel, bg=BG_COLOR)
        preview_actions_frame.pack(fill=tk.X, pady=5)
        self.preview_btn = Button(preview_actions_frame, text="Show Preview", command=self.toggle_preview_window,
                                  state=tk.DISABLED, **button_style)
        self.preview_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        self.debug_btn = Button(preview_actions_frame, text="Show Debug", command=self.toggle_debug_window,
                                state=tk.DISABLED, **button_style)
        self.debug_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        config_frame = Frame(self.controls_panel, bg=BG_COLOR)
        config_frame.pack(fill='x', expand=True, pady=(5, 0))
        style = ttk.Style()
        style.configure("Header.TButton", font=(FONT_FAMILY, 9, 'bold'), background="#dcdcdc", relief="flat")
        style.map("Header.TButton", background=[('active', '#c8c8c8')])
        self.accordion = AccordionManager(self)
        detection_pane = CollapsiblePane(config_frame, text="Detection", manager=self.accordion)
        behavior_pane = CollapsiblePane(config_frame, text="Behavior", manager=self.accordion)
        window_pane = CollapsiblePane(config_frame, text="Window", manager=self.accordion)
        hotkeys_pane = CollapsiblePane(config_frame, text="Hotkeys", manager=self.accordion)
        settings_pane = CollapsiblePane(config_frame, text="Settings", manager=self.accordion)
        for pane in [detection_pane, behavior_pane, window_pane, hotkeys_pane, settings_pane]:
            pane.pack(fill='x', pady=2)
            self.accordion.add_pane(pane)

        def create_param_entry(parent, text, var_key, default_value, var_type=tk.IntVar):
            frame = Frame(parent, bg=FRAME_BG)
            frame.pack(fill='x', pady=4, padx=5)
            label = Label(frame, text=text, font=(FONT_FAMILY, 9), bg=FRAME_BG, fg=TEXT_COLOR)
            label.pack(side='left')

            tooltip_text = self.settings_manager.get_description(var_key)
            Tooltip(label, tooltip_text)

            self.param_vars[var_key] = var_type(value=default_value)
            self.last_known_good_params[var_key] = default_value
            tk.Entry(frame, textvariable=self.param_vars[var_key], font=(FONT_FAMILY, 9), bg=FRAME_BG, fg=TEXT_COLOR,
                     relief='solid', width=15, borderwidth=1).pack(side='right', ipady=4)

        create_param_entry(detection_pane.sub_frame, "Line Sensitivity:", 'line_sensitivity', 50, tk.IntVar)
        create_param_entry(detection_pane.sub_frame, "Line Min Height (%):", 'line_min_height', 100, tk.IntVar)
        create_param_entry(detection_pane.sub_frame, "Zone Min Width:", 'zone_min_width', 100, tk.IntVar)
        create_param_entry(detection_pane.sub_frame, "Zone Max Width (%):", 'max_zone_width_percent', 30, tk.IntVar)
        create_param_entry(detection_pane.sub_frame, "Zone Min Height (%):", 'min_zone_height_percent', 100, tk.IntVar)
        create_param_entry(detection_pane.sub_frame, "Initial Saturation Thresh:", 'saturation_threshold', 1, tk.IntVar)
        create_param_entry(behavior_pane.sub_frame, "Zone Smoothing:", 'zone_smoothing_factor', 1.0, tk.DoubleVar)
        create_param_entry(behavior_pane.sub_frame, "Target Width (%):", 'sweet_spot_width_percent', 15, tk.IntVar)
        create_param_entry(behavior_pane.sub_frame, "Post-Click Blindness (ms):", 'post_click_blindness', 250,
                           tk.IntVar)

        self.param_vars['prediction_enabled'] = tk.BooleanVar(value=True)
        pred_check = Checkbutton(behavior_pane.sub_frame, text="Enable Prediction",
                                 variable=self.param_vars['prediction_enabled'], bg=FRAME_BG, fg=TEXT_COLOR,
                                 selectcolor=BG_COLOR, activebackground=FRAME_BG, activeforeground=TEXT_COLOR,
                                 font=(FONT_FAMILY, 9))
        pred_check.pack(anchor='w', pady=5, padx=5)
        Tooltip(pred_check, self.settings_manager.get_description('prediction_enabled'))

        create_param_entry(behavior_pane.sub_frame, "Latency (ms):", 'system_latency', 0, tk.IntVar)
        create_param_entry(behavior_pane.sub_frame, "Max Prediction (ms):", 'max_prediction_time', 50, tk.IntVar)
        create_param_entry(behavior_pane.sub_frame, "Min Velocity:", 'min_velocity_threshold', 30, tk.IntVar)
        create_param_entry(behavior_pane.sub_frame, "Prediction Confidence:", 'prediction_confidence_threshold', 0.7,
                           tk.DoubleVar)

        check_style = {'bg': FRAME_BG, 'fg': TEXT_COLOR, 'selectcolor': BG_COLOR, 'activebackground': FRAME_BG,
                       'activeforeground': TEXT_COLOR, 'font': (FONT_FAMILY, 9)}

        self.param_vars['main_on_top'] = tk.BooleanVar(value=True)
        self.param_vars['main_on_top'].trace_add('write', self.toggle_main_on_top)
        main_top_check = Checkbutton(window_pane.sub_frame, text="Main Window Always on Top",
                                     variable=self.param_vars['main_on_top'], **check_style)
        main_top_check.pack(anchor='w', pady=5, padx=5)
        Tooltip(main_top_check, self.settings_manager.get_description('main_on_top'))

        self.param_vars['preview_on_top'] = tk.BooleanVar(value=True)
        self.param_vars['preview_on_top'].trace_add('write', self.toggle_preview_on_top)
        preview_top_check = Checkbutton(window_pane.sub_frame, text="Preview Window Always on Top",
                                        variable=self.param_vars['preview_on_top'], **check_style)
        preview_top_check.pack(anchor='w', pady=5, padx=5)
        Tooltip(preview_top_check, self.settings_manager.get_description('preview_on_top'))

        self.param_vars['debug_on_top'] = tk.BooleanVar(value=True)
        self.param_vars['debug_on_top'].trace_add('write', self.toggle_debug_on_top)
        debug_top_check = Checkbutton(window_pane.sub_frame, text="Debug Window Always on Top",
                                      variable=self.param_vars['debug_on_top'], **check_style)
        debug_top_check.pack(anchor='w', pady=5, padx=5)
        Tooltip(debug_top_check, self.settings_manager.get_description('debug_on_top'))

        def set_hotkey_thread(key_var, button):
            button.config(text="Press any key...", state=tk.DISABLED, bg="#0078D4", fg="#ffffff")
            self.root.update_idletasks()
            try:
                event = keyboard.read_event(suppress=True)
                if event.event_type == keyboard.KEY_DOWN:
                    key_var.set(event.name)
            except Exception as e:
                self.update_status(f"Hotkey capture failed: {e}")
            finally:
                button.config(text=key_var.get().upper(), state=tk.NORMAL, bg=BTN_BG, fg=TEXT_COLOR)
                self.apply_keybinds()

        def create_hotkey_setter(parent, text, key_name, default_value):
            frame = Frame(parent, bg=FRAME_BG)
            frame.pack(fill='x', pady=10, padx=5)
            label = Label(frame, text=text, font=(FONT_FAMILY, 10), bg=FRAME_BG, fg=TEXT_COLOR)
            label.pack(side='left', padx=(0, 20))

            tooltip_text = self.settings_manager.get_keybind_description(key_name)
            Tooltip(label, tooltip_text)

            self.keybind_vars[key_name] = tk.StringVar(value=default_value)
            hotkey_btn = Button(frame, text=default_value.upper(), font=(FONT_FAMILY, 10, 'bold'), bg=BTN_BG,
                                fg=TEXT_COLOR, relief='solid', borderwidth=1, width=15, pady=5)
            hotkey_btn.config(
                command=lambda v=self.keybind_vars[key_name], b=hotkey_btn: threading.Thread(target=set_hotkey_thread,
                                                                                             args=(v, b),
                                                                                             daemon=True).start())
            hotkey_btn.pack(side='right')

        create_hotkey_setter(hotkeys_pane.sub_frame, "Toggle Bot:", 'toggle_bot', 'f1')
        create_hotkey_setter(hotkeys_pane.sub_frame, "Toggle GUI:", 'toggle_gui', 'f2')
        create_hotkey_setter(hotkeys_pane.sub_frame, "Toggle Overlay:", 'toggle_overlay', 'f3')

        settings_btn_frame = Frame(settings_pane.sub_frame, bg=FRAME_BG)
        settings_btn_frame.pack(fill='x', pady=10, padx=5)
        Button(settings_btn_frame, text="Save Settings", command=self.settings_manager.save_settings,
               **button_style).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        Button(settings_btn_frame, text="Load Settings", command=self.settings_manager.load_settings,
               **button_style).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        reset_btn_frame = Frame(settings_pane.sub_frame, bg=FRAME_BG)
        reset_btn_frame.pack(fill='x', pady=(5, 10), padx=5)
        Button(reset_btn_frame, text="Reset to Defaults", command=self.settings_manager.reset_to_defaults,
               **button_style).pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.update_main_button_text()
        self.toggle_main_on_top()
        self.update_area_info()

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
            self.update_status("Clicking Started...")
            self.click_count = 0
            self.velocity_calculator = VelocityCalculator()
            self.init_debug_log()
            if self.click_lock.locked(): self.click_lock.release()
        else:
            self.running = False
            self.update_status("Stopped")
        self.update_main_button_text()

    def init_debug_log(self):
        try:
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
        try:
            timestamp = int(time.time())
            click_type = "PREDICTION" if prediction_used else "DIRECT"
            sweet_spot_range = f"{int(sweet_spot_start)}-{int(sweet_spot_end)}" if sweet_spot_start is not None else "N/A"

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
        send_click()
        self.last_click_time = time.time() * 1000
        self.click_count += 1
        self.click_lock.release()

    def save_debug_screenshot(self, screenshot, line_pos, sweet_spot_start, sweet_spot_end, zone_y2_cached, velocity,
                              acceleration, prediction_used=False, confidence=0.0):
        debug_img = screenshot.copy()
        height = debug_img.shape[0]

        if self.smoothed_zone_x is not None:
            cv2.rectangle(debug_img, (int(self.smoothed_zone_x), 0),
                          (int(self.smoothed_zone_x + self.smoothed_zone_w), zone_y2_cached), (0, 255, 0), 3)

        if sweet_spot_start is not None and sweet_spot_end is not None:
            cv2.rectangle(debug_img, (int(sweet_spot_start), 0), (int(sweet_spot_end), zone_y2_cached), (0, 255, 255),
                          3)

        if line_pos != -1:
            cv2.line(debug_img, (line_pos, 0), (line_pos, height), (0, 0, 255), 4)

        filename = f"click_{self.click_count:03d}_{int(time.time())}.jpg"
        filepath = os.path.join(self.debug_dir, filename)
        cv2.imwrite(filepath, debug_img)

        self.log_click_debug(self.click_count, line_pos, velocity, acceleration, sweet_spot_start, sweet_spot_end,
                             prediction_used, confidence, filename)

    def run_main_loop(self):
        target_fps = 120
        target_delay = 1.0 / target_fps
        final_mask = None
        height_80_cached = None
        zone_y2_cached = None
        kernel = np.ones((5, 15), np.uint8)

        while self.preview_active:
            start_time = time.perf_counter()
            current_time_ms = time.time() * 1000

            if self.game_area is None or current_time_ms < self.blind_until:
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

            if self.running and sweet_spot_center is not None and not self.click_lock.locked():
                line_in_sweet_spot = sweet_spot_start <= line_pos <= sweet_spot_end
                should_click, click_delay, prediction_used, confidence = False, 0, False, 0.0

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
                    self.save_debug_screenshot(screenshot, line_pos, sweet_spot_start, sweet_spot_end, zone_y2_cached,
                                               velocity, acceleration, prediction_used, confidence)
                    self.blind_until = current_time_ms + self.get_param('post_click_blindness')
                    self.click_lock.acquire()
                    threading.Thread(target=self.perform_click, args=(click_delay,)).start()

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
                overlay_info = {'sweet_spot_center': sweet_spot_center, 'velocity': velocity,
                                'click_count': self.click_count, 'locked_color_hex': self.locked_color_hex,
                                'preview_thumbnail': thumbnail}
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