#!/usr/bin/env python3
"""
Test script for detecting elements in different areas of the screen.
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

def test_area_detection():
    """Test element detection in different screen areas."""
    
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
    
    print("Element Detection Test - Different Areas")
    print("="*50)
    print()
    
    # Test different areas
    test_areas = [
        ("Start Button Area", (50, 1420)),
        ("Desktop Center", (960, 540)),
        ("Top of Screen", (960, 50)),
        ("Right Side Taskbar", (1800, 1420)),
        ("System Tray Area", (1850, 1420)),
    ]
    
    for area_name, (x, y) in test_areas:
        print(f"\n{area_name}")
        print("="*30)
        print(f"Testing detection at: ({x}, {y})")
        print("Debug output:")
        print("-" * 30)
        
        try:
            element = recorder._get_element_at_point(x, y)
            
            print("-" * 30)
            print("Results:")
            
            if element:
                print(f"  Control Type: {element.get('control_type', 'Unknown')}")
                print(f"  Text: '{element.get('text', '')}'")
                print(f"  Detection Method: {element.get('properties', {}).get('detection_method', 'Unknown')}")
                print(f"  Class: {element.get('properties', {}).get('class_name', 'Unknown')}")
            else:
                print("  No element detected!")
                
        except Exception as e:
            print(f"  Error: {e}")
        
        print()
        time.sleep(1)  # Brief pause between tests
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_area_detection() 