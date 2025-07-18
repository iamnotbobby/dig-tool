import importlib
import time
import cv2
import numpy as np
import win32gui, win32ui, win32con, win32api
import os
import sys
import ctypes
import ctypes.wintypes
import tkinter as tk
from tkinter import messagebox
import threading
import gc
import keyboard
from utils.debug_logger import logger


def check_dependencies():
    required_packages = {
        "cv2": "opencv-python",
        "numpy": "numpy",
        "PIL": "Pillow",
        "keyboard": "keyboard",
        "win32gui": "pywin32",
        "pynput": "pynput",
        "requests": "requests",
        "autoit": "pyautoit",
        "mss": "mss",
    }
    missing_packages = []
    for module, package in required_packages.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing_packages.append(package)
    if missing_packages:
        logger.error("Missing required packages:")
        for package in missing_packages:
            logger.error(f"  pip install {package}")
        logger.error("\nPlease install the missing packages and try again.")
        sys.exit(1)


def get_display_scale():
    try:
        user32 = ctypes.windll.user32

        if hasattr(user32, "GetDpiForSystem"):
            try:
                system_dpi = user32.GetDpiForSystem()
                scale_percent = int((system_dpi * 100) / 96)
                logger.debug(
                    f"Display scale detection (GetDpiForSystem): dpi={system_dpi}, scale={scale_percent}%"
                )
                if scale_percent != 100:
                    return scale_percent
            except:
                pass

        gdi32 = ctypes.windll.gdi32
        dc = user32.GetDC(0)

        logical_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN (scaled)
        logical_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN (scaled)

        physical_width = gdi32.GetDeviceCaps(dc, 8)  # HORZRES
        physical_height = gdi32.GetDeviceCaps(dc, 10)  # VERTRES

        user32.ReleaseDC(0, dc)

        if physical_width > 0 and logical_width > 0:
            scale_percent = int((logical_width * 100) / physical_width)
            logger.debug(
                f"Display scale detection (dimensions): logical={logical_width}x{logical_height}, physical={physical_width}x{physical_height}, scale={scale_percent}%"
            )
            return scale_percent
        else:
            logger.warning("Could not get valid dimensions for scale detection")
            return 100
    except Exception as e:
        logger.warning(f"Display scale detection failed: {e}")
        return 100


def check_display_scale():
    try:
        scale = get_display_scale()
        logger.info(f"Detected display scale: {scale}%")

        if scale != 100:
            root = tk.Tk()
            root.withdraw()
            result = messagebox.askquestion(
                "Display Scaling Warning",
                f"Your Windows display scaling (DPI) is set to {scale}%.\n\n"
                "For best results, set display scaling to 100% (Default) in Windows Display Settings.\n"
                "Detection may not work properly with scaling enabled.\n\n"
                "To fix this:\n"
                "1. Right-click on desktop → Display settings\n"
                "2. Set 'Scale and layout' to 100%\n"
                "3. Restart this application\n\n"
                "Do you want to continue anyway?",
                icon="warning",
            )
            root.destroy()

            if result == "no":
                logger.info("User chose to exit due to display scaling")
                sys.exit(0)
            else:
                logger.warning(
                    f"User chose to continue with {scale}% display scaling - detection may be unreliable"
                )
        else:
            logger.info("Display scaling check passed (100%)")
    except Exception as e:
        logger.warning(f"Could not detect display scaling: {e}")
        pass


_dig_tool_instance = None


def set_dig_tool_instance(instance):
    global _dig_tool_instance
    _dig_tool_instance = instance


def send_click_win32api():
    try:
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        return True
    except Exception as e:
        logger.error(f"Win32API click failed: {e}")
        return False


def send_click_ahk():  # NON-FUNC FOR NOW
    return send_click_win32api()


def send_click():
    global _dig_tool_instance
    
    if _dig_tool_instance:
        try:
            from utils.config_management import get_param
            click_method = get_param(_dig_tool_instance, 'click_method')
        except:
            click_method = 'win32api'
    else:
        click_method = 'win32api'
    
    if click_method == 'ahk':
        success = send_click_ahk()
        if not success:
            logger.warning("AHK click failed, falling back to Win32API")
            success = send_click_win32api()
        return success
    else:
        return send_click_win32api()


def get_window_list():
    windows = []

    def enum_windows_callback(hwnd, windows_list):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            if window_text:
                rect = win32gui.GetWindowRect(hwnd)
                windows_list.append(
                    {
                        "hwnd": hwnd,
                        "title": window_text,
                        "rect": rect,
                        "width": rect[2] - rect[0],
                        "height": rect[3] - rect[1],
                    }
                )
        return True

    win32gui.EnumWindows(enum_windows_callback, windows)
    return windows


def focus_window(hwnd):
    try:
        win32gui.SetForegroundWindow(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        return True
    except Exception as e:
        logger.error(f"Failed to focus window: {e}")
        return False


def get_window_info(hwnd):
    try:
        title = win32gui.GetWindowText(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        is_visible = win32gui.IsWindowVisible(hwnd)
        return {
            "hwnd": hwnd,
            "title": title,
            "class_name": class_name,
            "rect": rect,
            "width": rect[2] - rect[0],
            "height": rect[3] - rect[1],
            "visible": is_visible,
        }
    except Exception as e:
        logger.error(f"Failed to get window info: {e}")
        return None


def find_window_by_title(title_pattern, exact_match=False):
    windows = get_window_list()
    for window in windows:
        if exact_match:
            if window["title"] == title_pattern:
                return window
        else:
            if title_pattern.lower() in window["title"].lower():
                return window
    return None


def find_and_focus_roblox_window():
    """Find and focus the Roblox window."""
    try:
        roblox_patterns = ["Roblox", "roblox"]
        roblox_window = None

        for pattern in roblox_patterns:
            roblox_window = find_window_by_title(pattern, exact_match=False)
            if roblox_window:
                logger.debug(f"Found Roblox window: {roblox_window['title']}")
                break

        if roblox_window:
            success = focus_window_no_resize(roblox_window["hwnd"])
            if success:
                logger.info(
                    f"Successfully focused Roblox window: {roblox_window['title']}"
                )
                time.sleep(0.2)
                return True
            else:
                logger.warning("Failed to focus Roblox window")
                return False
        else:
            logger.warning("Roblox window not found")
            return False

    except Exception as e:
        logger.error(f"Error focusing Roblox window: {e}")
        return False


def focus_window_no_resize(hwnd):
    """Focus a window without resizing it."""
    try:
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        logger.error(f"Failed to focus window: {e}")
        return False


def focus_roblox_window_legacy():
    """Legacy method name for compatibility - find and focus Roblox window."""
    try:
        windows = get_window_list()
        roblox_patterns = ["Roblox", "roblox"]

        for pattern in roblox_patterns:
            for window in windows:
                if pattern.lower() in window["title"].lower():
                    if focus_window_no_resize(window["hwnd"]):
                        logger.info(
                            f"Successfully focused Roblox window: {window['title']}"
                        )
                        return True
                    else:
                        logger.warning(
                            f"Found Roblox window but failed to focus: {window['title']}"
                        )

        logger.warning("Roblox window not found")
        return False

    except Exception as e:
        logger.error(f"Error focusing Roblox window: {e}")
        return False


def capture_window(hwnd):
    try:
        rect = win32gui.GetWindowRect(hwnd)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        hwindc = win32gui.GetWindowDC(hwnd)
        srcdc = win32ui.CreateDCFromHandle(hwindc)
        memdc = srcdc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(srcdc, width, height)
        memdc.SelectObject(bmp)
        memdc.BitBlt((0, 0), (width, height), srcdc, (0, 0), win32con.SRCCOPY)
        signedIntsArray = bmp.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype="uint8").reshape((height, width, 4))
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        srcdc.DeleteDC()
        memdc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwindc)
        win32gui.DeleteObject(bmp.GetHandle())
        return img
    except Exception as e:
        logger.error(f"Window capture failed: {e}")
        return None

def get_screen_resolution():
    try:
        user32 = ctypes.windll.user32
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
        return width, height
    except Exception:
        return 1920, 1080


def is_point_in_rect(point, rect):
    x, y = point
    left, top, right, bottom = rect
    return left <= x <= right and top <= y <= bottom


def rect_intersection(rect1, rect2):
    left = max(rect1[0], rect2[0])
    top = max(rect1[1], rect2[1])
    right = min(rect1[2], rect2[2])
    bottom = min(rect1[3], rect2[3])
    if left < right and top < bottom:
        return (left, top, right, bottom)
    return None


def normalize_rect(rect):
    x1, y1, x2, y2 = rect
    return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def expand_rect(rect, padding):
    left, top, right, bottom = rect
    return (left - padding, top - padding, right + padding, bottom + padding)


def clamp_rect_to_screen(rect):
    screen_width, screen_height = get_screen_resolution()
    left, top, right, bottom = rect
    left = max(0, left)
    top = max(0, top)
    right = min(screen_width, right)
    bottom = min(screen_height, bottom)
    return (left, top, right, bottom)


def save_image(image, filepath, quality=95):
    try:
        if filepath.lower().endswith(".jpg") or filepath.lower().endswith(".jpeg"):
            cv2.imwrite(filepath, image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        else:
            cv2.imwrite(filepath, image)
        return True
    except Exception as e:
        logger.error(f"Failed to save image: {e}")
        return False


def load_image(filepath):
    try:
        return cv2.imread(filepath)
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        return None


def resize_image(image, target_size, maintain_aspect=True):
    try:
        if maintain_aspect:
            h, w = image.shape[:2]
            target_w, target_h = target_size
            scale = min(target_w / w, target_h / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            if new_w != target_w or new_h != target_h:
                canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
                y_offset = (target_h - new_h) // 2
                x_offset = (target_w - new_w) // 2
                canvas[y_offset : y_offset + new_h, x_offset : x_offset + new_w] = (
                    resized
                )
                return canvas
            else:
                return resized
        else:
            return cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)
    except Exception as e:
        logger.error(f"Failed to resize image: {e}")
        return image


def create_directory(path):
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False


def get_file_timestamp():
    import time

    return int(time.time())


def format_timestamp(timestamp=None):
    import time

    if timestamp is None:
        timestamp = time.time()
    return time.strftime("%Y%m%d_%H%M%S", time.localtime(timestamp))


def cleanup_old_files(directory, pattern, max_age_days=7):
    import glob
    import time

    try:
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        files = glob.glob(os.path.join(directory, pattern))
        deleted_count = 0
        for file_path in files:
            try:
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    deleted_count += 1
            except Exception:
                continue
        return deleted_count
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 0


def get_system_info():
    try:
        import platform
        import psutil

        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "screen_resolution": get_screen_resolution(),
        }
        return info
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return {}


def log_performance(func):
    import time
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = (end_time - start_time) * 1000
        if execution_time > 16.67:
            logger.warning(
                f"Performance warning: {func.__name__} took {execution_time:.2f}ms"
            )
        return result

    return wrapper


class PerformanceMonitor:
    def __init__(self, window_size=100):
        self.window_size = window_size
        self.frame_times = []
        self.last_time = None

    def tick(self):
        import time

        current_time = time.perf_counter()
        if self.last_time is not None:
            frame_time = current_time - self.last_time
            self.frame_times.append(frame_time)
            if len(self.frame_times) > self.window_size:
                self.frame_times.pop(0)
        self.last_time = current_time

    def get_fps(self):
        if not self.frame_times:
            return 0
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0

    def get_frame_time_ms(self):
        if not self.frame_times:
            return 0
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return avg_frame_time * 1000


def measure_system_latency(game_area=None, cam=None):
    """
    Measures system latency components in a non-intrusive way.
    
    This function measures:
    - Screenshot capture time
    - Image processing time  
    - System API call overhead (without actual mouse clicks)
    - Display refresh latency
    
    The measurement is designed to be non-intrusive - it does NOT perform
    actual mouse clicks that would interfere with the user's experience.
    Instead, it measures the timing of system API calls that would be
    involved in clicking operations.
    """
    try:
        screenshot_measurements = []
        processing_measurements = []
        click_measurements = []
        test_iterations = 15
        
        if game_area:
            x1, y1, x2, y2 = game_area
            w, h = x2 - x1, y2 - y1
            test_region = (x1, y1, x1 + min(w, 200), y1 + min(h, 100))
        else:
            test_region = (100, 100, 300, 200)
        
        from utils.screen_capture import ScreenCapture

        test_screen_grabber = ScreenCapture()
        
        for _ in range(3):
            test_screen_grabber.capture(bbox=test_region, region_key="latency_warmup")
            time.sleep(0.001)
        test_screen_grabber.clear_cache()
        
        for i in range(test_iterations):
            screenshot_start = time.perf_counter()
            try:
                screenshot = test_screen_grabber.capture(
                    bbox=test_region, region_key=f"latency_test_{i}"
                )
                if screenshot is None:
                    continue
                    
                screenshot_time = time.perf_counter()
                screenshot_latency = (screenshot_time - screenshot_start) * 1000
                screenshot_measurements.append(screenshot_latency)
                
                processing_start = time.perf_counter()
                if len(screenshot.shape) == 3:
                    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                    _, mask = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
                processing_time = time.perf_counter()
                processing_latency = (processing_time - processing_start) * 1000
                processing_measurements.append(processing_latency)
                
            except Exception:
                continue
            
            time.sleep(0.002)
        
        for _ in range(test_iterations):
            click_start = time.perf_counter()
            try:
                # Measure system call overhead without actually clicking
                # This measures the timing of API calls that would be used for clicking
                # without actually interfering with the user's experience
                
                # Get current cursor position (simulates click preparation)
                point = ctypes.wintypes.POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.pointer(point))
                
                # Simulate the timing overhead of preparing click coordinates
                # without actually sending mouse events
                current_pos = (point.x, point.y)
                
                # Measure time for system API calls that clicking would use
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                
            except Exception:
                continue
            click_end = time.perf_counter()
            click_latency = (click_end - click_start) * 1000
            click_measurements.append(click_latency)
            time.sleep(0.005)
        
        test_screen_grabber.close()

        def robust_average(measurements):
            if not measurements:
                return 0
            measurements.sort()
            if len(measurements) >= 10:
                trim_count = max(1, len(measurements) // 10)
                trimmed = measurements[trim_count:-trim_count]
            elif len(measurements) >= 5:
                trimmed = measurements[1:-1]
            else:
                trimmed = measurements
            return sum(trimmed) / len(trimmed) if trimmed else 0

        avg_screenshot = robust_average(screenshot_measurements)
        avg_processing = robust_average(processing_measurements)
        avg_click = robust_average(click_measurements)
        
        base_latency = avg_screenshot + avg_processing + avg_click
        
        try:
            device = win32api.EnumDisplaySettings(None, -1)
            refresh_rate = device.DisplayFrequency
        except:
            refresh_rate = 60
            
        if refresh_rate >= 240:
            display_latency = 2.08  # ~4.17ms / 2 (average frame time)
        elif refresh_rate >= 165:
            display_latency = 3.03  # ~6.06ms / 2
        elif refresh_rate >= 144:
            display_latency = 3.47  # ~6.94ms / 2
        elif refresh_rate >= 120:
            display_latency = 4.17  # ~8.33ms / 2
        elif refresh_rate >= 75:
            display_latency = 6.67  # ~13.33ms / 2
        else:
            display_latency = 8.33  # ~16.67ms / 2
        
        # System overhead (thread switching, OS scheduling)
        system_overhead = 2.0
        
        total_latency = base_latency + display_latency + system_overhead
        
        # Add a small safety margin (5%)
        safety_margin = total_latency * 0.05
        final_latency = total_latency + safety_margin

        # Ensure reasonable bounds
        result = max(3, min(100, int(final_latency)))
        
        logger.debug(f"Latency measurement: screenshot={avg_screenshot:.1f}ms, processing={avg_processing:.1f}ms, click={avg_click:.1f}ms, display={display_latency:.1f}ms, total={result}ms")
        
        return result
        
    except Exception as e:
        logger.error(f"System latency measurement failed: {e}")
        return 25


def calculate_window_dimensions():
    """Calculate appropriate window dimensions based on screen resolution."""
    screen_width, screen_height = get_screen_resolution()
    
    if screen_width <= 1366 and screen_height <= 768:
        width = 480
        base_height = 480  
    elif screen_width <= 1600 and screen_height <= 900:
        width = 490
        base_height = 510 
    elif screen_width <= 1920 and screen_height <= 1080:
        width = 500
        base_height = 550  
    elif screen_width <= 2560 and screen_height <= 1440:
        width = 520
        base_height = 630
    elif screen_width <= 3840 and screen_height <= 2160:
        width = 540
        base_height = 730
    else:
        width = 560
        base_height = 780


    width = max(width, 400)
    base_height = max(base_height, 480) 
    
   
    width = min(width, 600)
    base_height = min(base_height, int(screen_height * 0.85))  # Max 85% of screen height
    
    return width, base_height


def get_cached_system_latency(dig_tool_instance):
    """Get cached system latency or measure if cache is expired."""
    if hasattr(dig_tool_instance, "_cached_latency") and hasattr(
        dig_tool_instance, "_latency_measurement_time"
    ):
        if time.time() - dig_tool_instance._latency_measurement_time < 300:
            return dig_tool_instance._cached_latency

    if not hasattr(dig_tool_instance, "_cached_latency") or not hasattr(
        dig_tool_instance, "_latency_measurement_time"
    ):
        logger.info("Measuring system latency (one-time measurement)...")
        measured_latency = measure_system_latency_for_instance(dig_tool_instance)
        dig_tool_instance._cached_latency = measured_latency
        dig_tool_instance._latency_measurement_time = time.time()
        return measured_latency

    return dig_tool_instance._cached_latency


def force_latency_remeasurement(dig_tool_instance):
    """Force a new latency measurement."""
    if hasattr(dig_tool_instance, "_latency_measurement_time"):
        dig_tool_instance._latency_measurement_time = 0

    new_latency = measure_system_latency_for_instance(dig_tool_instance)
    dig_tool_instance._cached_latency = new_latency
    return new_latency

def measure_system_latency_for_instance(dig_tool_instance):
    """Measure system latency for a DigTool instance with caching."""
    import time
    
    if hasattr(dig_tool_instance, "_measured_latency") and hasattr(
        dig_tool_instance, "_latency_measurement_time"
    ):
        if time.time() - dig_tool_instance._latency_measurement_time < 30:
            return dig_tool_instance._measured_latency
          
    game_area = getattr(dig_tool_instance, "game_area", None)
    dig_tool_instance._measured_latency = measure_system_latency(game_area, dig_tool_instance.cam)
    dig_tool_instance._latency_measurement_time = time.time()
    return dig_tool_instance._measured_latency


def perform_final_cleanup(dig_tool_instance):
    """Perform final cleanup before application exit."""
    if dig_tool_instance.overlay:
        dig_tool_instance.overlay.destroy_overlay()
        dig_tool_instance.overlay = None
    if dig_tool_instance.autowalk_overlay:
        dig_tool_instance.autowalk_overlay.destroy_overlay()
        dig_tool_instance.autowalk_overlay = None
    if dig_tool_instance.color_modules_overlay:
        dig_tool_instance.color_modules_overlay.destroy_overlay()
        dig_tool_instance.color_modules_overlay = None

    if hasattr(dig_tool_instance, "automation_manager") and dig_tool_instance.automation_manager:
        dig_tool_instance.automation_manager.cleanup()
        del dig_tool_instance.automation_manager
        dig_tool_instance.automation_manager = None

    try:
        keyboard.unhook_all()
    except:
        pass

    try:
        dig_tool_instance.cam.close()
    except:
        pass

    for _ in range(3):
        gc.collect()

    try:
        import comtypes
        comtypes.CoUninitialize()
    except:
        pass

    dig_tool_instance.root.after(100, lambda: force_exit(dig_tool_instance))


def force_exit(dig_tool_instance):
    """Force application exit."""
    try:
        dig_tool_instance.root.destroy()
    except:
        pass

    def delayed_exit():
        time.sleep(0.2)
        os._exit(0)

    exit_thread = threading.Thread(target=delayed_exit, daemon=True)
    exit_thread.start()


def update_time_cache(dig_tool_instance):
    """Update the time cache for performance optimization."""
    now = time.time()
    if now - dig_tool_instance._last_time_update > 0.001:
        dig_tool_instance._current_time_cache = now
        dig_tool_instance._current_time_ms_cache = now * 1000
        dig_tool_instance._last_time_update = now