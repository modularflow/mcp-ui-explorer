"""Coordinate conversion utilities for MCP UI Explorer."""

from typing import Dict, Any, Tuple
import pyautogui


class CoordinateConverter:
    """Utility class for coordinate conversions."""
    
    @staticmethod
    def get_screen_size() -> Tuple[int, int]:
        """Get the current screen size."""
        return pyautogui.size()
    
    @staticmethod
    def normalize_coordinates(x: float, y: float) -> Dict[str, float]:
        """
        Convert absolute coordinates to normalized (0-1) coordinates.
        
        Args:
            x: Absolute X coordinate
            y: Absolute Y coordinate
            
        Returns:
            Dictionary with normalized coordinates
        """
        screen_width, screen_height = CoordinateConverter.get_screen_size()
        return {
            "x": x / screen_width,
            "y": y / screen_height
        }
    
    @staticmethod
    def denormalize_coordinates(x: float, y: float) -> Dict[str, int]:
        """
        Convert normalized (0-1) coordinates to absolute coordinates.
        
        Args:
            x: Normalized X coordinate (0-1)
            y: Normalized Y coordinate (0-1)
            
        Returns:
            Dictionary with absolute coordinates
        """
        screen_width, screen_height = CoordinateConverter.get_screen_size()
        return {
            "x": int(x * screen_width),
            "y": int(y * screen_height)
        }
    
    @staticmethod
    def convert_coordinates(
        x: float, 
        y: float, 
        normalized: bool = False
    ) -> Dict[str, Any]:
        """
        Convert coordinates to both normalized and absolute formats.
        
        Args:
            x: X coordinate
            y: Y coordinate
            normalized: Whether input coordinates are normalized
            
        Returns:
            Dictionary with both normalized and absolute coordinates
        """
        if normalized:
            # Input is normalized, convert to absolute
            abs_coords = CoordinateConverter.denormalize_coordinates(x, y)
            return {
                "normalized": {"x": x, "y": y},
                "absolute": abs_coords
            }
        else:
            # Input is absolute, convert to normalized
            norm_coords = CoordinateConverter.normalize_coordinates(x, y)
            return {
                "normalized": norm_coords,
                "absolute": {"x": int(x), "y": int(y)}
            }
    
    @staticmethod
    def create_coordinate_info(
        x: float,
        y: float,
        normalized: bool = False,
        include_screen_info: bool = True
    ) -> Dict[str, Any]:
        """
        Create comprehensive coordinate information.
        
        Args:
            x: X coordinate
            y: Y coordinate
            normalized: Whether input coordinates are normalized
            include_screen_info: Whether to include screen dimension info
            
        Returns:
            Dictionary with coordinate information
        """
        coords = CoordinateConverter.convert_coordinates(x, y, normalized)
        
        result = {
            "input": {
                "x": x,
                "y": y,
                "type": "normalized" if normalized else "absolute"
            },
            "coordinates": coords
        }
        
        if include_screen_info:
            screen_width, screen_height = CoordinateConverter.get_screen_size()
            result["screen_dimensions"] = {
                "width": screen_width,
                "height": screen_height
            }
        
        return result 