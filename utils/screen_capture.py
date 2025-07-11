import cv2
import numpy as np
import win32gui, win32ui, win32con


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
                self.srcdc = None
        except Exception:
            pass
        try:
            if self.memdc:
                self.memdc.DeleteDC()
                self.memdc = None
        except Exception:
            pass
        try:
            if self.hwindc:
                win32gui.ReleaseDC(self.hwnd, self.hwindc)
                self.hwindc = None
        except Exception:
            pass
        try:
            if self.bmp:
                win32gui.DeleteObject(self.bmp.GetHandle())
                self.bmp = None
        except Exception:
            pass
        self._initialized = False

    def capture(self, bbox=None):
        if not bbox: return None
        left, top, right, bottom = bbox
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0: return None

        if (self._last_bbox != bbox or not self._initialized or
                width != self._last_width or height != self._last_height):
            self._cleanup()
            self._last_bbox = bbox

        if not self._initialized:
            if not self._initialize_dc(width, height): return None

        try:
            self.memdc.BitBlt((0, 0), (width, height), self.srcdc, (left, top), win32con.SRCCOPY)
            signedIntsArray = self.bmp.GetBitmapBits(True)
            img = np.frombuffer(signedIntsArray, dtype='uint8').reshape((height, width, 4))
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception:
            self._cleanup()
            return None

    def close(self):
        self._cleanup()