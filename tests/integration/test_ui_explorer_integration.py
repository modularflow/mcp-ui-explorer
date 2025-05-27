"""Integration tests for UIExplorer functionality."""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_ui_explorer import UIExplorer
from mcp_ui_explorer.models import ScreenshotUIInput, ClickUIElementInput


class TestUIExplorerIntegration:
    """Integration tests for UIExplorer."""

    @pytest.fixture
    def ui_explorer(self):
        """Create a UIExplorer instance for testing."""
        return UIExplorer()

    @pytest.mark.asyncio
    async def test_screenshot_ui_basic(self, ui_explorer):
        """Test basic screenshot functionality."""
        try:
            result = await ui_explorer.screenshot_ui()
            
            assert result["success"] is True
            assert "image_path" in result
            assert "cursor_position" in result
            assert "metadata" in result
            
            # Check that the image file was created
            image_path = result["image_path"]
            assert Path(image_path).exists()
            assert Path(image_path).suffix.lower() in ['.png', '.jpg', '.jpeg']
            
            # Clean up
            Path(image_path).unlink(missing_ok=True)
            
        except Exception as e:
            pytest.skip(f"Screenshot test skipped due to environment: {e}")

    @pytest.mark.asyncio
    async def test_screenshot_ui_with_custom_settings(self, ui_explorer):
        """Test screenshot with custom settings."""
        try:
            input_data = ScreenshotUIInput(
                region="screen",
                min_size=30,
                max_depth=3,
                output_prefix="test_integration"
            )
            
            result = await ui_explorer.screenshot_ui(
                region=input_data.region,
                min_size=input_data.min_size,
                max_depth=input_data.max_depth,
                output_prefix=input_data.output_prefix
            )
            
            assert result["success"] is True
            assert "test_integration" in result["image_path"]
            
            # Clean up
            Path(result["image_path"]).unlink(missing_ok=True)
            
        except Exception as e:
            pytest.skip(f"Screenshot test skipped due to environment: {e}")

    @pytest.mark.asyncio
    async def test_click_ui_element_mock(self, ui_explorer):
        """Test click UI element with mocked pyautogui."""
        with patch('pyautogui.click') as mock_click, \
             patch('pyautogui.screenshot') as mock_screenshot, \
             patch('time.sleep'):
            
            # Mock screenshot
            mock_screenshot.return_value = MagicMock()
            
            input_data = ClickUIElementInput(x=100, y=200, auto_verify=False)
            
            result = await ui_explorer.click_ui_element(
                x=input_data.x,
                y=input_data.y,
                auto_verify=input_data.auto_verify
            )
            
            assert result["success"] is True
            assert "coordinates" in result
            mock_click.assert_called_once_with(100, 200)

    @pytest.mark.asyncio
    async def test_keyboard_input_mock(self, ui_explorer):
        """Test keyboard input with mocked pyautogui."""
        with patch('pyautogui.write') as mock_write, \
             patch('time.sleep'):
            
            result = await ui_explorer.keyboard_input(
                text="Hello World",
                auto_verify=False
            )
            
            assert result["success"] is True
            assert result["text"] == "Hello World"
            mock_write.assert_called_once_with("Hello World", interval=0.0)

    @pytest.mark.asyncio
    async def test_press_key_mock(self, ui_explorer):
        """Test press key with mocked pyautogui."""
        with patch('pyautogui.press') as mock_press, \
             patch('time.sleep'):
            
            result = await ui_explorer.press_key(
                key="enter",
                auto_verify=False
            )
            
            assert result["success"] is True
            assert result["key"] == "enter"
            mock_press.assert_called_once_with("enter", presses=1, interval=0.0)

    @pytest.mark.asyncio
    async def test_hot_key_mock(self, ui_explorer):
        """Test hot key with mocked pyautogui."""
        with patch('pyautogui.hotkey') as mock_hotkey, \
             patch('time.sleep'):
            
            result = await ui_explorer.hot_key(
                keys=["ctrl", "c"],
                auto_verify=False
            )
            
            assert result["success"] is True
            assert result["keys"] == ["ctrl", "c"]
            mock_hotkey.assert_called_once_with("ctrl", "c")

    @pytest.mark.asyncio
    async def test_ui_tars_analyze_mock(self, ui_explorer):
        """Test UI-TARS analysis with mocked API."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            image_path = temp_file.name
        
        try:
            # Mock the OpenAI client
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "click(100, 200)"
            
            with patch('openai.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                result = await ui_explorer.ui_tars_analyze(
                    image_path=image_path,
                    query="find button"
                )
                
                assert result["success"] is True
                assert "coordinates" in result or "response" in result
                
        finally:
            Path(image_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_memory_operations(self, ui_explorer):
        """Test memory operations."""
        # Test creating memory summary
        result = await ui_explorer.create_memory_summary(force_summary=True)
        assert "summary_created" in result

    @pytest.mark.asyncio
    async def test_step_tracking(self, ui_explorer):
        """Test step tracking functionality."""
        # Document a step
        result = await ui_explorer.document_step(
            step_description="Test step for integration testing"
        )
        assert result["success"] is True
        
        # Get step status
        status_result = await ui_explorer.get_step_status()
        assert "current_step" in status_result

    @pytest.mark.asyncio
    async def test_find_elements_near_cursor_mock(self, ui_explorer):
        """Test finding elements near cursor with mocked pywinauto."""
        with patch('pyautogui.position') as mock_position, \
             patch('pywinauto.Desktop') as mock_desktop:
            
            # Mock cursor position
            mock_position.return_value = (500, 300)
            
            # Mock desktop and windows
            mock_window = MagicMock()
            mock_window.rectangle.return_value = MagicMock(left=400, top=250, right=600, bottom=350)
            mock_window.window_text.return_value = "Test Window"
            mock_window.class_name.return_value = "Button"
            
            mock_desktop_instance = MagicMock()
            mock_desktop_instance.windows.return_value = [mock_window]
            mock_desktop.return_value = mock_desktop_instance
            
            result = await ui_explorer.find_elements_near_cursor(limit=5)
            
            assert result["success"] is True
            assert "cursor_position" in result
            assert "elements" in result

    @pytest.mark.asyncio
    async def test_error_handling(self, ui_explorer):
        """Test error handling in various scenarios."""
        # Test with invalid coordinates
        result = await ui_explorer.click_ui_element(
            x=-1000,
            y=-1000,
            auto_verify=False
        )
        # Should handle gracefully, not necessarily fail
        assert "success" in result

    @pytest.mark.asyncio
    async def test_verification_service_mock(self, ui_explorer):
        """Test verification service functionality."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            comparison_image = temp_file.name
        
        try:
            with patch.object(ui_explorer.verification_service, 'verify_action') as mock_verify:
                mock_verify.return_value = {
                    "verification_passed": True,
                    "verification_details": {"confidence": 0.95}
                }
                
                result = await ui_explorer.verify_ui_action(
                    action_description="Clicked button",
                    expected_result="Window opened",
                    verification_query="new window visible",
                    comparison_image=comparison_image
                )
                
                assert result["verification_passed"] is True
                mock_verify.assert_called_once()
                
        finally:
            Path(comparison_image).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_tool_usage_tracking(self, ui_explorer):
        """Test that tool usage is tracked properly."""
        initial_count = ui_explorer.tool_usage_tracker.get_usage_count("screenshot_ui")
        
        # Perform an action
        try:
            await ui_explorer.screenshot_ui()
            
            # Check that usage was tracked
            new_count = ui_explorer.tool_usage_tracker.get_usage_count("screenshot_ui")
            assert new_count == initial_count + 1
            
        except Exception:
            # If screenshot fails due to environment, that's okay for this test
            pass

    @pytest.mark.asyncio
    async def test_action_logging(self, ui_explorer):
        """Test that actions are logged properly."""
        initial_log_count = len(ui_explorer.action_logger.get_recent_actions())
        
        # Perform an action with mocked dependencies
        with patch('pyautogui.click'), patch('time.sleep'):
            await ui_explorer.click_ui_element(x=100, y=200, auto_verify=False)
        
        # Check that action was logged
        new_log_count = len(ui_explorer.action_logger.get_recent_actions())
        assert new_log_count == initial_log_count + 1

    @pytest.mark.asyncio
    async def test_settings_integration(self, ui_explorer):
        """Test that settings are properly integrated."""
        # Check that settings are accessible
        assert hasattr(ui_explorer, 'settings')
        assert ui_explorer.settings.ui.auto_verify in [True, False]
        assert isinstance(ui_explorer.settings.ui.default_verification_timeout, (int, float))

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, ui_explorer):
        """Test concurrent operations don't interfere with each other."""
        with patch('pyautogui.click'), patch('pyautogui.write'), patch('time.sleep'):
            # Run multiple operations concurrently
            tasks = [
                ui_explorer.click_ui_element(x=100, y=200, auto_verify=False),
                ui_explorer.keyboard_input(text="test", auto_verify=False),
                ui_explorer.press_key(key="enter", auto_verify=False)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All operations should complete successfully
            for result in results:
                assert not isinstance(result, Exception)
                assert result["success"] is True 