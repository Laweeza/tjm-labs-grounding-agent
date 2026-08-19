import logging

from .capture import capture_screen
from .grounding import ground_element
from .actions import click, press_key

log = logging.getLogger(__name__)

MIN_POPUP_CONFIDENCE = 0.5

POPUP_INSTRUCTION = """
{context}

Only report a popup when an additional dialog, notification, or overlay
appears separately from what is expected. Examples include:

- An error message
- A save prompt
- A permission request
- A Windows system dialog or notification toast

If an additional element exists, return the coordinates of its safest
dismiss, close, cancel, or OK control.

If nothing unexpected is visible, return found=false.
""".strip()


def make_context(app_name: str, phase: str) -> str:
    """phase: 'pre_launch' or 'post_launch'"""
    if phase == "pre_launch":
        return f"The desktop is expected to be visible with a {app_name} shortcut icon on it."
    return (
        f"A {app_name} application window was intentionally opened. "
        f"The main {app_name} window is expected and must not be treated as a popup."
    )


def check_and_dismiss_popup(context: str, confidence_threshold: float = MIN_POPUP_CONFIDENCE) -> bool:
    """Returns True if a popup was confidently detected and clicked to dismiss.

    Returns False if no popup was found, or if one was suspected but couldn't
    be confidently located — in which case an Escape keypress is tried as a
    generic, appearance-agnostic fallback.
    """
    screenshot = capture_screen()

    result = ground_element(
        screenshot,
        instruction=POPUP_INSTRUCTION.format(context=context),
    )

    if result.found and result.confidence >= confidence_threshold:
        click(result.x, result.y)
        log.info("Dismissed unexpected popup at (%d, %d)", result.x, result.y)
        return True

    if result.found:
        log.warning(
            "Possible popup ignored because confidence %.2f is below %.2f",
            result.confidence,
            confidence_threshold,
        )
    else:
        log.debug("No unexpected popup detected")

    log.debug("Trying Escape as a generic fallback in case something was missed")
    press_key("escape")
    return False


def ground_with_popup_recovery(instruction: str, context: str, max_attempts: int = 2):
    """Ground an element, and if it's not found, attempt to dismiss whatever
    might be blocking it (popup, dialog, toast) and retry.

    Returns the final GroundResult (found=False if all attempts are exhausted).
    """
    screenshot = capture_screen()
    result = ground_element(screenshot, instruction=instruction)

    attempts = 0
    while not result.found and attempts < max_attempts:
        dismissed = check_and_dismiss_popup(context=context)
        if not dismissed:
            # Escape was tried inside check_and_dismiss_popup as a last resort;
            # re-screenshot once more in case it helped, then stop either way.
            screenshot = capture_screen()
            result = ground_element(screenshot, instruction=instruction)
            break

        screenshot = capture_screen()
        result = ground_element(screenshot, instruction=instruction)
        attempts += 1

    return result