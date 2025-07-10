import importlib
import time
import cv2
import numpy as np
import win32gui, win32ui, win32con, win32api
import os
import sys
import ctypes
import tkinter as tk
from tkinter import messagebox
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


def send_click():
    try:
        user32 = ctypes.windll.user32
        INPUT_MOUSE = 0
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.wintypes.DWORD),
                ("dwFlags", ctypes.wintypes.DWORD),
                ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG)),
            ]

        class INPUT(ctypes.Structure):
            class _INPUT(ctypes.Union):
                _fields_ = [("mi", MOUSEINPUT)]

            _anonymous_ = ("_input",)
            _fields_ = [("type", ctypes.wintypes.DWORD), ("_input", _INPUT)]

        input_down = INPUT()
        input_down.type = INPUT_MOUSE
        input_down.mi.dx = 0
        input_down.mi.dy = 0
        input_down.mi.mouseData = 0
        input_down.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
        input_down.mi.time = 0
        input_down.mi.dwExtraInfo = None
        input_up = INPUT()
        input_up.type = INPUT_MOUSE
        input_up.mi.dx = 0
        input_up.mi.dy = 0
        input_up.mi.mouseData = 0
        input_up.mi.dwFlags = MOUSEEVENTF_LEFTUP
        input_up.mi.time = 0
        input_up.mi.dwExtraInfo = None
        inputs = (INPUT * 2)(input_down, input_up)
        user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
        return True
    except Exception as e:
        try:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return True
        except Exception as e2:
            logger.error(f"Win32API click failed: {e}, {e2}")
            return False



class ScreenCapture:
    def __init__(self):
        self.hwnd = win32gui.GetDesktopWindow()
        self.hwindc = None
        self.srcdc = None
        self.memdc = None
        self.bmp = None
        self._initialized = False
        self._last_bbox = None
        self._last_width = 0
        self._last_height = 0

    def _initialize_dc(self, width, height):
        try:
            self.hwindc = win32gui.GetWindowDC(self.hwnd)
            self.srcdc = win32ui.CreateDCFromHandle(self.hwindc)
            self.memdc = self.srcdc.CreateCompatibleDC()
            self.bmp = win32ui.CreateBitmap()
            self.bmp.CreateCompatibleBitmap(self.srcdc, width, height)
            self.memdc.SelectObject(self.bmp)
            self._initialized = True
            self._last_width = width
            self._last_height = height
        except Exception:
            self._cleanup()
            return False
        return True

    def _cleanup(self):
        try:
            if self.srcdc:
                self.srcdc.DeleteDC()
            if self.memdc:
                self.memdc.DeleteDC()
            if self.hwindc:
                win32gui.ReleaseDC(self.hwnd, self.hwindc)
            if self.bmp:
                win32gui.DeleteObject(self.bmp.GetHandle())
        except Exception:
            pass
        self._initialized = False

    def capture(self, bbox=None):
        if not bbox:
            return None
        left, top, right, bottom = bbox
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return None
        if (
            self._last_bbox != bbox
            or not self._initialized
            or width != self._last_width
            or height != self._last_height
        ):
            self._cleanup()
            self._last_bbox = bbox
        if not self._initialized:
            if not self._initialize_dc(width, height):
                return None
        try:
            self.memdc.BitBlt(
                (0, 0), (width, height), self.srcdc, (left, top), win32con.SRCCOPY
            )
            signedIntsArray = self.bmp.GetBitmapBits(True)
            img = np.frombuffer(signedIntsArray, dtype="uint8").reshape(
                (height, width, 4)
            )
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception:
            self._cleanup()
            return None

    def close(self):
        self._cleanup()


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


def measure_system_latency(game_area=None):
    try:
        pipeline_measurements = []
        screenshot_measurements = []
        click_measurements = []
        test_iterations = 10
        if game_area:
            x1, y1, x2, y2 = game_area
            w, h = x2 - x1, y2 - y1
            test_region = (x1, y1, x1 + min(w, 200), y1 + min(h, 100))
        else:
            test_region = (100, 100, 300, 200)
        from utils.screen_capture import ScreenCapture

        test_screen_grabber = ScreenCapture()
        for _ in range(5):
            test_screen_grabber.capture(bbox=test_region, region_key="latency_warmup")
            time.sleep(0.002)
        test_screen_grabber.clear_cache()
        for i in range(test_iterations):
            pipeline_start = time.perf_counter()
            screenshot_start = time.perf_counter()
            try:
                screenshot = test_screen_grabber.capture(
                    bbox=test_region, region_key=f"latency_test_{i}"
                )
                if screenshot is not None:
                    img_array = screenshot
                else:
                    continue
            except:
                try:
                    import PIL.ImageGrab

                    screenshot = PIL.ImageGrab.grab(bbox=test_region)
                    img_array = np.array(screenshot)
                except:
                    continue
            screenshot_time = time.perf_counter()
            try:
                if len(img_array.shape) == 3:
                    hsv = cv2.cvtColor(img_array, cv2.COLOR_BGR2HSV)
                    saturation = hsv[:, :, 1]
                    _, mask = cv2.threshold(saturation, 100, 255, cv2.THRESH_BINARY)
            except:
                time.sleep(0.001)
            processing_time = time.perf_counter()
            click_start = time.perf_counter()
            try:
                current_pos = win32gui.GetCursorPos()
                test_x, test_y = current_pos[0], current_pos[1]
            except:
                pass
            click_time = time.perf_counter()
            screenshot_latency = (screenshot_time - screenshot_start) * 1000
            processing_latency = (processing_time - screenshot_time) * 1000
            click_latency = (click_time - click_start) * 1000
            total_pipeline = (click_time - pipeline_start) * 1000
            pipeline_measurements.append(total_pipeline)
            screenshot_measurements.append(screenshot_latency)
            click_measurements.append(click_latency)
            time.sleep(0.005)
        for _ in range(test_iterations):
            click_start = time.perf_counter()
            try:
                current_pos = win32gui.GetCursorPos()
                test_x, test_y = current_pos[0], current_pos[1]
            except:
                continue
            click_end = time.perf_counter()
            actual_click_latency = (click_end - click_start) * 1000
            click_measurements.append(actual_click_latency)
            time.sleep(0.01)
        test_screen_grabber.close()

        def robust_average(measurements):
            if not measurements:
                return 0
            measurements.sort()
            if len(measurements) >= 6:
                trim_count = max(1, len(measurements) // 6)
                trimmed = measurements[trim_count:-trim_count]
            elif len(measurements) >= 3:
                trimmed = measurements[1:-1]
            else:
                trimmed = measurements
            return sum(trimmed) / len(trimmed) if trimmed else measurements[0]

        pipeline_latency = robust_average(pipeline_measurements)
        screenshot_latency = robust_average(screenshot_measurements)
        click_latency = robust_average(click_measurements)
        calibration_factor = 1.35
        calibrated_pipeline = pipeline_latency * calibration_factor
        calibrated_screenshot = screenshot_latency * calibration_factor
        total_latency = calibrated_pipeline
        try:
            try:
                device = win32api.EnumDisplaySettings(None, -1)
                refresh_rate = device.DisplayFrequency
            except:
                refresh_rate = 60
            if refresh_rate >= 240:
                display_latency = 4.17
            elif refresh_rate >= 165:
                display_latency = 6.06
            elif refresh_rate >= 144:
                display_latency = 6.94
            elif refresh_rate >= 120:
                display_latency = 8.33
            elif refresh_rate >= 75:
                display_latency = 13.33
            else:
                display_latency = 16.67
        except:
            display_latency = 8.33
        system_overhead = 3.0
        total_latency += display_latency + system_overhead
        safety_margin = total_latency * 0.15
        final_latency = total_latency + safety_margin
        return max(5, min(150, int(final_latency)))
    except Exception:
        return 35
