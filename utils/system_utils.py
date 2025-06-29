import importlib

import cv2
import numpy as np
import win32gui, win32ui, win32con
import sys
import ctypes
import tkinter as tk
from tkinter import messagebox
from ahk import AHK

ahk = AHK()

def check_dependencies():
    required_packages = {
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'PIL': 'Pillow',
        'keyboard': 'keyboard',
        'win32gui': 'pywin32',
        'pynput': 'pynput',
        'requests': 'requests',
        'autoit': 'pyautoit',
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


def check_display_scale():
    try:
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()

        hdc = user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
        user32.ReleaseDC(0, hdc)

        scale_percent = (dpi * 100) // 96

        if scale_percent != 100:
            root = tk.Tk()
            root.withdraw()

            messagebox.showerror(
                "Display Scale Error",
                f"ERROR: Display scale is set to {scale_percent}%. This tool requires 100% display scaling to work correctly."
            )

            root.destroy()
            sys.exit(1)

    except Exception:
        pass


def send_click():
    ahk.send_input('{Click}')


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