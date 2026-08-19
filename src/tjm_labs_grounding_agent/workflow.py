""" This fill will handle the full automation loop: capture,
grounding, actions, api fethc, and popup handling.

system flow: screenshot -> ground -> launch -> post -> save -> close, reground before every launch.
"""

import logging
from pathlib import Path

from .capture import capture_screen
from .grounding import ground_element
from .actions import double_click, type_text, save_as, force_close_all_notepad
from .api_client import fetch_posts, format_post
from .handle_popup import check_and_dismiss_popup

OUTPUT_DIR = str(Path.home() / "Desktop" / "tjm-project")
MAX_RETRIES = 2

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def ground_and_launch_notepad() -> bool:
    for attempt in range(MAX_RETRIES):
        screenshot = capture_screen()
        result = ground_element(screenshot, "Locate Notepad desktop icon")
        if result is None or not result.found or result.confidence < 0.5:
            log.warning(f"Grounding attempt {attempt + 1} failed, retrying")
            continue
        double_click(result.x, result.y)
        #if check_and_dismiss_popup():
            #log.info("Dismissed an unexpected popup")
        return True
    return False

def run():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    posts = fetch_posts(limit=10)
    skipped = []

    for post in posts:
        if not ground_and_launch_notepad():
            log.error(f"Skipping post {post['id']}: could not ground or launch Notepad")
            skipped.append(post["id"])
            continue
        type_text(format_post(post))
        save_as(f"post_{post['id']}.txt", OUTPUT_DIR)
        force_close_all_notepad()
        
    log.info(f"Run complete. Skipped posts: {skipped or 'none'}")

if __name__ == "__main__":
    run()
