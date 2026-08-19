"""Standalone demo: shows that ground_element (+ optional click) works for
arbitrary icons, not just Notepad, with no code changes to the detector itself.

Usage:
    uv run python demo_grounding.py "the Recycle Bin desktop icon" --click
    uv run python demo_grounding.py "the Microsoft Edge desktop icon" --click
"""

import argparse
import logging

from tjm_labs_grounding_agent.capture import capture_screen
from tjm_labs_grounding_agent.grounding import ground_element
from tjm_labs_grounding_agent.actions import double_click

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.5


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("instruction", help='e.g. "the Recycle Bin desktop icon"')
    parser.add_argument(
        "--click",
        action="store_true",
        help="Double-click the located coordinates instead of just reporting them",
    )
    args = parser.parse_args()

    screenshot = capture_screen()
    result = ground_element(screenshot, args.instruction)

    print(f"Instruction: {args.instruction}")
    print(f"Found: {result.found}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Coordinates: ({result.x}, {result.y})")
    print(f"Method: {result.method}")

    if not args.click:
        return

    if not result.found:
        print("Not clicking: target was not found.")
        return

    if result.confidence < MIN_CONFIDENCE:
        print(f"Not clicking: confidence {result.confidence:.2f} is below threshold {MIN_CONFIDENCE}.")
        return

    print(f"Double-clicking ({result.x}, {result.y})...")
    double_click(result.x, result.y)
    print("Done.")


if __name__ == "__main__":
    main()
