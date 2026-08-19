""" This file will handle the full automation loop: capture,
grounding, actions, api fetch, and popup handling.

system flow: screenshot -> ground -> launch -> post -> save -> close, reground before every launch.
"""

import logging
import time
from pathlib import Path

from .actions import (
    double_click,
    type_text,
    save_as,
    close_window,
    activate_window,
    wait_for_active_window,
    get_windows_by_title,
)
from .api_client import fetch_posts, format_post
from .popup import check_and_dismiss_popup, ground_with_popup_recovery, make_context

POST_LIMIT = 10
MAX_GROUNDING_ATTEMPTS = 2
MIN_GROUNDING_CONFIDENCE = 0.5
DELAY_SECONDS = 1.0
WINDOW_APPEAR_TIMEOUT = 3.0

APP_NAME = "Notepad"
OUTPUT_DIR = Path.home() / "Desktop" / "tjm-project"
NOTEPAD_INSTRUCTION = (
    'Locate the Windows desktop shortcut icon labeled "Notepad". '
    "Do not select a taskbar icon or an open Notepad window."
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def _close_any_stray_notepad():
    """Best-effort cleanup: if a Notepad window opened but never became the
    confirmed active window (e.g. focus was stolen by another interruption),
    close it before retrying so orphaned windows don't accumulate and
    confuse future focus checks. Checks by title regardless of focus state,
    since a stray window is by definition likely not the active one."""
    for stray in get_windows_by_title(APP_NAME):
        log.info("Closing stray Notepad window before retrying: %r", stray.title)
        close_window(stray)


def ground_and_launch_notepad():
    """Ground the Notepad shortcut, launch it, and return the resulting
    window object. Returns None if it could not be located and launched."""
    for attempt in range(1, MAX_GROUNDING_ATTEMPTS + 1):
        log.info(
            "Locating Notepad shortcut: attempt %d of %d",
            attempt,
            MAX_GROUNDING_ATTEMPTS
        )

        result = ground_with_popup_recovery(
            instruction=NOTEPAD_INSTRUCTION,
            context=make_context(APP_NAME, "pre_launch"),
        )

        if result is None:
            log.warning("Grounding returned no result")
            continue

        log.info(
            "Grounding result: found=%s confidence=%.2f "
            "coordinates=(%d, %d) method=%s",
            result.found,
            result.confidence,
            result.x,
            result.y,
            result.method
        )

        if not result.found:
            log.warning("Notepad shortcut not found")
            continue

        if result.confidence < MIN_GROUNDING_CONFIDENCE:
            log.warning(
                "Grounding confidence %.2f is below the %.2f threshold",
                result.confidence,
                MIN_GROUNDING_CONFIDENCE,
            )
            continue

        double_click(result.x, result.y)

        notepad_window = wait_for_active_window(APP_NAME, timeout=WINDOW_APPEAR_TIMEOUT)
        if notepad_window is None:
            log.warning(
                "Grounded coordinates (%d, %d) did not open Notepad",
                result.x,
                result.y,
            )
            _close_any_stray_notepad()
            continue

        if check_and_dismiss_popup(context=make_context(APP_NAME, "post_launch")):
            log.info("Dismissed an unexpected popup")
            # Popup dismissal may have changed focus. The Notepad window
            # itself should still exist (we're not closing it, just
            # unfocused), so try re-activating it directly rather than
            # closing and relaunching from scratch.
            if not activate_window(notepad_window):
                log.warning("Could not re-activate Notepad after popup dismissal")
                _close_any_stray_notepad()
                continue

        return notepad_window

    log.error(
        "Could not locate and launch Notepad after %d attempts",
        MAX_GROUNDING_ATTEMPTS,
    )
    return None


def process_post(post: dict) -> bool:
    """Open Notepad and enter one post, save it, and then close Notepad."""

    post_id = post["id"]
    filename = f"post_{post_id}.txt"
    start_time = time.monotonic()

    log.info("Processing post %s", post_id)

    notepad_window = ground_and_launch_notepad()
    if notepad_window is None:
        log.error("Post %s failed: Notepad did not launch", post_id)
        return False

    post_text = format_post(post)

    if not type_text(notepad_window, post_text):
        log.error("Post %s failed: could not type into Notepad", post_id)
        close_window(notepad_window)
        return False

    saved = save_as(notepad_window, filename, OUTPUT_DIR)
    if not saved:
        log.error("Post %s failed: file was not saved", post_id)
        close_window(notepad_window)
        return False

    close_window(notepad_window)
    time.sleep(DELAY_SECONDS)

    elapsed = time.monotonic() - start_time
    log.info("Post %s saved as %s (%.2fs)", post_id, filename, elapsed)
    return True


def run(post_limit: int = POST_LIMIT) -> bool:
    """Process the first `post_limit` posts."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_start = time.monotonic()

    try:
        posts = fetch_posts(limit=post_limit)
    except Exception:
        log.exception("Could not fetch posts")
        return False

    failed_post_ids = []
    post_durations = []

    for post in posts:
        post_start = time.monotonic()
        try:
            succeeded = process_post(post)
        except Exception:
            log.exception("Unexpected error while processing post %s", post.get("id", "unknown"))
            succeeded = False
        post_durations.append(time.monotonic() - post_start)

        if not succeeded:
            failed_post_ids.append(post.get("id", "unknown"))

    total_elapsed = time.monotonic() - run_start
    avg_per_post = sum(post_durations) / len(post_durations) if post_durations else 0.0

    log.info(
        "Run finished in %.2fs (%d posts, avg %.2fs/post)",
        total_elapsed,
        len(posts),
        avg_per_post,
    )

    if failed_post_ids:
        log.error("Run incomplete. Failed post IDs: %s", failed_post_ids)
        return False

    log.info("Run complete. All %d posts processed successfully.", len(posts))
    return True


if __name__ == "__main__":
    run()