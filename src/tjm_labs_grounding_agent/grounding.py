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


def ground_element(screenshot: Image.Image, instruction: str) -> GroundResult:
    """
    Stage 1: coarse grounding on the full screenshot.
    Stage 2 (ReGround): crop around the coarse prediction, re-query on
    the crop, map the refined point back to full-screen coordinates.
    Fallback: if pass is low confidence or found nothing, retry against full image
    """
    coarse = _vlm_ground(screenshot, instruction)
    if not coarse.found:
        log.warning("Pass found nothing")
        return coarse

    crop, offset = _crop_around(screenshot, coarse, size=RECROP_SIZE)
    refined = _vlm_ground(crop, instruction)

    if not refined.found or refined.confidence < CONFIDENCE_THRESHOLD:
        log.warning("ReGround low-confidence/miss, faillling back to full image grounding")
        fallback = _vlm_ground(screenshot, instruction)
        fallback.method = "fallback"
        return fallback
    
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

def _vlm_ground(image: Image.Image, instruction: str) -> GroundResult:
    """Single VLM call: send image + instruction, parse returned coordinates."""
    api_image, scale = _prep_img_for_api(image)
    buf = io.BytesIO()
    api_image.save(buf, format="PNG")
    image_b64 = base64.b64encode(buf.getvalue()).decode()

    response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
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

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
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
  
