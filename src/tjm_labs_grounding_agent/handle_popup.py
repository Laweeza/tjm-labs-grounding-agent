"""Generic popup/dialog detection and dismissal - uses same
grounding mechanism as icon detection. Reasons about function (control that closes dialog)
not by appearance so generalizes never-seen before popups
"""

from .capture import capture_screen
from .grounding import ground_element
from .actions import click

def check_and_dismiss_popup(confidence_threshold: float = 0.5) -> bool:
    """Returns True if popup detected and dismissed"""
    screenshot = capture_screen()
    result = ground_element(screenshot, instruction="Is there dialog or popup on screen? If there ism return coordinate of the control that would dismiss it (X button, Cancel, ok, or similiar)"
    )
    if result and result.found and result.confidence > confidence_threshold:
        click(result.x, result.y)
        return True
    return False