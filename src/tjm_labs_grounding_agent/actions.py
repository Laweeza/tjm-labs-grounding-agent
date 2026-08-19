"""Mouse/keyboard actions and window interaction."""

import logging
import time
import pyautogui
import win32gui
import win32con
import subprocess

log = logging.getLogger(__name__)
pyautogui.FAILSAFE = True


def double_click(x: int, y: int, settle_sec: float = 1.5):
    pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.doubleClick()
    time.sleep(settle_sec)
    _focus_notepad()


def _focus_notepad(timeout: float = 3.0) -> bool:
    """Find the Notepad window and force it to the foreground."""
    elapsed = 0.0
    while elapsed < timeout:
        windows = []
        win32gui.EnumWindows(
            lambda hwnd, res: res.append(hwnd)
            if win32gui.IsWindowVisible(hwnd) and "Notepad" in win32gui.GetWindowText(hwnd)
            else None,
            windows
        )
        if windows:
            try:
                win32gui.SetForegroundWindow(windows[0])
            except Exception as e:
                log.warning(f"SetForegroundWindow failed: {e}")
            time.sleep(0.3)
            return True
        time.sleep(0.2)
        elapsed += 0.2
    log.warning("Notepad window never appeared to focus")
    return False


def click(x: int, y: int):
    pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.click()


def type_text(text: str):
    pyautogui.write(text, interval=0.01)


def _list_all_window_titles():
    titles = []
    win32gui.EnumWindows(
        lambda hwnd, res: res.append(win32gui.GetWindowText(hwnd))
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd)
        else None,
        titles
    )
    return titles


def _wait_for_window(title_substring: str, timeout: float = 3.0) -> bool:
    elapsed = 0.0
    while elapsed < timeout:
        found = []
        win32gui.EnumWindows(
            lambda hwnd, res: res.append(hwnd)
            if title_substring.lower() in win32gui.GetWindowText(hwnd).lower()
            else None,
            found
        )
        if found:
            return True
        time.sleep(0.2)
        elapsed += 0.2

    # debug aid: show what windows DID exist, so we can see the real title
    log.error(f"'{title_substring}' not found. Open windows were: {_list_all_window_titles()}")
    return False


def save_as(filename: str, directory: str) -> bool:
    pyautogui.hotkey("ctrl", "s")
    if not _wait_for_window("Save As", timeout=3.0):
        log.error("Save As dialog never appeared")
        return False
    time.sleep(0.3)
    full_path = rf"{directory}\{filename}"
    pyautogui.write(full_path, interval=0.01)
    pyautogui.press("enter")
    time.sleep(1)
    return True


def force_close_all_notepad():
    subprocess.run(["taskkill", "/IM", "notepad.exe", "/F"], capture_output=True)
    time.sleep(1)