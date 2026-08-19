from unittest.mock import patch, MagicMock
from tjm_labs_grounding_agent.popup import check_and_dismiss_popup
from tjm_labs_grounding_agent.grounding import GroundResult

def test_dismisses_popup_when_confidently_found():
    fake_result = GroundResult(x=500, y=300, confidence=0.9, method="coarse", found=True)
    with patch("tjm_labs_grounding_agent.popup.capture_screen"), \
         patch("tjm_labs_grounding_agent.popup.ground_element", return_value=fake_result), \
         patch("tjm_labs_grounding_agent.popup.click") as mock_click:
        result = check_and_dismiss_popup(context="test context")
        assert result is True
        mock_click.assert_called_once_with(500, 300)

def test_falls_back_to_escape_when_not_found():
    fake_result = GroundResult(x=0, y=0, confidence=0.0, method="coarse", found=False)
    with patch("tjm_labs_grounding_agent.popup.capture_screen"), \
         patch("tjm_labs_grounding_agent.popup.ground_element", return_value=fake_result), \
         patch("tjm_labs_grounding_agent.popup.press_key") as mock_press:
        result = check_and_dismiss_popup(context="test context")
        assert result is False
        mock_press.assert_called_once_with("escape")

def test_low_confidence_is_treated_as_not_found():
    fake_result = GroundResult(x=100, y=100, confidence=0.2, method="coarse", found=True)
    with patch("tjm_labs_grounding_agent.popup.capture_screen"), \
         patch("tjm_labs_grounding_agent.popup.ground_element", return_value=fake_result), \
         patch("tjm_labs_grounding_agent.popup.click") as mock_click, \
         patch("tjm_labs_grounding_agent.popup.press_key") as mock_press:
        result = check_and_dismiss_popup(context="test context", confidence_threshold=0.5)
        assert result is False
        mock_click.assert_not_called()
        mock_press.assert_called_once()