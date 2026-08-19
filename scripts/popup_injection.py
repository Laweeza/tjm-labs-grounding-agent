"""Chaos test: runs the real workflow while injecting multiple genuine,
unexpected popups at random points throughout the ENTIRE run, to verify
popup detection and recovery hold up across repeated interruptions.

Do not move your own mouse or type during the run - that's direct input
contention with pyautogui, a different failure mode than an unexpected
popup, and will interfere with results regardless of recovery logic.

Usage:
    uv run python test_popup_random_injections.py
    uv run python test_popup_random_injections.py --limit 5 --min-interval 5 --max-interval 15
"""

import argparse
import logging
import random
import threading
import time

from tjm_labs_grounding_agent.workflow import run

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


import ctypes


def trigger_fake_error_dialog():
    """Shows a real, modal Windows message box, simulating an unexpected
    error/permission dialog without spawning a persistent competing
    application window (unlike launching a full separate app, which can
    itself steal focus repeatedly and accumulate windows across injections).
    """
    log.info(">>> INJECTING POPUP NOW <<<")
    threading.Thread(
        target=lambda: ctypes.windll.user32.MessageBoxW(
            0, "Simulated unexpected interruption", "Alert", 0
        ),
        daemon=True,
    ).start()


def injection_loop(stop_event: threading.Event, min_interval: float, max_interval: float, max_injections: int):
    """Repeatedly injects a popup at random intervals until stop_event is
    set or max_injections is reached, whichever comes first."""
    count = 0
    while not stop_event.is_set() and count < max_injections:
        delay = random.uniform(min_interval, max_interval)
        log.info("Next popup injection in %.1fs", delay)

        # Wait in short slices so we notice stop_event promptly rather than
        # sleeping past the end of the run.
        waited = 0.0
        while waited < delay and not stop_event.is_set():
            time.sleep(0.5)
            waited += 0.5

        if stop_event.is_set():
            break

        trigger_fake_error_dialog()
        count += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5, help="Number of posts to process")
    parser.add_argument("--min-interval", type=float, default=20.0, help="Minimum seconds between injections")
    parser.add_argument("--max-interval", type=float, default=40.0, help="Maximum seconds between injections")
    parser.add_argument("--max-injections", type=int, default=4, help="Total number of popups to inject during the run")
    args = parser.parse_args()

    stop_event = threading.Event()
    injector = threading.Thread(
        target=injection_loop,
        args=(stop_event, args.min_interval, args.max_interval, args.max_injections),
        daemon=True,
    )
    injector.start()

    log.info(
        "Starting workflow run (limit=%d) with recurring popup injections every %.0f-%.0fs...",
        args.limit,
        args.min_interval,
        args.max_interval,
    )
    log.info("Do not move your mouse or type manually during this run.")

    try:
        success = run()
    finally:
        stop_event.set()

    if success:
        print("\nPASS: workflow completed successfully despite repeated injected popups.")
    else:
        print("\nSome posts failed. Review the logs above to see which injections were")
        print("recovered from and which were not.")


if __name__ == "__main__":
    main()