import cv2
import numpy as np
import mss


class ScreenCapture:
    def __init__(self):
        self.sct = mss.mss()

    def capture(self, bbox=None):
        if not bbox: return None
        # mss expects a dictionary with keys 'left', 'top', 'width', 'height'
        monitor = {
            "left": bbox[0],
            "top": bbox[1],
            "width": bbox[2] - bbox[0],
            "height": bbox[3] - bbox[1],
        }
        sct_img = self.sct.grab(monitor)
        # Convert to a numpy array and then to OpenCV format
        img = np.array(sct_img)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def close(self):
        # mss does not require explicit closing of resources
        pass
