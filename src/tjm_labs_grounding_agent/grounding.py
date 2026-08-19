"""
Grounding module implementing a VLM-base grounder with a
ReGround refinement pass, per Li et al., "ScreenSpot-Pro: GUI Grounding
for Professional High-Resolution Computer Use".

ReGround: crop a fixed-size window around the initial coarse prediction,
then re-query the grounding model on that tighter crop for a refined,
higher-precision coordinate. The paper found this simple technique
(no iteration, no planner) already yields large accuracy gains over a
single direct-grounding pass.
"""

import base64
import io
import json
import logging
import re
from dataclasses import dataclass

import anthropic
from PIL import Image

RECROP_SIZE = 1024  # px, paper found 1024x1024 near-optimal for larger grounding models
CONFIDENCE_THRESHOLD = 0.5
MAX_DIM = 1568

client = anthropic.Anthropic()
log = logging.getLogger(__name__)

@dataclass
class GroundResult:
    x: int
    y: int
    confidence: float
    method: str  # "coarse" or "reground"
    found: bool = True


def _is_confident(result:GroundResult) -> bool:
    """Return whether a grounding result is usable"""

    return (
        result.found
        and result.confidence >= CONFIDENCE_THRESHOLD
    )


def ground_element(screenshot: Image.Image, instruction: str) -> GroundResult:
    """Locate a screen element using a coarse pass and one ReGround pass"""

    coarse = _vlm_ground(screenshot, instruction)
    coarse.method = "coarse"

    log.info(
        "Coarse grounding: found=%s confidence=%.2f coordinates=(%d, %d)",
        coarse.found,
        coarse.confidence,
        coarse.x,
        coarse.y
    )
    if not _is_confident(coarse):
        return coarse

   # Crop around the coarse location and locate it again
    crop, offset = _crop_around(screenshot, coarse, size=RECROP_SIZE)

    refined = _vlm_ground(crop, instruction)

    log.info(
        "ReGround: found =%s confidence=%.2f crop_coordinates=(%d,%d)",
        refined.found,
        refined.confidence,
        refined.x,
        refined.y
    )

    if not _is_confident(refined):
        log.info("ReGround unsuccessful; using coarse result")
        return coarse

    # The crop's position is added to convert them back to screen coordinates
    x, y = refined.x + offset[0], refined.y + offset[1]
    return GroundResult(x=x, y=y, confidence=refined.confidence, method="reground")

def _prep_img_for_api(image: Image.Image):
    """Resize if needed to stay within model processing limits and return
    the scale factor needed to map returned coordiantes back to original image pixel space"""
    w, h = image.size
    longest = max(w, h)
    if longest <= MAX_DIM:
        return image, 1.0
    scale = MAX_DIM / longest
    resized = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return resized, scale


def _extract_json(text: str) -> dict | None:
    """Parse text as JSON, falling back to extracting the first {...} block
    if the model added reasoning or other prose before/after the JSON
    despite being instructed to respond with only JSON."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _vlm_ground(image: Image.Image, instruction: str) -> GroundResult:
    """Single VLM call: send image + instruction, parse returned coordinates."""
    api_image, scale = _prep_img_for_api(image)
    buf = io.BytesIO()
    api_image.save(buf, format="PNG")
    image_b64 = base64.b64encode(buf.getvalue()).decode()

    response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            temperature=0,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                    {"type": "text", "text": (
                        f"This image is exactly {api_image.size[0]}x{api_image.size[1]} pixels, "
                        f"with (0,0) at the top-left corner.\n\n"
                        f"{instruction}\n\n"
                        "Respond with ONLY a JSON object, no other text, no markdown fences:\n"
                        '{"found": true, "x": <center x pixel>, "y": <center y pixel>, "confidence": <0.0-1.0>}\n'
                        'If not found: {"found": false, "x": 0, "y": 0, "confidence": 0.0}'
                    )}
                ]
            }]
        )

    text = response.content[0].text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    data = _extract_json(text)
    if data is None:
        log.error(f"Could not parse model response as JSON: {text!r}")
        return GroundResult(x=0, y=0, confidence=0.0, method="coarse", found=False)

    return GroundResult(
        x=int(data.get("x", 0) / scale),
        y=int(data.get("y", 0) / scale),
        confidence=float(data.get("confidence", 0.0)),
        method="coarse",
        found=bool(data.get("found", False)),
    )


def _crop_around(image: Image.Image, point: GroundResult, size: int):
    """Crop a size x size window centered on point, return (crop, (offset_x, offset_y))."""
    half = size // 2
    w, h = image.size

    left = max(0, min(point.x - half, w- size))
    top = max(0, min(point.y - half, h - size))
    right = min(left + size, w)
    bottom = min(top + size, h)

    crop = image.crop((left, top, right, bottom))
    return crop, (left, top)