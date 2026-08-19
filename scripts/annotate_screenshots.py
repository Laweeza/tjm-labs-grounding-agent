"""Generates an annotated screenshot showing the grounded Notepad icon
location, for the deliverable screenshots. Run once per icon position."""

from PIL import Image, ImageDraw, ImageFont
from tjm_labs_grounding_agent.capture import capture_screen
from tjm_labs_grounding_agent.grounding import ground_element

LABEL = "bottom_right"  # change to "bottom_right" | "center" | "top_left"

screenshot = capture_screen()
result = ground_element(screenshot, "Locate Notepad desktop icon")

annotated = screenshot.copy()
draw = ImageDraw.Draw(annotated)
img_w, img_h = annotated.size

r = 45
draw.ellipse(
    [result.x - r, result.y - r, result.x + r, result.y + r],
    outline="red", width=6
)
draw.line([result.x - 60, result.y, result.x + 60, result.y], fill="red", width=4)
draw.line([result.x, result.y - 60, result.x, result.y + 60], fill="red", width=4)

label = f"({result.x}, {result.y})  conf={result.confidence:.2f}"
try:
    font = ImageFont.truetype("arial.ttf", 28)
except OSError:
    font = ImageFont.load_default()

# Measure text size first
temp_bbox = draw.textbbox((0, 0), label, font=font)
text_w = temp_bbox[2] - temp_bbox[0]
text_h = temp_bbox[3] - temp_bbox[1]

# Prefer placing label below-right of marker, then clamp to stay fully on screen
text_x = result.x + 60
text_y = result.y + 60
text_x = max(10, min(text_x, img_w - text_w - 20))
text_y = max(10, min(text_y, img_h - text_h - 20))

bbox = draw.textbbox((text_x, text_y), label, font=font)
draw.rectangle([bbox[0] - 8, bbox[1] - 6, bbox[2] + 8, bbox[3] + 6], fill="black")
draw.text((text_x, text_y), label, fill="yellow", font=font)

annotated.save(f"screenshots/detected_{LABEL}.png")

crop_size = 300
crop_box = (
    max(0, result.x - crop_size), max(0, result.y - crop_size),
    min(img_w, result.x + crop_size), min(img_h, result.y + crop_size)
)
annotated.crop(crop_box).save(f"screenshots/detected_{LABEL}_closeup.png")

print(f"Saved: detected_{LABEL}.png — coords=({result.x},{result.y}) conf={result.confidence:.2f}")