#!/usr/bin/env python3
"""
Test script for debugging Firefox button detection on Windows taskbar.
"""

import sys
import time
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.mcp_ui_explorer.services.macro_recorder import MacroRecorder
from src.mcp_ui_explorer.utils.logging import setup_logging
import pyautogui

def test_firefox_detection():
    """Test Firefox button detection with enhanced debugging."""
    
    # Set up logging with DEBUG level
    logger = setup_logging()
    
    # Set the macro recorder logger to DEBUG level to see all output
    macro_logger = logging.getLogger('src.mcp_ui_explorer.services.macro_recorder')
    macro_logger.setLevel(logging.DEBUG)
    
    # Also add a console handler to see the debug output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    console_handler.setFormatter(formatter)
    macro_logger.addHandler(console_handler)
    
    # Create macro recorder
    recorder = MacroRecorder()
    
    print("Firefox Button Detection Test")
    print("="*50)
    print()
    print("Instructions:")
    print("1. Make sure Firefox is open and visible in your taskbar")
    print("2. When prompted, position mouse over the Firefox button")
    print("3. The script will analyze what element is detected")
    print()
    
    # Wait for user to position cursor
    print("Position your mouse over the Firefox button in the taskbar...")
    print("Detection test will start in 5 seconds...")
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    
    # Get current cursor position
    x, y = pyautogui.position()
    print(f"\nTesting detection at cursor position: ({x}, {y})")
    print("Debug output will follow:")
    print("-" * 50)
    
    # Test the detection
    try:
        element = recorder._get_element_at_point(x, y)
        
        print("-" * 50)
        print("\nDetection Results:")
        print("="*30)
        
        if element:
            print(f"Control Type: {element.get('control_type', 'Unknown')}")
            print(f"Text: '{element.get('text', '')}'")
            print(f"Position: {element.get('position', {})}")
            print(f"Distance: {element.get('distance', 'Unknown')}")
            print(f"Detection Method: {element.get('properties', {}).get('detection_method', 'Unknown')}")
            
            properties = element.get('properties', {})
            if properties:
                print("\nProperties:")
                for key, value in properties.items():
                    print(f"  {key}: {value}")
            
            # Check for context hierarchy
            context = element.get('context_hierarchy', [])
            if context:
                print(f"\nContext Hierarchy ({len(context)} elements):")
                for i, ctx_elem in enumerate(context):
                    print(f"  {i+1}. Depth {ctx_elem.get('depth', '?')}: {ctx_elem.get('control_type', 'Unknown')} '{ctx_elem.get('text', '')}'")
            
        else:
            print("No element detected!")
            
    except Exception as e:
        print(f"Error during detection: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_firefox_detection() 