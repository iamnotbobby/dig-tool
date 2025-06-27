import cv2
import numpy as np
import win32gui, win32ui, win32con
import os
import sys


def get_ahk_path():
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
        ahk_exe_path = os.path.join(bundle_dir, 'AutoHotkey.exe')
        if os.path.exists(ahk_exe_path):
            return ahk_exe_path
    else:
        ahk_exe_path = os.path.join('assets', 'AutoHotkey.exe')
        if os.path.exists(ahk_exe_path):
            return ahk_exe_path
    return None


try:
    from ahk import AHK

    ahk_path = get_ahk_path()
    if ahk_path:
        ahk = AHK(executable_path=ahk_path)
    else:
        ahk = AHK()
except Exception as e:
    print(f"AHK initialization error: {e}")
    ahk = None


def send_click():
    if ahk:
        try:
            ahk.send_input('{Click}')
            return
        except Exception as e:
            print(f"AHK click failed: {e}")

    import win32api
    import win32con
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


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
            if self.srcdc: self.srcdc.DeleteDC()
            if self.memdc: self.memdc.DeleteDC()
            if self.hwindc: win32gui.ReleaseDC(self.hwnd, self.hwindc)
            if self.bmp: win32gui.DeleteObject(self.bmp.GetHandle())
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