import logging
import subprocess
import time
from pathlib import Path
from typing import Any

import pyautogui


log = logging.getLogger(__name__)
pyautogui.FAILSAFE = True

POLL_INTERVAL_SECONDS = 0.2


def double_click(x: int, y: int, settle_sec: float = 1.5) -> None:
    """Double-click the supplied screen coordinates."""
    pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.doubleClick()
    time.sleep(settle_sec)


def click(x: int, y: int) -> None:
    """Click the supplied screen coordinates."""
    pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.click()


def press_key(key: str) -> None:
    """Press a single key, such as 'escape' or 'enter'."""
    pyautogui.press(key)


def _list_all_window_titles() -> list[str]:
    """Return the titles of all visible windows."""
    return [
        window.title
        for window in pyautogui.getAllWindows()
        if window.visible and window.title
    ]


def get_windows_by_title(title_substring: str) -> list:
    """Return all visible windows whose title contains the given text,
    regardless of whether they're currently focused/active."""
    expected = title_substring.casefold()
    return [
        window
        for window in pyautogui.getAllWindows()
        if window.visible and expected in window.title.casefold()
    ]


def wait_for_active_window(
    title_substring: str,
    timeout: float = 3.0,
) -> Any | None:
    """Wait until the active window title contains the expected text."""
    deadline = time.monotonic() + timeout
    expected = title_substring.casefold()

    while time.monotonic() < deadline:
        window = pyautogui.getActiveWindow()

        if window and expected in window.title.casefold():
            return window

        time.sleep(POLL_INTERVAL_SECONDS)

    log.error(
        "%r did not become active. Open windows were: %s",
        title_substring,
        _list_all_window_titles(),
    )
    return None


def activate_window(window, timeout: float = 3.0) -> bool:
    """Activate a window and verify that it became active."""
    try:
        if window.isMinimized:
            window.restore()

        window.activate()
    except Exception:
        log.exception("Could not activate window %r", window.title)
        return False

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        active_window = pyautogui.getActiveWindow()

        if active_window and active_window.title == window.title:
            return True

        time.sleep(POLL_INTERVAL_SECONDS)

    log.error("Window did not become active: %r", window.title)
    return False


def type_text(window, text: str) -> bool:
    """Activate the intended window and type text into it."""
    if not activate_window(window):
        return False

    try:
        pyautogui.write(text, interval=0.01)
    except Exception:
        log.exception("Could not type into window %r", window.title)
        return False

    return True


def save_as(
    window,
    filename: str,
    directory: Path,
    timeout: float = 5.0,
) -> bool:
    """Save the active document and verify that the output file exists."""
    if not activate_window(window):
        return False

    full_path = directory / filename

    try:
        pyautogui.hotkey("ctrl", "s")
    except Exception:
        log.exception("Could not open the Save As dialog")
        return False

    save_dialog = wait_for_active_window("Save As", timeout=timeout)
    if save_dialog is None:
        log.error("Save As dialog never appeared")
        return False

    try:
        pyautogui.write(str(full_path), interval=0.01)
        pyautogui.press("enter")
    except Exception:
        log.exception("Could not enter the save path")
        return False

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if full_path.is_file():
            return True

        time.sleep(POLL_INTERVAL_SECONDS)

    log.error("Saved file was not created: %s", full_path)
    return False


def close_window(window, timeout: float = 3.0) -> bool:
    """Close a window normally and verify that it disappeared.

    Falls back to force-killing Notepad if the graceful close doesn't
    take effect within the timeout, or if closing raises an exception.
    """
    title = window.title

    try:
        if window.isMinimized:
            window.restore()

        window.activate()
        window.close()
    except Exception:
        log.exception("Could not close window %r; force-closing", title)
        return _force_close_notepad()

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if not window.visible:
            return True

        time.sleep(POLL_INTERVAL_SECONDS)

    log.warning("Window did not close normally, force-closing: %s", title)
    return _force_close_notepad()


def _force_close_notepad() -> bool:
    """Last-resort fallback: forcibly terminate any Notepad process."""
    subprocess.run(["taskkill", "/IM", "notepad.exe", "/F"], capture_output=True)
    time.sleep(1)
    return True