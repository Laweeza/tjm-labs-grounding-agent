
import mss
from PIL import Image


def capture_screen() -> Image.Image:
    """Capture the primary monitor and return as a PIL Image."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # index 0 is 'all monitors combined'; 1 is primary
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        return img