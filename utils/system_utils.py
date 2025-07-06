import importlib

import cv2
import numpy as np
import os
import sys
import tkinter as tk
from tkinter import messagebox
from pynput.mouse import Controller, Button


def check_dependencies():
    required_packages = {
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'PIL': 'Pillow',
        'pynput': 'pynput',
        'requests': 'requests',
        'mss': 'mss'
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

def send_click():
    mouse = Controller()
    mouse.click(Button.left)


import mss

def get_screen_resolution():
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        return monitor["width"], monitor["height"]


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
        if filepath.lower().endswith('.jpg') or filepath.lower().endswith('.jpeg'):
            cv2.imwrite(filepath, image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        else:
            cv2.imwrite(filepath, image)
        return True
    except Exception as e:
        print(f"Failed to save image: {e}")
        return False


def load_image(filepath):
    try:
        return cv2.imread(filepath)
    except Exception as e:
        print(f"Failed to load image: {e}")
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
                canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
                return canvas
            else:
                return resized
        else:
            return cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)

    except Exception as e:
        print(f"Failed to resize image: {e}")
        return image


def create_directory(path):
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Failed to create directory {path}: {e}")
        return False


def get_file_timestamp():
    import time
    return int(time.time())


def format_timestamp(timestamp=None):
    import time
    if timestamp is None:
        timestamp = time.time()
    return time.strftime('%Y%m%d_%H%M%S', time.localtime(timestamp))


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
        print(f"Cleanup failed: {e}")
        return 0


def get_system_info():
    try:
        import platform
        import psutil

        info = {
            'os': platform.system(),
            'os_version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'screen_resolution': get_screen_resolution()
        }
        return info
    except Exception as e:
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
            pass

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