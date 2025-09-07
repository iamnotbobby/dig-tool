import ctypes
import os
import queue
import sys
import threading
import time
import tkinter as tk
import traceback

import cv2
import numpy as np

try:
    from tkinterdnd2 import TkinterDnD

    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from core.automation import AutomationManager
from core.automation.roblox_status import RobloxRejoiner
from core.detection import (
    VelocityCalculator,
    calculate_velocity_based_sweet_spot_width,
    check_target_engagement,
    detect_by_color_picker,
    detect_by_otsu_adaptive_area,
    detect_by_otsu_with_area_filter,
    find_line_position,
    get_hsv_bounds,
    rgb_to_hsv_single,
)
from core.initialization import (
    check_and_enable_buttons,
    initialize_default_param_vars,
    perform_initial_latency_measurement,
)
from core.notifications import (
    DiscordNotifier,
    check_milestone_notifications,
    send_shutdown_notification,
    send_startup_notification,
)
from core.ocr import ItemOCR, MoneyOCR
from interface.main_window import MainWindow
from interface.settings import SettingsManager
from utils.config_management import (
    get_param,
)
from utils.debug_logger import (
    enable_console_logging,
    ensure_debug_directory,
    get_debug_log_path,
    init_click_debug_log,
    logger,
    setup_debug_directory,
)
from utils.input_management import (
    perform_click,
    perform_instant_click,
    save_debug_screenshot_wrapper,
)
from utils.screen_capture import ScreenCapture
from utils.system_utils import (
    calculate_window_dimensions,
    check_beta_version_warning,
    check_display_scale,
    get_cached_system_latency,
    set_dig_tool_instance,
    update_time_cache,
)
from utils.thread_utils import (
    check_shutdown,
    start_threads,
)
from utils.ui_management import (
    setup_dropdown_resize_handling,
    update_gui_from_queue,
    update_main_button_text,
)
from utils.system_utils import _get_version_info


def get_window_title():
    version, version_beta = _get_version_info()
    if version_beta is not None:
        version += f"-beta.{version_beta}"
    return f"Dig Tool - v{version}"

try:
    PROCESS_PER_MONITOR_DPI_AWARE = 2
    ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
except Exception:
    pass

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    try:
        error_msg = f"Uncaught exception: {exc_type.__name__}: {exc_value}"
        logger.error(error_msg)
        logger.error(
            f"Traceback: {''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))}"
        )
        logger._save_latest_log()
    except:
        pass

    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = handle_exception
check_display_scale()
_, version_beta = _get_version_info()
check_beta_version_warning(version_beta)


class DigTool:
    def __init__(self):
        # Comment if in dev
        enable_console_logging()

        # Test stdout and stderr
        print("Did you know Dig Tool is voice activated?")
        sys.stderr.write("Herobrine is in your system...\n")

        if DND_AVAILABLE:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()
        self.root.title(get_window_title())

        self.root.wm_iconbitmap(
            os.path.join(sys._MEIPASS, "assets/icon.ico")
            if hasattr(sys, "_MEIPASS")
            else "assets/icon.ico"
        )

        self.width, self.base_height = calculate_window_dimensions()
        self.root.geometry(f"{self.width}x{self.base_height}")
        self.root.minsize(self.width, self.base_height)

        self.param_vars = {}
        self.keybind_vars = {}
        self.last_known_good_params = {}
        self.window_positions = {}

        self.game_area = None
        self.cursor_position = None

        self.settings_manager = SettingsManager(self)

        initialize_default_param_vars(self)

        self.automation_manager = AutomationManager(self)
        self.discord_notifier = DiscordNotifier()

        self.roblox_rejoiner = RobloxRejoiner(self)

        self.money_ocr = MoneyOCR(self)
        self.item_ocr = ItemOCR()

        self.settings_manager.load_all_settings()

        self.automation_manager.auto_load_patterns()

        self.main_window = MainWindow(self)
        self.custom_pattern_window = None

        self.root.after_idle(lambda: self.settings_manager.apply_loaded_parameters())

        self.root.after_idle(lambda: check_and_enable_buttons(self))

        set_dig_tool_instance(self)
        self.root.after(500, lambda: perform_initial_latency_measurement(self))
        self.running = False
        self.preview_active = True
        self.is_auto_rejoining = False
        self.overlay = None
        self.overlay_enabled = False
        self.autowalk_overlay = None
        self.autowalk_overlay_enabled = False
        self.color_modules_overlay = None
        self.color_modules_overlay_enabled = False
        self.cam = ScreenCapture()
        self.region_key = "main_game"
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
        self.detection_info_label = None
        self.velocity_info_label = None
        self.main_loop_thread = None
        self.hotkey_thread = None
        self.results_queue = queue.Queue(maxsize=1)

        self.status_text = None
        self.status_label = None

        self.debug_dir = setup_debug_directory()
        ensure_debug_directory(self.debug_dir)
        self.debug_log_path = get_debug_log_path(self.debug_dir)

        self._memory_cleanup_counter = 0
        self._cached_kernel = None
        self._cached_kernel_size = 0

        self.last_milestone_notification = 0

        self.target_engaged = False
        self.line_moving_history = []
        self.base_line_movement_check_frames = 30
        self.min_movement_threshold = 50

        self.manual_dig_target_disengaged_time = 0
        self.manual_dig_was_engaged = False

        self._kernel = np.ones((5, 15), np.uint8)
        self._hsv_lower_bound_cache = None
        self._hsv_upper_bound_cache = None
        self._last_hsv_color = None
        self._last_is_low_sat = None

        self._current_time_cache = 0
        self._current_time_ms_cache = 0
        self._last_time_update = 0

        self._click_thread_pool = []
        self._max_click_threads = 3

        self.item_counts_since_startup = {
            "junk": 0,
            "common": 0,
            "unusual": 0,
            "scarce": 0,
            "legendary": 0,
            "mythical": 0,
            "divine": 0,
            "prismatic": 0,
        }

        # Benchmarking
        self.report_interval = 1
        self.frame_times = []
        self.last_report_time = time.time()
        self.last_frame_time = time.perf_counter()
        self.benchmark_fps = 0

        self.main_window.create_ui()

        setup_dropdown_resize_handling(self)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(50, lambda: update_gui_from_queue(self))

    def on_closing(self):
        try:
            self.settings_manager.save_all_settings()
            logger.info("Settings saved on application close")
        except Exception as e:
            logger.error(f"Error saving settings on close: {e}")

        if self.running:
            send_shutdown_notification(self)

        self.preview_active = False
        self.running = False
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.update_status("Shutting down...")

        try:
            self.automation_manager.cleanup()
        except Exception as e:
            logger.error(f"Error during automation cleanup: {e}")

        logger.cleanup()

        self.root.after(100, lambda: check_shutdown(self))

    def start_threads(self):
        start_threads(self)

    def toggle_detection(self):
        self.root.after(0, self._toggle_detection_thread_safe)

    def _toggle_detection_thread_safe(self):
        if not self.running:
            if not self.game_area:
                self.update_status("Select game area first")
                return

            self.running = True
            self.update_status("Bot Started...")

            self.reset_detection_state()

            self.automation_manager.sell_count = 0
            self.automation_manager.shiftlock_state = {
                "shift": False,
                "right_shift": False,
            }
            self.automation_manager.movement_manager.is_walking = False

            self.item_counts_since_startup = {
                "junk": 0,
                "common": 0,
                "unusual": 0,
                "scarce": 0,
                "legendary": 0,
                "mythical": 0,
                "divine": 0,
                "prismatic": 0,
            }

            if get_param(self, "debug_enabled"):
                init_click_debug_log(self.debug_log_path)
            if self.click_lock.locked():
                self.click_lock.release()

            send_startup_notification(self)

        else:
            self.running = False

            if self.automation_manager.is_recording:
                self.automation_manager.stop_recording_pattern()

            self.automation_manager.is_selling = False
            self.automation_manager.movement_manager.is_walking = False

            if hasattr(self, "roblox_rejoiner"):
                logger.debug("Resetting auto-rejoin state due to manual stop")
                self.roblox_rejoiner.rejoin_attempts = 0
                self.roblox_rejoiner._max_attempts_reached = False
                self.roblox_rejoiner._is_rejoining = False
                if hasattr(self.roblox_rejoiner, "_current_attempt_start"):
                    self.roblox_rejoiner._current_attempt_start = None
                if hasattr(
                    self.roblox_rejoiner.status_monitor, "_automation_was_running"
                ):
                    self.roblox_rejoiner.status_monitor._automation_was_running = False

            self.update_status("Stopped")

            send_shutdown_notification(self)

        update_main_button_text(self)

    def update_status(self, text):
        if self.root.winfo_exists():
            try:
                if hasattr(self, "status_text") and self.status_text:
                    self.status_text.config(state="normal")
                    self.status_text.delete(1.0, tk.END)
                    self.status_text.insert(1.0, text)

                    lines = text.count("\n") + 1
                    chars_per_line = 90
                    wrapped_lines = max(1, len(text) // chars_per_line)
                    total_lines = max(lines, wrapped_lines)

                    height = max(3, min(6, total_lines))
                    self.status_text.config(height=height)

                    self.status_text.config(state="disabled")
                elif hasattr(self, "status_label") and self.status_label:
                    self.status_label.config(text=f"Status: {text}")
            except Exception:
                pass

    def _update_time_cache(self):
        update_time_cache(self)

    def reset_detection_state(self):
        reset_values = {
            # Visual detection state
            "blind_until": 0,
            "smoothed_zone_x": None,
            "smoothed_zone_w": None,
            "is_color_locked": False,
            "locked_color_hsv": None,
            "locked_color_hex": None,
            "is_low_sat_lock": False,
            "frames_since_last_zone_detection": 0,
            # Target engagement state
            "target_engaged": False,
            "line_moving_history": [],
            "manual_dig_target_disengaged_time": 0,
            "manual_dig_was_engaged": False,
            # Autowalk state machine
            "auto_walk_state": "move",
            "move_completed_time": 0,
            "wait_for_target_start": 0,
            "target_disengaged_time": 0,
            "click_retry_count": 0,
            # Cache variables
            "_hsv_lower_bound_cache": None,
            "_hsv_upper_bound_cache": None,
            "_last_hsv_color": None,
            "_last_is_low_sat": None,
            # Timing caches
            "_current_time_cache": 0,
            "_current_time_ms_cache": 0,
            "_last_time_update": 0,
            # Counters
            "click_count": 0,
            "dig_count": 0,
        }

        for attr_name, reset_value in reset_values.items():
            setattr(self, attr_name, reset_value)

        if hasattr(self, "_line_detection_stats"):
            del self._line_detection_stats

        if hasattr(self, "automation_manager"):
            old_index = self.automation_manager.walk_pattern_index
            self.automation_manager.walk_pattern_index = 0
            logger.debug(f"Reset walk pattern index from {old_index} to 0")

        self.startup_time = time.time() * 1000
        self._startup_grace_ended = False
        self.velocity_calculator.reset()

    def reset_item_counts_for_startup(self):
        self.item_counts_since_startup = {
            "junk": 0,
            "common": 0,
            "unusual": 0,
            "scarce": 0,
            "legendary": 0,
            "mythical": 0,
            "divine": 0,
            "prismatic": 0,
        }

    def count_item_rarity(self, rarity):
        if rarity and rarity.lower() in self.item_counts_since_startup:
            self.item_counts_since_startup[rarity.lower()] += 1
            logger.debug(
                f"Item counted: {rarity} (total: {self.item_counts_since_startup[rarity.lower()]})"
            )

    def run_main_loop(self):
        screenshot_fps = get_param(self, "screenshot_fps")
        process_every_nth_frame = 1

        screenshot_delay = 1.0 / screenshot_fps
        final_mask = None

        if not hasattr(self, "auto_walk_state"):
            self.auto_walk_state = "move"
        if not hasattr(self, "move_completed_time"):
            self.move_completed_time = 0
        if not hasattr(self, "wait_for_target_start"):
            self.wait_for_target_start = 0
        if not hasattr(self, "target_disengaged_time"):
            self.target_disengaged_time = 0
        if not hasattr(self, "click_retry_count"):
            self.click_retry_count = 0

        current_step_click_enabled = True
        dig_completed_time = 0
        pending_auto_sell = False
        walk_thread = None
        post_dig_delay = 2000
        max_click_retries = 2

        cached_height_80 = None
        cached_zone_y2 = None
        cached_line_area = None
        cached_hsv_area = None
        frame_skip_counter = 0
        click_delay = 0  # UnboundLocalError

        while self.preview_active:
            frame_start_time = time.perf_counter()
            self._update_time_cache()
            current_time_ms = self._current_time_ms_cache

            startup_grace_period = 100
            if (
                hasattr(self, "startup_time")
                and hasattr(self, "_startup_grace_ended")
                and not self._startup_grace_ended
                and (current_time_ms - self.startup_time) > startup_grace_period
            ):
                self._startup_grace_ended = True
                if self.running:
                    self.update_status("Bot Running...")

            self._memory_cleanup_counter += 1
            if self._memory_cleanup_counter % 300 == 0:
                import gc

                gc.collect()

            game_fps = max(get_param(self, "target_fps"), 1)
            self.velocity_calculator.update_fps(game_fps)

            if self.game_area is None:
                time.sleep(0.01)
                continue

            if self.running and self.automation_manager.should_re_equip_shovel():
                self.automation_manager.re_equip_shovel()
            frame_skip_counter += 1
            should_process_zones = frame_skip_counter % process_every_nth_frame == 0

            capture_start = time.perf_counter()
            screenshot = self.cam.capture(
                bbox=self.game_area, region_key=self.region_key
            )
            capture_time = time.perf_counter() - capture_start

            if screenshot is None:
                time.sleep(screenshot_delay)
                continue

            height, width = screenshot.shape[:2]

            if cached_height_80 is None or cached_height_80 != int(height * 0.80):
                cached_height_80 = int(height * 0.80)
                cached_zone_y2 = cached_height_80

            height_80 = cached_height_80
            zone_y2 = cached_zone_y2

            if cached_line_area is None or cached_line_area.shape != (height, width):
                cached_line_area = np.empty((height, width), dtype=np.uint8)

            cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY, dst=cached_line_area)
            line_sensitivity = get_param(self, "line_sensitivity")
            line_min_height = 1.0
            line_offset = get_param(self, "line_detection_offset")
            if isinstance(line_offset, str):
                line_offset = float(line_offset)

            line_pos = find_line_position(
                cached_line_area, line_sensitivity, line_min_height, int(line_offset)
            )

            velocity_line_pos = line_pos
            if line_pos == -1:
                bottom_height = int(height * 0.3)
                bottom_start = height - bottom_height
                bottom_area = cached_line_area[bottom_start:, :]
                velocity_line_pos = find_line_position(
                    bottom_area, line_sensitivity, line_min_height, int(line_offset)
                )
                if velocity_line_pos != -1:
                    velocity_line_pos += 0

            if not hasattr(self, "_line_detection_stats"):
                self._line_detection_stats = {
                    "detected": 0,
                    "failed": 0,
                    "last_positions": [],
                }

            if line_pos == -1:
                self._line_detection_stats["failed"] += 1
            else:
                self._line_detection_stats["detected"] += 1
                self._line_detection_stats["last_positions"].append(line_pos)
                if len(self._line_detection_stats["last_positions"]) > 10:
                    self._line_detection_stats["last_positions"].pop(0)

            if should_process_zones:
                if cached_hsv_area is None or cached_hsv_area.shape != (
                    height_80,
                    width,
                    3,
                ):
                    cached_hsv_area = np.empty((height_80, width, 3), dtype=np.uint8)

                zone_detection_area = screenshot[:height_80, :]
                cv2.cvtColor(
                    zone_detection_area, cv2.COLOR_BGR2HSV, dst=cached_hsv_area
                )
                hsv = cached_hsv_area

                saturation_threshold = get_param(self, "saturation_threshold")

                use_otsu = get_param(self, "use_otsu_detection")
                otsu_disable_color_lock = get_param(self, "otsu_disable_color_lock")

                if not self.is_color_locked or (use_otsu and otsu_disable_color_lock):
                    if final_mask is None or final_mask.shape != (height_80, width):
                        final_mask = np.empty((height_80, width), dtype=np.uint8)

                    use_color_picker = get_param(self, "use_color_picker_detection")
                    detection_info = {}

                    if use_color_picker:
                        picked_color = get_param(self, "picked_color_rgb")
                        if picked_color and picked_color.strip() and picked_color != "":
                            try:
                                picked_color = picked_color.strip()

                                if picked_color.startswith("#"):
                                    picked_color = picked_color[1:]

                                if len(picked_color) != 6:
                                    raise ValueError(
                                        f"Invalid hex color length: {len(picked_color)}"
                                    )

                                rgb_color = int(picked_color, 16)
                                target_hsv = rgb_to_hsv_single(rgb_color)

                                color_tolerance_param = get_param(
                                    self, "color_tolerance"
                                )
                                color_tolerance = (
                                    color_tolerance_param
                                    if isinstance(color_tolerance_param, int)
                                    else 30
                                )

                                final_mask = detect_by_color_picker(
                                    hsv, target_hsv, color_tolerance, False
                                )

                                detected_pixels = (
                                    np.sum(final_mask > 0)
                                    if final_mask is not None
                                    else 0
                                )

                                detection_info = {
                                    "method": "Color Picker",
                                    "target_color": f"#{picked_color}",
                                    "tolerance": color_tolerance,
                                    "target_hsv": f"H:{target_hsv[0]} S:{target_hsv[1]} V:{target_hsv[2]}",
                                    "detected_pixels": detected_pixels,
                                }
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Color picker detection failed: {e}")
                                saturation = hsv[:, :, 1]
                                cv2.threshold(
                                    saturation,
                                    saturation_threshold,
                                    255,
                                    cv2.THRESH_BINARY,
                                    dst=final_mask,
                                )
                                detection_info = {
                                    "method": "Saturation (Fallback)",
                                    "threshold": saturation_threshold,
                                    "error": f"Color picker failed: {e}",
                                }
                        else:
                            saturation = hsv[:, :, 1]
                            cv2.threshold(
                                saturation,
                                saturation_threshold,
                                255,
                                cv2.THRESH_BINARY,
                                dst=final_mask,
                            )
                            detection_info = {
                                "method": "Saturation (No Color Picked)",
                                "threshold": saturation_threshold,
                            }
                    elif use_otsu:
                        if get_param(self, "otsu_adaptive_area"):
                            area_percentile = get_param(self, "otsu_area_percentile")
                            morph_kernel = get_param(self, "otsu_morph_kernel_size")
                            invert_mask = get_param(self, "otsu_invert_mask")
                            zone_connection_dilation = get_param(self, "zone_connection_dilation")
                            final_mask, threshold_value = detect_by_otsu_adaptive_area(
                                hsv,
                                area_percentile=area_percentile,
                                morph_kernel_size=morph_kernel,
                                invert_mask=invert_mask,
                                zone_connection_dilation=zone_connection_dilation,
                            )
                            detection_info = {
                                "method": "Otsu (Adaptive)",
                                "threshold": threshold_value,
                                "area_percentile": area_percentile,
                                "morph_kernel": morph_kernel,
                                "invert_mask": invert_mask,
                                "zone_connection_dilation": zone_connection_dilation,
                            }
                        else:
                            min_area = get_param(self, "otsu_min_area")
                            max_area_param = get_param(self, "otsu_max_area")
                            if (
                                max_area_param == ""
                                or max_area_param == "None"
                                or max_area_param == 0
                                or max_area_param is None
                            ):
                                max_area = None
                            else:
                                try:
                                    max_area = int(max_area_param)
                                except (ValueError, TypeError):
                                    max_area = None
                            morph_kernel = get_param(self, "otsu_morph_kernel_size")
                            invert_mask = get_param(self, "otsu_invert_mask")
                            zone_connection_dilation = get_param(self, "zone_connection_dilation")
                            final_mask, threshold_value = (
                                detect_by_otsu_with_area_filter(
                                    hsv,
                                    min_area=min_area,
                                    max_area=max_area,
                                    morph_kernel_size=morph_kernel,
                                    invert_mask=invert_mask,
                                    zone_connection_dilation=zone_connection_dilation,
                                )
                            )
                            detection_info = {
                                "method": "Otsu (Fixed Area)",
                                "threshold": threshold_value,
                                "min_area": min_area,
                                "max_area": (
                                    max_area if max_area is not None else "Unlimited"
                                ),
                                "morph_kernel": morph_kernel,
                                "invert_mask": invert_mask,
                                "zone_connection_dilation": zone_connection_dilation,
                            }
                    else:
                        saturation = hsv[:, :, 1]
                        cv2.threshold(
                            saturation,
                            saturation_threshold,
                            255,
                            cv2.THRESH_BINARY,
                            dst=final_mask,
                        )
                        detection_info = {
                            "method": "Saturation Threshold",
                            "threshold": saturation_threshold,
                        }

                    line_exclusion_radius = get_param(self, "line_exclusion_radius")
                    if line_exclusion_radius > 0 and line_pos != -1:
                        cv2.rectangle(
                            final_mask,
                            (max(0, line_pos - line_exclusion_radius), 0),
                            (min(width, line_pos + line_exclusion_radius), height_80),
                            0,
                            -1,
                        )

                    if not use_otsu and line_exclusion_radius > 0:
                        kernel_size = max(3, int(min(width, height) * 0.008))
                        if (
                            self._cached_kernel is None
                            or self._cached_kernel_size != kernel_size
                        ):
                            self._cached_kernel = cv2.getStructuringElement(
                                cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
                            )
                            self._cached_kernel_size = kernel_size
                        cv2.morphologyEx(
                            final_mask,
                            cv2.MORPH_CLOSE,
                            self._cached_kernel,
                            dst=final_mask,
                            iterations=2,
                        )
                        cv2.morphologyEx(
                            final_mask,
                            cv2.MORPH_OPEN,
                            self._cached_kernel,
                            dst=final_mask,
                            iterations=1,
                        )
                else:
                    if (
                        self._last_hsv_color is None
                        or (
                            self.locked_color_hsv is not None
                            and not np.array_equal(
                                self.locked_color_hsv, self._last_hsv_color
                            )
                        )
                        or self._last_is_low_sat != self.is_low_sat_lock
                    ):
                        self._hsv_lower_bound_cache, self._hsv_upper_bound_cache = (
                            get_hsv_bounds(self.locked_color_hsv, self.is_low_sat_lock)
                        )
                        if self.locked_color_hsv is not None:
                            self._last_hsv_color = self.locked_color_hsv.copy()
                        self._last_is_low_sat = self.is_low_sat_lock
                    lower_bound, upper_bound = (
                        self._hsv_lower_bound_cache,
                        self._hsv_upper_bound_cache,
                    )
                    if final_mask is None or final_mask.shape != (height_80, width):
                        final_mask = np.empty((height_80, width), dtype=np.uint8)

                    if lower_bound is not None and upper_bound is not None:
                        cv2.inRange(hsv, lower_bound, upper_bound, dst=final_mask)
                        detection_info = {
                            "method": "Color Lock (HSV Range)",
                            "threshold": f"HSV: {lower_bound} - {upper_bound}",
                            "locked_color": (
                                self.locked_color_hex
                                if hasattr(self, "locked_color_hex")
                                else "Unknown"
                            ),
                        }
                    else:
                        final_mask.fill(0)
                        detection_info = {
                            "method": "Color Lock (No Color)",
                            "threshold": "N/A",
                        }

                    line_exclusion_radius = get_param(self, "line_exclusion_radius")
                    if line_exclusion_radius > 0 and line_pos != -1:
                        cv2.rectangle(
                            final_mask,
                            (max(0, line_pos - line_exclusion_radius), 0),
                            (min(width, line_pos + line_exclusion_radius), height_80),
                            0,
                            -1,
                        )

                cv2.morphologyEx(
                    final_mask,
                    cv2.MORPH_CLOSE,
                    self._kernel,
                    dst=final_mask,
                    iterations=2,
                )
                contours, _ = cv2.findContours(
                    final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                merge_nearby = get_param(self, "merge_nearby_zones")
                if merge_nearby and len(contours) > 1:
                    merge_distance = get_param(self, "zone_merge_distance")
                    from core.detection import merge_nearby_contours
                    contours = merge_nearby_contours(contours, merge_distance)

                raw_zone_x, raw_zone_w = None, None
                if contours:
                    main_contour = max(contours, key=cv2.contourArea)
                    x_temp, y_temp, w_temp, h_temp = cv2.boundingRect(main_contour)

                    zone_min_width = get_param(self, "zone_min_width")
                    max_zone_width = width * (
                        get_param(self, "max_zone_width_percent") / 100.0
                    )
                    min_zone_height = height_80 * (
                        get_param(self, "min_zone_height_percent") / 100.0
                    )

                    if (
                        w_temp > zone_min_width
                        and w_temp < max_zone_width
                        and h_temp >= min_zone_height
                    ):
                        raw_zone_x, raw_zone_w = x_temp, w_temp
                        if (
                            not self.is_color_locked
                            and not (use_otsu and otsu_disable_color_lock)
                            and not use_color_picker
                        ):
                            mask = np.zeros(hsv.shape[:2], dtype="uint8")
                            cv2.drawContours(mask, [main_contour], -1, (255,), -1)
                            mean_hsv = cv2.mean(hsv, mask=mask)
                            self.locked_color_hsv = np.array(
                                mean_hsv[:3], dtype=np.float32
                            )
                            self.is_color_locked = True
                            if self.locked_color_hsv is not None:
                                hsv_array = np.array(
                                    [
                                        [
                                            [
                                                int(self.locked_color_hsv[0]),
                                                int(self.locked_color_hsv[1]),
                                                int(self.locked_color_hsv[2]),
                                            ]
                                        ]
                                    ],
                                    dtype=np.uint8,
                                )
                                bgr_color = cv2.cvtColor(hsv_array, cv2.COLOR_HSV2BGR)[
                                    0
                                ][0]
                                self.locked_color_hex = f"#{bgr_color[2]:02x}{bgr_color[1]:02x}{bgr_color[0]:02x}"
                            self.is_low_sat_lock = self.locked_color_hsv[1] < 25
            else:
                raw_zone_x, raw_zone_w = None, None

            if raw_zone_x is not None and raw_zone_w is not None:
                self.automation_manager.update_target_lock_activity()
                self.frames_since_last_zone_detection = 0

                zone_smoothing_factor = get_param(self, "zone_smoothing_factor")

                if self.smoothed_zone_x is None:
                    self.smoothed_zone_x, self.smoothed_zone_w = raw_zone_x, raw_zone_w
                else:
                    position_change = abs(raw_zone_x - self.smoothed_zone_x)
                    width_change = abs(raw_zone_w - (self.smoothed_zone_w or 0))

                    if zone_smoothing_factor >= 1.0:
                        adaptive_smoothing = 1.0
                    elif zone_smoothing_factor <= 0.01:
                        adaptive_smoothing = zone_smoothing_factor
                    else:
                        max_change_threshold = width * 0.1
                        if (
                            position_change > max_change_threshold
                            or width_change > max_change_threshold
                        ):
                            adaptive_smoothing = min(zone_smoothing_factor + 0.1, 1.0)
                        else:
                            adaptive_smoothing = zone_smoothing_factor

                    self.smoothed_zone_x = adaptive_smoothing * raw_zone_x + (
                        1 - adaptive_smoothing
                    ) * (self.smoothed_zone_x or 0)
                    self.smoothed_zone_w = adaptive_smoothing * raw_zone_w + (
                        1 - adaptive_smoothing
                    ) * (self.smoothed_zone_w or 0)
            else:
                self.frames_since_last_zone_detection += 1

            zone_timeout_frames = max(int(game_fps * 0.167), 5)
            if self.frames_since_last_zone_detection > zone_timeout_frames:
                self.is_color_locked = False
                self.locked_color_hsv = None
                self.locked_color_hex = None
                self.smoothed_zone_x = None

            velocity = self.velocity_calculator.add_position(
                velocity_line_pos, self._current_time_cache
            )
            acceleration = self.velocity_calculator.get_acceleration()

            display_velocity = 0.0
            if len(self.velocity_calculator.position_history) >= 2:
                recent_positions = list(self.velocity_calculator.position_history)[-2:]
                if len(recent_positions) == 2:
                    pos1, t1 = recent_positions[0]
                    pos2, t2 = recent_positions[1]
                    if pos1 != -1 and pos2 != -1 and t2 > t1:
                        display_velocity = (pos2 - pos1) / (t2 - t1)

            self.target_engaged = check_target_engagement(self, line_pos, game_fps)

            sweet_spot_center, sweet_spot_start, sweet_spot_end = None, None, None
            if self.smoothed_zone_x is not None:
                sweet_spot_center = (self.smoothed_zone_x or 0) + (
                    self.smoothed_zone_w or 0
                ) / 2

                base_sweet_spot_width_percent = (
                    get_param(self, "sweet_spot_width_percent") / 100.0
                )
                enabled = get_param(self, "velocity_based_width_enabled")
                velocity_multiplier = get_param(self, "velocity_width_multiplier")
                max_velocity_factor = get_param(self, "velocity_max_factor")

                dynamic_sweet_spot_width_percent = (
                    calculate_velocity_based_sweet_spot_width(
                        base_sweet_spot_width_percent * 100.0,
                        velocity,
                        enabled=enabled,
                        velocity_multiplier=velocity_multiplier,
                        max_velocity_factor=max_velocity_factor,
                    )
                    / 100.0
                )
                sweet_spot_width = (
                    self.smoothed_zone_w or 0
                ) * dynamic_sweet_spot_width_percent
                sweet_spot_start = sweet_spot_center - sweet_spot_width / 2
                sweet_spot_end = sweet_spot_center + sweet_spot_width / 2

            if pending_auto_sell and dig_completed_time > 0:
                time_since_pending = current_time_ms - dig_completed_time
                if time_since_pending > 10000:
                    logger.warning(
                        f"Auto-sell pending timeout ({time_since_pending}ms) - clearing stuck state"
                    )
                    pending_auto_sell = False
                    dig_completed_time = 0

            if (
                self.running
                and pending_auto_sell
                and dig_completed_time > 0
                and current_time_ms - dig_completed_time >= post_dig_delay
                and not self.automation_manager.is_selling
            ):
                logger.debug(
                    f"Initiating auto-sell: dig_count={self.dig_count}, sell_every_x_digs={get_param(self, 'sell_every_x_digs')}"
                )

                if self.automation_manager.is_auto_sell_ready():
                    threading.Thread(
                        target=self.automation_manager.perform_auto_sell,
                        daemon=True,
                    ).start()
                    pending_auto_sell = False
                    dig_completed_time = 0

                    wait_start_time = time.time()
                    auto_sell_max_wait_time = 30.0

                    while (
                        self.automation_manager.is_selling
                        and self.running
                        and (time.time() - wait_start_time) < auto_sell_max_wait_time
                    ):
                        time.sleep(0.1)

                    if (time.time() - wait_start_time) >= auto_sell_max_wait_time:
                        logger.warning(
                            "Auto-sell wait timeout reached, continuing operation"
                        )

                    logger.info("Auto-sell completed, returning to movement")
                    self.auto_walk_state = "move"
                    self.move_completed_time = current_time_ms + 500
                else:
                    logger.warning(
                        "Auto-sell skipped: not ready (sell button, running state, or already selling)"
                    )
                    pending_auto_sell = False
                    dig_completed_time = 0

            if (
                self.running
                and get_param(self, "auto_walk_enabled")
                and not self.automation_manager.is_selling
            ):
                if self.auto_walk_state == "move":
                    if (
                        not self.automation_manager.is_selling
                        and not pending_auto_sell
                        and current_time_ms >= self.move_completed_time
                    ):
                        if walk_thread is None or not walk_thread.is_alive():
                            direction = (
                                self.automation_manager.get_next_walk_direction()
                            )

                            if isinstance(direction, dict):
                                current_step_click_enabled = direction.get(
                                    "click", True
                                )
                            else:
                                current_step_click_enabled = True

                            def perform_walk_with_callback():
                                if (
                                    self.automation_manager.is_selling
                                    or not self.running
                                ):
                                    logger.debug(
                                        "Walk step aborted - selling in progress or tool stopped"
                                    )
                                    return

                                if isinstance(direction, dict):
                                    key = direction.get("key", "")
                                    custom_duration = direction.get("duration", None)
                                    if custom_duration is not None:
                                        success = self.automation_manager.movement_manager.execute_movement_with_duration(
                                            key, custom_duration / 1000.0
                                        )
                                    else:
                                        success = (
                                            self.automation_manager.perform_walk_step(
                                                key
                                            )
                                        )
                                else:
                                    success = self.automation_manager.perform_walk_step(
                                        direction
                                    )

                            walk_thread = threading.Thread(
                                target=perform_walk_with_callback, daemon=True
                            )
                            walk_thread.start()

                            self.auto_walk_state = "click_to_start"

                            if (
                                isinstance(direction, dict)
                                and direction.get("duration") is not None
                            ):
                                duration_value = direction.get("duration")
                                try:
                                    walk_duration = (
                                        int(duration_value)
                                        if duration_value is not None
                                        else 1000
                                    )
                                except (ValueError, TypeError):
                                    walk_duration = 1000
                            else:
                                walk_duration = get_param(self, "walk_duration")

                            self.move_completed_time = current_time_ms + walk_duration

                elif (
                    self.auto_walk_state == "click_to_start"
                    and current_time_ms >= self.move_completed_time
                    and not self.automation_manager.is_selling
                    and self.running
                ):
                    if current_step_click_enabled:
                        if not self.click_lock.locked():
                            self.click_lock.acquire()
                            threading.Thread(
                                target=perform_click,
                                args=(
                                    self,
                                    click_delay,
                                ),
                            ).start()
                            self.auto_walk_state = "wait_for_target"
                            self.wait_for_target_start = current_time_ms
                    else:
                        logger.debug("Skipping click for this step (click disabled)")
                        self.auto_walk_state = "move"
                        self.automation_manager.advance_walk_pattern()
                        logger.debug(
                            f"Advanced to pattern index: {self.automation_manager.walk_pattern_index}"
                        )
                        self.move_completed_time = 0

                elif (
                    self.auto_walk_state == "wait_for_target"
                    and not self.automation_manager.is_selling
                    and self.running
                ):
                    if self.target_engaged:
                        self.auto_walk_state = "digging"
                        self.target_disengaged_time = 0
                        self.click_retry_count = 0
                    elif current_time_ms - self.wait_for_target_start > get_param(
                        self, "max_wait_time"
                    ):
                        if self.click_retry_count < max_click_retries:
                            self.click_retry_count += 1
                            logger.debug(
                                f"Target engagement timeout - retry {self.click_retry_count}/{max_click_retries}"
                            )

                            if not self.click_lock.locked():
                                self.click_lock.acquire()
                                threading.Thread(
                                    target=perform_click,
                                    args=(
                                        self,
                                        0,
                                    ),
                                ).start()
                                self.wait_for_target_start = current_time_ms
                        else:
                            logger.warning(
                                f"Target engagement failed after {max_click_retries} retries - advancing pattern"
                            )
                            self.automation_manager.advance_walk_pattern()
                            self.click_retry_count = 0
                            self.auto_walk_state = "move"

                elif self.auto_walk_state == "digging" and self.running:
                    if not self.target_engaged:
                        if self.target_disengaged_time == 0:
                            self.target_disengaged_time = current_time_ms
                    else:
                        self.target_disengaged_time = 0

            should_allow_clicking = True
            if get_param(self, "auto_walk_enabled"):
                should_allow_clicking = (
                    self.auto_walk_state == "digging"
                    and not self.automation_manager.is_selling
                    and self.target_engaged
                )
            else:
                should_allow_clicking = self.target_engaged

            post_click_blindness = get_param(self, "post_click_blindness")

            startup_grace_period = 100
            is_past_startup_grace = (
                not hasattr(self, "startup_time")
                or (current_time_ms - self.startup_time) > startup_grace_period
            )

            if (
                self.running
                and should_allow_clicking
                and current_time_ms >= self.blind_until
                and sweet_spot_center is not None
                and not self.click_lock.locked()
                and is_past_startup_grace
            ):
                should_click, click_delay, prediction_used, confidence = (
                    False,
                    0,
                    False,
                    0.0,
                )

                line_in_sweet_spot = (
                    sweet_spot_start is not None
                    and sweet_spot_end is not None
                    and sweet_spot_start <= line_pos <= sweet_spot_end
                )

                if get_param(self, "prediction_enabled") and line_pos != -1:
                    prediction_confidence_threshold = get_param(
                        self, "prediction_confidence_threshold"
                    )
                    system_latency = get_cached_system_latency(self) / 1000.0

                    is_moving_towards = (
                        line_pos < sweet_spot_center and velocity > 0
                    ) or (line_pos > sweet_spot_center and velocity < 0)

                    if is_moving_towards:
                        predicted_pos, prediction_time = (
                            self.velocity_calculator.predict_position(
                                line_pos, sweet_spot_center, self._current_time_cache
                            )
                        )

                        if prediction_time > 0:
                            distance_to_center = abs(predicted_pos - sweet_spot_center)
                            sweet_spot_radius = (
                                (sweet_spot_end or 0) - (sweet_spot_start or 0)
                            ) / 2

                            if distance_to_center <= sweet_spot_radius:
                                base_confidence = max(
                                    0.0, 1.0 - (distance_to_center / sweet_spot_radius)
                                )
                                velocity_confidence = (
                                    self.velocity_calculator.get_prediction_confidence(
                                        line_pos,
                                        sweet_spot_center,
                                        predicted_pos,
                                        prediction_time,
                                        game_fps,
                                    )
                                )

                                confidence = base_confidence * velocity_confidence

                                fps_adjusted_threshold = (
                                    prediction_confidence_threshold
                                    * (game_fps / 120.0) ** 0.15
                                )

                                if confidence >= fps_adjusted_threshold:
                                    fps_latency_adjustment = (
                                        system_latency * (120.0 / game_fps) * 0.8
                                    )
                                    sleep_duration = (
                                        prediction_time - fps_latency_adjustment
                                    )

                                    if sleep_duration > 0:
                                        should_click, click_delay, prediction_used = (
                                            True,
                                            sleep_duration,
                                            True,
                                        )

                if not should_click and line_in_sweet_spot:
                    should_click = True
                    confidence = 1.0

                if should_click:
                    self.automation_manager.update_click_activity()

                    self.blind_until = current_time_ms + post_click_blindness

                    if click_delay == 0:
                        save_debug_screenshot_wrapper(
                            self,
                            screenshot,
                            line_pos,
                            sweet_spot_start,
                            sweet_spot_end,
                            zone_y2,
                            velocity,
                            acceleration,
                            prediction_used,
                            confidence,
                        )
                        perform_instant_click(self)
                    else:
                        self.click_lock.acquire()

                        def delayed_click_with_debug():
                            save_debug_screenshot_wrapper(
                                self,
                                screenshot,
                                line_pos,
                                sweet_spot_start,
                                sweet_spot_end,
                                zone_y2,
                                velocity,
                                acceleration,
                                prediction_used,
                                confidence,
                            )
                            perform_click(self, click_delay)

                        threading.Thread(target=delayed_click_with_debug).start()

            if (
                get_param(self, "auto_walk_enabled")
                and self.auto_walk_state == "digging"
                and self.target_disengaged_time > 0
                and current_time_ms - self.target_disengaged_time > 1500
                and not self.automation_manager.is_selling
            ):
                self.dig_count += 1
                self.automation_manager.update_dig_activity()
                dig_completed_time = current_time_ms

                auto_sell_enabled = get_param(self, "auto_sell_enabled")
                sell_every_x_digs = get_param(self, "sell_every_x_digs")
                has_sell_button = (
                    self.automation_manager.sell_button_position is not None
                )

                logger.info(
                    f"Dig completed #{self.dig_count}: auto_sell_enabled={auto_sell_enabled}, sell_button_set={has_sell_button}, sell_every_x_digs={sell_every_x_digs}"
                )

                if (
                    auto_sell_enabled
                    and has_sell_button
                    and self.dig_count > 0
                    and self.dig_count % sell_every_x_digs == 0
                ):
                    pending_auto_sell = True
                    logger.info(
                        f"Auto-sell triggered! Will sell after {post_dig_delay}ms delay"
                    )

                self.auto_walk_state = "move"
                self.automation_manager.advance_walk_pattern()
                check_milestone_notifications(self)

                if get_param(self, "enable_item_detection"):
                    from core.notifications import check_item_notifications

                    check_item_notifications(self)

            elif not get_param(self, "auto_walk_enabled") and self.running:
                if self.target_engaged:
                    self.manual_dig_was_engaged = True
                    self.manual_dig_target_disengaged_time = 0
                elif self.manual_dig_was_engaged and not self.target_engaged:
                    if self.manual_dig_target_disengaged_time == 0:
                        self.manual_dig_target_disengaged_time = current_time_ms
                    elif (
                        current_time_ms - self.manual_dig_target_disengaged_time > 1500
                        and not self.automation_manager.is_selling
                    ):
                        self.dig_count += 1
                        self.automation_manager.update_dig_activity()
                        self.manual_dig_was_engaged = False
                        self.manual_dig_target_disengaged_time = 0

                        logger.info(f"Manual dig completed #{self.dig_count}")

                        auto_sell_enabled = get_param(self, "auto_sell_enabled")
                        sell_every_x_digs = get_param(self, "sell_every_x_digs")
                        has_sell_button = (
                            self.automation_manager.sell_button_position is not None
                        )

                        if (
                            auto_sell_enabled
                            and has_sell_button
                            and self.dig_count > 0
                            and self.dig_count % sell_every_x_digs == 0
                        ):
                            logger.info(
                                "Manual mode auto-sell triggered! Will sell immediately"
                            )
                            if self.automation_manager.is_auto_sell_ready():
                                threading.Thread(
                                    target=self.automation_manager.perform_auto_sell,
                                    daemon=True,
                                ).start()

                        check_milestone_notifications(self)

                        if get_param(self, "enable_item_detection"):
                            from core.notifications import check_item_notifications

                            check_item_notifications(self)

            if self.results_queue.empty():
                preview_img = screenshot.copy()
                if (
                    sweet_spot_center is not None
                    and self.smoothed_zone_x is not None
                    and self.smoothed_zone_w is not None
                    and sweet_spot_start is not None
                    and sweet_spot_end is not None
                ):
                    cv2.rectangle(
                        preview_img,
                        (int(self.smoothed_zone_x), 0),
                        (
                            int(self.smoothed_zone_x + self.smoothed_zone_w),
                            zone_y2 or height,
                        ),
                        (0, 255, 0),
                        2,
                    )
                    cv2.rectangle(
                        preview_img,
                        (int(sweet_spot_start), 0),
                        (int(sweet_spot_end), zone_y2 or height),
                        (0, 255, 255),
                        2,
                    )
                if line_pos != -1:
                    cv2.line(
                        preview_img, (line_pos, 0), (line_pos, height), (0, 0, 255), 1
                    )
                h, w = preview_img.shape[:2]
                thumbnail = cv2.resize(
                    preview_img,
                    (150, int(150 * h / w)),
                    interpolation=cv2.INTER_NEAREST,
                )

                debug_visualization = None
                if final_mask is not None:
                    if "detection_info" in locals() and detection_info:
                        method = detection_info.get("method", "")
                        if "Otsu" in method or "Color Picker" in method:
                            if (
                                "zone_detection_area" in locals()
                                and zone_detection_area is not None
                            ):
                                debug_visualization = zone_detection_area.copy()
                            else:
                                debug_visualization = (
                                    screenshot[:height_80, :].copy()
                                    if height_80 < screenshot.shape[0]
                                    else screenshot.copy()
                                )

                            if final_mask.shape[:2] == debug_visualization.shape[:2]:
                                overlay = debug_visualization.copy()
                                overlay[final_mask > 0] = [0, 255, 0]
                                debug_visualization = cv2.addWeighted(
                                    debug_visualization, 0.7, overlay, 0.3, 0
                                )
                            elif final_mask.shape[1] == debug_visualization.shape[1]:
                                mask_height = min(
                                    final_mask.shape[0], debug_visualization.shape[0]
                                )
                                overlay = debug_visualization.copy()
                                overlay[:mask_height][final_mask[:mask_height] > 0] = [
                                    0,
                                    255,
                                    0,
                                ]
                                debug_visualization = cv2.addWeighted(
                                    debug_visualization, 0.7, overlay, 0.3, 0
                                )

                overlay_info = {
                    "sweet_spot_center": sweet_spot_center,
                    "velocity": display_velocity,
                    "acceleration": acceleration,  #
                    "click_count": self.click_count,
                    "locked_color_hex": self.locked_color_hex,
                    "preview_thumbnail": thumbnail,
                    "dig_count": self.dig_count,
                    "automation_status": self.automation_manager.get_current_status(),
                    "sell_count": self.automation_manager.sell_count,
                    "target_engaged": self.target_engaged,
                    "line_detected": line_pos != -1,
                    # 'benchmark_fps': self.benchmark_fps,
                    "detection_info": (
                        detection_info
                        if "detection_info" in locals()
                        else {"method": "Unknown", "threshold": "N/A"}
                    ),
                }
                try:
                    self.results_queue.put_nowait(
                        (
                            preview_img,
                            (
                                debug_visualization
                                if debug_visualization is not None
                                else final_mask
                            ),
                            overlay_info,
                        )
                    )
                except queue.Full:
                    pass

            # Benchmarking
            now = time.time()
            frame_time = frame_start_time - self.last_frame_time
            self.last_frame_time = frame_start_time

            self.frame_times.append(frame_time)

            if now - self.last_report_time >= self.report_interval:
                if self.frame_times:
                    avg_frame_time = sum(self.frame_times) / len(self.frame_times)
                    self.benchmark_fps = (
                        int(1.0 / avg_frame_time) if avg_frame_time > 0 else 0
                    )
                    # logger.debug(f"Benchmark: {self.benchmark_fps} FPS (avg frame time: {avg_frame_time*1000:.2f}ms)")
                    self.frame_times.clear()
                self.last_report_time = now
            elapsed = time.perf_counter() - frame_start_time

            if screenshot_delay > elapsed:
                time.sleep(screenshot_delay - elapsed)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        app = DigTool()
        app.run()
    except Exception as e:
        try:
            logger.error(f"Application failed to start: {e}")
            logger._save_latest_log()
        except:
            pass
        raise
