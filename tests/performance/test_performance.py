"""Performance tests for MCP UI Explorer."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from old_way.mcp_ui_explorer import UIExplorer
from mcp_ui_explorer.models import ScreenshotUIInput, ClickUIElementInput
from mcp_ui_explorer.utils import CoordinateConverter
from mcp_ui_explorer.config import get_settings


class TestPerformance:
    """Performance tests for core functionality."""

    @pytest.fixture
    def ui_explorer(self):
        """Create a UIExplorer instance for testing."""
        return UIExplorer()

    def test_ui_explorer_initialization_performance(self, benchmark):
        """Test UIExplorer initialization performance."""
        def create_ui_explorer():
            return UIExplorer()
        
        result = benchmark(create_ui_explorer)
        assert result is not None

    def test_settings_loading_performance(self, benchmark):
        """Test settings loading performance."""
        def load_settings():
            return get_settings(reload=True)
        
        result = benchmark(load_settings)
        assert result is not None

    def test_coordinate_conversion_performance(self, benchmark):
        """Test coordinate conversion performance."""
        converter = CoordinateConverter(screen_width=1920, screen_height=1080)
        
        def convert_coordinates():
            # Convert 1000 coordinate pairs
            for i in range(1000):
                x, y = i % 1920, i % 1080
                norm_x, norm_y = converter.absolute_to_normalized(x, y)
                converter.normalized_to_absolute(norm_x, norm_y)
        
        benchmark(convert_coordinates)

    def test_model_validation_performance(self, benchmark):
        """Test Pydantic model validation performance."""
        def validate_models():
            # Validate 100 model instances
            for i in range(100):
                ScreenshotUIInput(
                    region="screen",
                    min_size=20 + i % 10,
                    max_depth=4,
                    output_prefix=f"test_{i}"
                )
                ClickUIElementInput(
                    x=100 + i,
                    y=200 + i,
                    wait_time=2.0
                )
        
        benchmark(validate_models)

    @pytest.mark.asyncio
    async def test_screenshot_ui_performance(self, benchmark, ui_explorer):
        """Test screenshot UI performance."""
        with patch('pyautogui.screenshot') as mock_screenshot, \
             patch('pywinauto.Desktop') as mock_desktop:
            
            # Mock screenshot
            mock_img = MagicMock()
            mock_img.save = MagicMock()
            mock_screenshot.return_value = mock_img
            
            # Mock desktop
            mock_desktop_instance = MagicMock()
            mock_desktop_instance.windows.return_value = []
            mock_desktop.return_value = mock_desktop_instance
            
            async def take_screenshot():
                return await ui_explorer.screenshot_ui()
            
            # Use benchmark.pedantic for async functions
            result = await benchmark.pedantic(
                take_screenshot,
                iterations=10,
                rounds=3
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_click_performance(self, benchmark, ui_explorer):
        """Test click performance."""
        with patch('pyautogui.click') as mock_click, \
             patch('time.sleep'):
            
            async def perform_click():
                return await ui_explorer.click_ui_element(
                    x=100, y=200, auto_verify=False
                )
            
            result = await benchmark.pedantic(
                perform_click,
                iterations=50,
                rounds=5
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_keyboard_input_performance(self, benchmark, ui_explorer):
        """Test keyboard input performance."""
        with patch('pyautogui.write') as mock_write, \
             patch('time.sleep'):
            
            async def perform_typing():
                return await ui_explorer.keyboard_input(
                    text="Performance test text",
                    auto_verify=False
                )
            
            result = await benchmark.pedantic(
                perform_typing,
                iterations=30,
                rounds=3
            )
            assert result["success"] is True

    def test_memory_operations_performance(self, benchmark, ui_explorer):
        """Test memory operations performance."""
        def memory_operations():
            # Simulate memory operations
            for i in range(10):
                ui_explorer.tool_usage_tracker.track_usage(f"test_tool_{i}")
                ui_explorer.action_logger.log_action(
                    f"test_action_{i}",
                    {"param": i},
                    {"success": True}
                )
        
        benchmark(memory_operations)

    def test_concurrent_model_validation_performance(self, benchmark):
        """Test concurrent model validation performance."""
        def concurrent_validation():
            # Simulate concurrent validation of multiple models
            models = []
            for i in range(50):
                models.append(ScreenshotUIInput(
                    region="screen",
                    min_size=20,
                    max_depth=4,
                    output_prefix=f"concurrent_{i}"
                ))
                models.append(ClickUIElementInput(
                    x=100 + i,
                    y=200 + i
                ))
            return len(models)
        
        result = benchmark(concurrent_validation)
        assert result == 100

    @pytest.mark.asyncio
    async def test_ui_tars_mock_performance(self, benchmark, ui_explorer):
        """Test UI-TARS analysis performance with mocked API."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            image_path = temp_file.name
        
        try:
            # Mock the OpenAI client for fast response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "click(100, 200)"
            
            with patch('openai.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                async def analyze_image():
                    return await ui_explorer.ui_tars_analyze(
                        image_path=image_path,
                        query="find button"
                    )
                
                result = await benchmark.pedantic(
                    analyze_image,
                    iterations=10,
                    rounds=3
                )
                assert result["success"] is True
                
        finally:
            Path(image_path).unlink(missing_ok=True)

    def test_large_data_handling_performance(self, benchmark):
        """Test performance with large data structures."""
        def handle_large_data():
            # Simulate handling large amounts of UI element data
            elements = []
            for i in range(1000):
                element = {
                    "id": f"element_{i}",
                    "type": "Button",
                    "coordinates": {"x": i % 1920, "y": i % 1080},
                    "properties": {
                        "text": f"Button {i}",
                        "enabled": True,
                        "visible": True
                    }
                }
                elements.append(element)
            
            # Process elements
            processed = []
            for element in elements:
                if element["properties"]["enabled"]:
                    processed.append({
                        "id": element["id"],
                        "clickable": True,
                        "position": element["coordinates"]
                    })
            
            return len(processed)
        
        result = benchmark(handle_large_data)
        assert result > 0

    @pytest.mark.asyncio
    async def test_rapid_sequential_operations_performance(self, benchmark, ui_explorer):
        """Test performance of rapid sequential operations."""
        with patch('pyautogui.click'), \
             patch('pyautogui.write'), \
             patch('pyautogui.press'), \
             patch('time.sleep'):
            
            async def rapid_operations():
                # Perform 20 rapid operations
                for i in range(20):
                    await ui_explorer.click_ui_element(
                        x=100 + i, y=200 + i, auto_verify=False
                    )
                    if i % 3 == 0:
                        await ui_explorer.keyboard_input(
                            text=f"test{i}", auto_verify=False
                        )
                    if i % 5 == 0:
                        await ui_explorer.press_key(
                            key="tab", auto_verify=False
                        )
                return i + 1
            
            result = await benchmark.pedantic(
                rapid_operations,
                iterations=5,
                rounds=2
            )
            assert result == 20

    def test_settings_caching_performance(self, benchmark):
        """Test settings caching performance."""
        def access_cached_settings():
            # Access settings multiple times (should be cached)
            for _ in range(100):
                settings = get_settings()  # Should return cached instance
                _ = settings.ui.auto_verify
                _ = settings.ui_tars.api_url
                _ = settings.memory.enabled
        
        benchmark(access_cached_settings)

    def test_logger_performance(self, benchmark):
        """Test logger performance."""
        from mcp_ui_explorer.utils import get_logger
        
        def logging_operations():
            logger = get_logger("performance_test")
            for i in range(100):
                logger.info(f"Performance test log message {i}")
                logger.debug(f"Debug message {i}")
                if i % 10 == 0:
                    logger.warning(f"Warning message {i}")
        
        benchmark(logging_operations)

    @pytest.mark.asyncio
    async def test_memory_usage_performance(self, benchmark, ui_explorer):
        """Test memory usage during operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        async def memory_intensive_operations():
            initial_memory = process.memory_info().rss
            
            # Perform memory-intensive operations
            with patch('pyautogui.screenshot') as mock_screenshot:
                mock_img = MagicMock()
                mock_screenshot.return_value = mock_img
                
                for i in range(10):
                    await ui_explorer.screenshot_ui()
                    # Simulate some processing
                    data = [j for j in range(1000)]
                    del data
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB)
            assert memory_increase < 100 * 1024 * 1024
            
            return memory_increase
        
        result = await benchmark.pedantic(
            memory_intensive_operations,
            iterations=3,
            rounds=2
        )
        assert result >= 0 