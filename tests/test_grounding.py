'''uv run pytest tests/test_grounding.py -v'''

from PIL import Image

from tjm_labs_grounding_agent.grounding import (
    GroundResult,
    _extract_json,
    _is_confident,
    _crop_around,
)


# --- _extract_json ---

def test_extract_json_parses_clean_json():
    text = '{"found": true, "x": 100, "y": 200, "confidence": 0.9}'
    assert _extract_json(text) == {"found": True, "x": 100, "y": 200, "confidence": 0.9}


def test_extract_json_recovers_json_wrapped_in_prose():
    text = (
        'Looking at the image, I can see the icon.\n'
        '{"found": true, "x": 812, "y": 479, "confidence": 0.97}'
    )
    result = _extract_json(text)
    assert result == {"found": True, "x": 812, "y": 479, "confidence": 0.97}


def test_extract_json_returns_none_for_unparseable_text():
    assert _extract_json("no json here at all") is None


# --- _is_confident ---

def test_is_confident_true_above_threshold():
    result = GroundResult(x=1, y=1, confidence=0.9, method="coarse", found=True)
    assert _is_confident(result) is True


def test_is_confident_false_below_threshold():
    result = GroundResult(x=1, y=1, confidence=0.2, method="coarse", found=True)
    assert _is_confident(result) is False


def test_is_confident_false_when_not_found_even_with_high_confidence():
    result = GroundResult(x=1, y=1, confidence=0.9, method="coarse", found=False)
    assert _is_confident(result) is False


# --- _crop_around ---

def test_crop_around_centers_on_point_within_bounds():
    image = Image.new("RGB", (1920, 1080))
    point = GroundResult(x=960, y=540, confidence=1.0, method="coarse")
    crop, (offset_x, offset_y) = _crop_around(image, point, size=1024)
    assert crop.size == (1024, 1024)
    # crop should be centered on the point, not clamped, since it's mid-screen
    assert offset_x == 960 - 512
    assert offset_y == 540 - 512


def test_crop_around_clamps_at_top_left_edge():
    image = Image.new("RGB", (1920, 1080))
    point = GroundResult(x=10, y=10, confidence=1.0, method="coarse")
    crop, (offset_x, offset_y) = _crop_around(image, point, size=1024)
    assert crop.size == (1024, 1024)
    assert offset_x == 0
    assert offset_y == 0


def test_crop_around_clamps_at_bottom_right_edge():
    image = Image.new("RGB", (1920, 1080))
    point = GroundResult(x=1910, y=1070, confidence=1.0, method="coarse")
    crop, (offset_x, offset_y) = _crop_around(image, point, size=1024)
    assert crop.size == (1024, 1024)
    assert offset_x == 1920 - 1024
    assert offset_y == 1080 - 1024