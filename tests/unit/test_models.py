"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from mcp_ui_explorer.models import (
    RegionType,
    ControlType,
    ScreenshotUIInput,
    ClickUIElementInput,
    KeyboardInputInput,
    PressKeyInput,
    HotKeyInput,
    FindNearCursorInput,
    UITarsInput,
    UIVerificationInput,
    CreateMemorySummaryInput,
    DocumentStepInput,
    GetStepStatusInput,
)


class TestRegionType:
    """Test RegionType enum."""

    def test_valid_regions(self):
        """Test valid region types."""
        valid_regions = [
            "screen", "top", "bottom", "left", "right", "center",
            "top-left", "top-right", "bottom-left", "bottom-right"
        ]
        for region in valid_regions:
            assert region in RegionType.__members__.values()

    def test_region_string_values(self):
        """Test that region enum values are strings."""
        for region in RegionType:
            assert isinstance(region.value, str)


class TestControlType:
    """Test ControlType enum."""

    def test_valid_control_types(self):
        """Test valid control types."""
        valid_types = [
            "Button", "Text", "Edit", "CheckBox", "RadioButton",
            "ComboBox", "List", "ListItem", "Menu", "MenuItem",
            "Tree", "TreeItem", "ToolBar", "Tab", "TabItem",
            "Window", "Dialog", "Pane", "Group", "Document",
            "StatusBar", "Image", "Hyperlink"
        ]
        for control_type in valid_types:
            assert control_type in ControlType.__members__.values()


class TestScreenshotUIInput:
    """Test ScreenshotUIInput model."""

    def test_default_values(self):
        """Test default values are set correctly."""
        input_model = ScreenshotUIInput()
        assert input_model.focus_only is True
        assert input_model.highlight_levels is True
        assert input_model.max_depth == 4
        assert input_model.min_size == 20
        assert input_model.output_prefix == "ui_hierarchy"
        assert input_model.region is None

    def test_valid_region_string(self):
        """Test valid region string."""
        input_model = ScreenshotUIInput(region="screen")
        assert input_model.region == "screen"

    def test_valid_region_enum(self):
        """Test valid region enum."""
        input_model = ScreenshotUIInput(region=RegionType.TOP)
        assert input_model.region == RegionType.TOP

    def test_custom_coordinates(self):
        """Test custom coordinates as region."""
        input_model = ScreenshotUIInput(region="100,200,300,400")
        assert input_model.region == "100,200,300,400"

    def test_negative_values_allowed(self):
        """Test that negative values are allowed (no validation constraints)."""
        input_model = ScreenshotUIInput(max_depth=-1, min_size=-1)
        assert input_model.max_depth == -1
        assert input_model.min_size == -1


class TestClickUIElementInput:
    """Test ClickUIElementInput model."""

    def test_required_coordinates(self):
        """Test that x and y coordinates are required."""
        input_model = ClickUIElementInput(x=100, y=200)
        assert input_model.x == 100
        assert input_model.y == 200

    def test_missing_coordinates(self):
        """Test that missing coordinates raise validation error."""
        with pytest.raises(ValidationError):
            ClickUIElementInput(x=100)  # Missing y
        
        with pytest.raises(ValidationError):
            ClickUIElementInput(y=200)  # Missing x

    def test_default_values(self):
        """Test default values."""
        input_model = ClickUIElementInput(x=100, y=200)
        assert input_model.auto_verify is True
        assert input_model.normalized is False
        assert input_model.verification_query is None
        assert input_model.verification_timeout == 3.0
        assert input_model.wait_time == 2.0

    def test_normalized_coordinates(self):
        """Test normalized coordinates."""
        input_model = ClickUIElementInput(x=0.5, y=0.7, normalized=True)
        assert input_model.x == 0.5
        assert input_model.y == 0.7
        assert input_model.normalized is True

    def test_negative_wait_time_allowed(self):
        """Test that negative wait time is allowed (no validation constraint)."""
        input_model = ClickUIElementInput(x=100, y=200, wait_time=-1)
        assert input_model.wait_time == -1


class TestKeyboardInputInput:
    """Test KeyboardInputInput model."""

    def test_required_text(self):
        """Test that text is required."""
        input_model = KeyboardInputInput(text="Hello World")
        assert input_model.text == "Hello World"

    def test_missing_text(self):
        """Test that missing text raises validation error."""
        with pytest.raises(ValidationError):
            KeyboardInputInput()

    def test_default_values(self):
        """Test default values."""
        input_model = KeyboardInputInput(text="test")
        assert input_model.delay == 0.1
        assert input_model.interval == 0.0
        assert input_model.press_enter is False
        assert input_model.auto_verify is True
        assert input_model.verification_query is None
        assert input_model.verification_timeout == 3.0

    def test_custom_values(self):
        """Test custom values."""
        input_model = KeyboardInputInput(
            text="test",
            delay=0.5,
            interval=0.1,
            press_enter=True,
            auto_verify=False,
            verification_query="text appeared",
            verification_timeout=5.0
        )
        assert input_model.delay == 0.5
        assert input_model.interval == 0.1
        assert input_model.press_enter is True
        assert input_model.auto_verify is False
        assert input_model.verification_query == "text appeared"
        assert input_model.verification_timeout == 5.0

    def test_negative_values_allowed(self):
        """Test that negative values are allowed (no validation constraints)."""
        input_model = KeyboardInputInput(text="test", delay=-1, interval=-1)
        assert input_model.delay == -1
        assert input_model.interval == -1


class TestPressKeyInput:
    """Test PressKeyInput model."""

    def test_required_key(self):
        """Test that key is required."""
        input_model = PressKeyInput(key="enter")
        assert input_model.key == "enter"

    def test_missing_key(self):
        """Test that missing key raises validation error."""
        with pytest.raises(ValidationError):
            PressKeyInput()

    def test_default_values(self):
        """Test default values."""
        input_model = PressKeyInput(key="tab")
        assert input_model.delay == 0.1
        assert input_model.presses == 1
        assert input_model.interval == 0.0
        assert input_model.auto_verify is True
        assert input_model.verification_query is None
        assert input_model.verification_timeout == 3.0

    def test_multiple_presses(self):
        """Test multiple key presses."""
        input_model = PressKeyInput(key="backspace", presses=5)
        assert input_model.presses == 5

    def test_zero_or_negative_presses_allowed(self):
        """Test that zero or negative presses are allowed (no validation constraint)."""
        input_model = PressKeyInput(key="enter", presses=0)
        assert input_model.presses == 0
        
        input_model = PressKeyInput(key="enter", presses=-1)
        assert input_model.presses == -1


class TestHotKeyInput:
    """Test HotKeyInput model."""

    def test_required_keys(self):
        """Test that keys list is required."""
        input_model = HotKeyInput(keys=["ctrl", "c"])
        assert input_model.keys == ["ctrl", "c"]

    def test_missing_keys(self):
        """Test that missing keys raises validation error."""
        with pytest.raises(ValidationError):
            HotKeyInput()

    def test_empty_keys_list_allowed(self):
        """Test that empty keys list is allowed (no validation constraint)."""
        input_model = HotKeyInput(keys=[])
        assert input_model.keys == []

    def test_single_key(self):
        """Test single key in list."""
        input_model = HotKeyInput(keys=["escape"])
        assert input_model.keys == ["escape"]

    def test_complex_hotkey(self):
        """Test complex hotkey combination."""
        input_model = HotKeyInput(keys=["ctrl", "shift", "alt", "f12"])
        assert input_model.keys == ["ctrl", "shift", "alt", "f12"]

    def test_default_values(self):
        """Test default values."""
        input_model = HotKeyInput(keys=["ctrl", "v"])
        assert input_model.delay == 0.1
        assert input_model.auto_verify is True
        assert input_model.verification_query is None
        assert input_model.verification_timeout == 3.0


class TestFindNearCursorInput:
    """Test FindNearCursorInput model."""

    def test_default_values(self):
        """Test default values."""
        input_model = FindNearCursorInput()
        assert input_model.control_type is None
        assert input_model.limit == 5
        assert input_model.max_distance == 100

    def test_control_type_filter(self):
        """Test control type filtering."""
        input_model = FindNearCursorInput(control_type=ControlType.BUTTON)
        assert input_model.control_type == ControlType.BUTTON

    def test_custom_limits(self):
        """Test custom limits."""
        input_model = FindNearCursorInput(limit=10, max_distance=200)
        assert input_model.limit == 10
        assert input_model.max_distance == 200

    def test_zero_or_negative_values_allowed(self):
        """Test that zero or negative values are allowed (no validation constraints)."""
        input_model = FindNearCursorInput(limit=0, max_distance=-1)
        assert input_model.limit == 0
        assert input_model.max_distance == -1


class TestUITarsInput:
    """Test UITarsInput model."""

    def test_required_fields(self):
        """Test required fields."""
        input_model = UITarsInput(
            image_path="/path/to/image.png",
            query="find button"
        )
        assert input_model.image_path == "/path/to/image.png"
        assert input_model.query == "find button"

    def test_missing_required_fields(self):
        """Test missing required fields."""
        with pytest.raises(ValidationError):
            UITarsInput(image_path="/path/to/image.png")  # Missing query
        
        with pytest.raises(ValidationError):
            UITarsInput(query="find button")  # Missing image_path

    def test_default_values(self):
        """Test default values."""
        input_model = UITarsInput(
            image_path="/path/to/image.png",
            query="find button"
        )
        assert input_model.api_url == "http://127.0.0.1:1234/v1"
        assert input_model.model_name == "ui-tars-7b-dpo"

    def test_custom_api_settings(self):
        """Test custom API settings."""
        input_model = UITarsInput(
            image_path="/path/to/image.png",
            query="find button",
            api_url="http://custom-api:8080/v1",
            model_name="custom-model"
        )
        assert input_model.api_url == "http://custom-api:8080/v1"
        assert input_model.model_name == "custom-model"


class TestUIVerificationInput:
    """Test UIVerificationInput model."""

    def test_required_fields(self):
        """Test required fields."""
        input_model = UIVerificationInput(
            action_description="Clicked button",
            expected_result="Window should open",
            verification_query="new window appeared"
        )
        assert input_model.action_description == "Clicked button"
        assert input_model.expected_result == "Window should open"
        assert input_model.verification_query == "new window appeared"

    def test_missing_required_fields(self):
        """Test missing required fields."""
        with pytest.raises(ValidationError):
            UIVerificationInput(
                expected_result="Window should open",
                verification_query="new window appeared"
            )  # Missing action_description

    def test_default_values(self):
        """Test default values."""
        input_model = UIVerificationInput(
            action_description="Clicked button",
            expected_result="Window should open",
            verification_query="new window appeared"
        )
        assert input_model.timeout == 3.0
        assert input_model.comparison_image is None

    def test_custom_values(self):
        """Test custom values."""
        input_model = UIVerificationInput(
            action_description="Clicked button",
            expected_result="Window should open",
            verification_query="new window appeared",
            timeout=10.0,
            comparison_image="/path/to/before.png"
        )
        assert input_model.timeout == 10.0
        assert input_model.comparison_image == "/path/to/before.png"


class TestCreateMemorySummaryInput:
    """Test CreateMemorySummaryInput model."""

    def test_default_values(self):
        """Test default values."""
        input_model = CreateMemorySummaryInput()
        assert input_model.force_summary is False

    def test_force_summary(self):
        """Test force summary option."""
        input_model = CreateMemorySummaryInput(force_summary=True)
        assert input_model.force_summary is True


class TestDocumentStepInput:
    """Test DocumentStepInput model."""

    def test_required_step_description(self):
        """Test required step description."""
        input_model = DocumentStepInput(step_description="Test step")
        assert input_model.step_description == "Test step"

    def test_missing_step_description(self):
        """Test missing step description."""
        with pytest.raises(ValidationError):
            DocumentStepInput()

    def test_default_values(self):
        """Test default values."""
        input_model = DocumentStepInput(step_description="Test step")
        assert input_model.completion_notes == ""
        assert input_model.mark_previous_complete is False

    def test_custom_values(self):
        """Test custom values."""
        input_model = DocumentStepInput(
            step_description="Test step",
            completion_notes="Previous step completed successfully",
            mark_previous_complete=True
        )
        assert input_model.completion_notes == "Previous step completed successfully"
        assert input_model.mark_previous_complete is True


class TestGetStepStatusInput:
    """Test GetStepStatusInput model."""

    def test_default_values(self):
        """Test default values."""
        input_model = GetStepStatusInput()
        assert input_model.show_all_steps is False

    def test_show_all_steps(self):
        """Test show all steps option."""
        input_model = GetStepStatusInput(show_all_steps=True)
        assert input_model.show_all_steps is True 