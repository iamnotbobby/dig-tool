import cv2
import numpy as np
import threading
import mss
import os
from concurrent.futures import ThreadPoolExecutor
from utils.debug_logger import logger


class ScreenCapture:
    def __init__(self):
        self._last_bbox = None
        self._cached_monitor = None
        self._thread_local = threading.local()
        self._reuse_array = None
        self._last_size = None
        self._raw_buffer = None
        self._bgr_view = None
        self._capture_executor = None
        self._region_cache = {}
        os.environ["MSS_COMPRESSION"] = "0"
        self._capture_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="ScreenCapture"
        )

    def _get_sct(self):
        if not hasattr(self._thread_local, "sct"):
            self._thread_local.sct = mss.mss(compression_level=0)
        return self._thread_local.sct

    def capture(self, bbox=None, region_key=None):
        if not bbox:
            return None
        left, top, right, bottom = bbox
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return None
        try:
            current_size = (width, height)
            cache_key = (left, top, width, height)
            if region_key and region_key in self._region_cache:
                cached_monitor = self._region_cache[region_key]
                if (
                    cached_monitor["left"] == left
                    and cached_monitor["top"] == top
                    and cached_monitor["width"] == width
                    and cached_monitor["height"] == height
                ):
                    self._cached_monitor = cached_monitor
                else:
                    self._region_cache[region_key] = {
                        "top": top,
                        "left": left,
                        "width": width,
                        "height": height,
                    }
                    self._cached_monitor = self._region_cache[region_key]
            else:
                if self._last_bbox != cache_key or self._cached_monitor is None:
                    self._cached_monitor = {
                        "top": top,
                        "left": left,
                        "width": width,
                        "height": height,
                    }
                    self._last_bbox = cache_key
                    if region_key:
                        self._region_cache[region_key] = self._cached_monitor
            if self._last_size != current_size:
                self._reuse_array = None
                self._raw_buffer = None
                self._bgr_view = None
                self._last_size = current_size
            sct = self._get_sct()
            if self._raw_buffer is None:
                total_pixels = width * height
                self._raw_buffer = np.empty(total_pixels * 4, dtype=np.uint8)
                self._reuse_array = np.empty((height, width, 3), dtype=np.uint8)
            screenshot = sct.grab(self._cached_monitor)
            raw_data = np.frombuffer(screenshot.bgra, dtype=np.uint8)
            if raw_data.size == width * height * 4:
                bgra_view = raw_data.reshape((height, width, 4))
                self._reuse_array[:, :, 0] = bgra_view[:, :, 2]
                self._reuse_array[:, :, 1] = bgra_view[:, :, 1]
                self._reuse_array[:, :, 2] = bgra_view[:, :, 0]
            else:
                img_data = np.frombuffer(screenshot.rgb, dtype=np.uint8)
                img_rgb = img_data.reshape((height, width, 3))
                np.copyto(self._reuse_array, img_rgb[:, :, ::-1])
            return self._reuse_array
        except Exception as e:
            logger.error(f"MSS capture failed: {e}")
            return None

    def capture_async(self, bbox=None, region_key=None):
        if not self._capture_executor:
            return self.capture(bbox, region_key)
        future = self._capture_executor.submit(self.capture, bbox, region_key)
        return future

    def clear_cache(self):
        self._region_cache.clear()

    def close(self):
        if self._capture_executor:
            self._capture_executor.shutdown(wait=True)
        if hasattr(self._thread_local, "sct"):
            try:
                self._thread_local.sct.close()
            except:
                pass

    def capture_region(self, bbox=None, focus_area=None, reduction_factor=0.8):
        if not bbox or not focus_area:
            return self.capture(bbox)
        left, top, right, bottom = bbox
        full_width, full_height = right - left, bottom - top
        focus_x, focus_y, focus_w, focus_h = focus_area
        reduced_width = int(full_width * reduction_factor)
        reduced_height = int(full_height * reduction_factor)
        center_x = focus_x + focus_w // 2
        center_y = focus_y + focus_h // 2
        new_left = max(left, left + center_x - reduced_width // 2)
        new_top = max(top, top + center_y - reduced_height // 2)
        new_right = min(right, new_left + reduced_width)
        new_bottom = min(bottom, new_top + reduced_height)
        if new_right - new_left < 200:
            new_left = max(left, center_x - 100)
            new_right = min(right, new_left + 200)
        if new_bottom - new_top < 200:
            new_top = max(top, center_y - 100)
            new_bottom = min(bottom, new_top + 200)
        reduced_bbox = (new_left, new_top, new_right, new_bottom)
        return self.capture(reduced_bbox, region_key="region")

    def capture_diff(self, bbox=None, last_screenshot=None, change_threshold=0.1):
        if last_screenshot is None:
            return self.capture(bbox)
        left, top, right, bottom = bbox
        sample_width, sample_height = min(100, right - left), min(100, bottom - top)
        sample_bbox = (left, top, left + sample_width, top + sample_height)
        sample = self.capture(sample_bbox, region_key="sample")
        if sample is None:
            return self.capture(bbox)
        if hasattr(self, "_last_sample") and self._last_sample is not None:
            diff = cv2.absdiff(sample, self._last_sample)
            change_amount = np.mean(diff) / 255.0
            if change_amount < change_threshold:
                return last_screenshot
        self._last_sample = sample.copy()
        return self.capture(bbox)
