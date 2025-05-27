"""Unit tests for utility functions."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_ui_explorer.utils import (
    get_logger,
    setup_logging,
    CoordinateConverter,
)


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_get_logger_with_module_name(self):
        """Test get_logger with __name__ parameter."""
        logger = get_logger(__name__)
        assert logger.name == __name__

    def test_get_logger_singleton_behavior(self):
        """Test that get_logger returns the same instance for the same name."""
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Test that get_logger returns different instances for different names."""
        logger1 = get_logger("name1")
        logger2 = get_logger("name2")
        assert logger1 is not logger2
        assert logger1.name != logger2.name


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_default_level(self):
        """Test setup_logging with default level."""
        with patch('mcp_ui_explorer.config.get_settings') as mock_settings:
            mock_settings.return_value.logging.level = "INFO"
            mock_settings.return_value.logging.format = "%(message)s"
            
            logger = setup_logging()
            assert isinstance(logger, logging.Logger)
            assert logger.level == logging.INFO

    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom level."""
        with patch('mcp_ui_explorer.config.get_settings') as mock_settings:
            mock_settings.return_value.logging.level = "INFO"
            mock_settings.return_value.logging.format = "%(message)s"
            
            logger = setup_logging(level="DEBUG")
            assert logger.level == logging.DEBUG

    def test_setup_logging_invalid_level(self):
        """Test setup_logging with invalid level."""
        with patch('mcp_ui_explorer.config.get_settings') as mock_settings:
            mock_settings.return_value.logging.level = "INFO"
            mock_settings.return_value.logging.format = "%(message)s"
            
            with pytest.raises(AttributeError):
                setup_logging(level="INVALID_LEVEL")

    def test_setup_logging_custom_format(self):
        """Test setup_logging with custom format."""
        with patch('mcp_ui_explorer.config.get_settings') as mock_settings:
            mock_settings.return_value.logging.level = "INFO"
            mock_settings.return_value.logging.format = "%(message)s"
            
            custom_format = "%(name)s - %(message)s"
            logger = setup_logging(format_string=custom_format)
            
            # Check that the logger has handlers with the custom format
            assert len(logger.handlers) > 0
            handler = logger.handlers[0]
            assert handler.formatter._fmt == custom_format

    def test_setup_logging_custom_logger_name(self):
        """Test setup_logging with custom logger name."""
        with patch('mcp_ui_explorer.config.get_settings') as mock_settings:
            mock_settings.return_value.logging.level = "INFO"
            mock_settings.return_value.logging.format = "%(message)s"
            
            logger = setup_logging(logger_name="custom_logger")
            assert logger.name == "custom_logger"


class TestCoordinateConverter:
    """Test CoordinateConverter utility class."""

    def test_get_screen_size(self):
        """Test getting screen size."""
        with patch('pyautogui.size') as mock_size:
            mock_size.return_value = (1920, 1080)
            
            width, height = CoordinateConverter.get_screen_size()
            assert width == 1920
            assert height == 1080

    def test_normalize_coordinates(self):
        """Test normalizing coordinates."""
        with patch('pyautogui.size') as mock_size:
            mock_size.return_value = (1920, 1080)
            
            # Test center of screen
            result = CoordinateConverter.normalize_coordinates(960, 540)
            assert abs(result["x"] - 0.5) < 0.001
            assert abs(result["y"] - 0.5) < 0.001
            
            # Test top-left corner
            result = CoordinateConverter.normalize_coordinates(0, 0)
            assert result["x"] == 0.0
            assert result["y"] == 0.0

    def test_denormalize_coordinates(self):
        """Test denormalizing coordinates."""
        with patch('pyautogui.size') as mock_size:
            mock_size.return_value = (1920, 1080)
            
            # Test center of screen
            result = CoordinateConverter.denormalize_coordinates(0.5, 0.5)
            assert result["x"] == 960
            assert result["y"] == 540
            
            # Test top-left corner
            result = CoordinateConverter.denormalize_coordinates(0.0, 0.0)
            assert result["x"] == 0
            assert result["y"] == 0

    def test_convert_coordinates_absolute_input(self):
        """Test converting absolute coordinates."""
        with patch('pyautogui.size') as mock_size:
            mock_size.return_value = (1920, 1080)
            
            result = CoordinateConverter.convert_coordinates(960, 540, normalized=False)
            
            assert "normalized" in result
            assert "absolute" in result
            assert abs(result["normalized"]["x"] - 0.5) < 0.001
            assert abs(result["normalized"]["y"] - 0.5) < 0.001
            assert result["absolute"]["x"] == 960
            assert result["absolute"]["y"] == 540

    def test_convert_coordinates_normalized_input(self):
        """Test converting normalized coordinates."""
        with patch('pyautogui.size') as mock_size:
            mock_size.return_value = (1920, 1080)
            
            result = CoordinateConverter.convert_coordinates(0.5, 0.5, normalized=True)
            
            assert "normalized" in result
            assert "absolute" in result
            assert result["normalized"]["x"] == 0.5
            assert result["normalized"]["y"] == 0.5
            assert result["absolute"]["x"] == 960
            assert result["absolute"]["y"] == 540

    def test_create_coordinate_info(self):
        """Test creating comprehensive coordinate information."""
        with patch('pyautogui.size') as mock_size:
            mock_size.return_value = (1920, 1080)
            
            result = CoordinateConverter.create_coordinate_info(960, 540)
            
            assert "input" in result
            assert "coordinates" in result
            assert "screen_dimensions" in result
            
            assert result["input"]["x"] == 960
            assert result["input"]["y"] == 540
            assert result["input"]["type"] == "absolute"
            
            assert result["screen_dimensions"]["width"] == 1920
            assert result["screen_dimensions"]["height"] == 1080

    def test_create_coordinate_info_without_screen_info(self):
        """Test creating coordinate info without screen dimensions."""
        with patch('pyautogui.size') as mock_size:
            mock_size.return_value = (1920, 1080)
            
            result = CoordinateConverter.create_coordinate_info(
                960, 540, include_screen_info=False
            )
            
            assert "input" in result
            assert "coordinates" in result
            assert "screen_dimensions" not in result

    def test_coordinate_conversion_roundtrip(self):
        """Test that coordinate conversion is reversible."""
        with patch('pyautogui.size') as mock_size:
            mock_size.return_value = (1920, 1080)
            
            # Test various coordinates
            test_coords = [(100, 200), (960, 540), (1800, 1000)]
            
            for orig_x, orig_y in test_coords:
                # Convert to normalized and back
                norm_result = CoordinateConverter.normalize_coordinates(orig_x, orig_y)
                abs_result = CoordinateConverter.denormalize_coordinates(
                    norm_result["x"], norm_result["y"]
                )
                
                assert abs_result["x"] == orig_x
                assert abs_result["y"] == orig_y

    def test_edge_case_coordinates(self):
        """Test edge case coordinates."""
        with patch('pyautogui.size') as mock_size:
            mock_size.return_value = (1920, 1080)
            
            # Test coordinates at screen edges
            result = CoordinateConverter.normalize_coordinates(1920, 1080)
            assert result["x"] == 1.0
            assert result["y"] == 1.0
            
            # Test coordinates outside screen bounds
            result = CoordinateConverter.normalize_coordinates(2000, 1200)
            assert result["x"] > 1.0
            assert result["y"] > 1.0 