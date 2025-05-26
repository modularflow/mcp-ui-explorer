#!/usr/bin/env python3
"""
Test script to compare screenshot filtering behavior
"""
import asyncio
import os
import sys

# Add the src directory to the path so we can import our module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_ui_explorer.mcp_ui_explorer import UIExplorer


async def test_screenshot_filtering():
    """Test different screenshot filtering options"""
    
    print("📸 Testing Screenshot Filtering Options")
    print("=" * 50)
    
    ui_explorer = UIExplorer()
    
    # Test 1: Default new behavior (should be more selective)
    print("\n🎯 Test 1: New default behavior (selective)")
    print("Parameters: min_size=20, max_depth=4, focus_only=False")
    try:
        image_data, image_path, cursor_pos = await ui_explorer._screenshot_ui(
            output_prefix="selective_test"
        )
        print(f"✅ Selective screenshot saved: {image_path}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 2: Old behavior (show everything)
    print("\n📋 Test 2: Old behavior (show everything)")
    print("Parameters: min_size=5, max_depth=8, focus_only=False")
    try:
        image_data, image_path, cursor_pos = await ui_explorer._screenshot_ui(
            output_prefix="detailed_test",
            min_size=5,
            max_depth=8,
            focus_only=False
        )
        print(f"✅ Detailed screenshot saved: {image_path}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 3: Focus only on foreground window
    print("\n🎯 Test 3: Focus on foreground window only")
    print("Parameters: min_size=15, max_depth=4, focus_only=True")
    try:
        image_data, image_path, cursor_pos = await ui_explorer._screenshot_ui(
            output_prefix="focus_test",
            min_size=15,
            max_depth=4,
            focus_only=True
        )
        print(f"✅ Focus screenshot saved: {image_path}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 4: Very selective (large elements only)
    print("\n🎯 Test 4: Very selective (large elements only)")
    print("Parameters: min_size=50, max_depth=3, focus_only=False")
    try:
        image_data, image_path, cursor_pos = await ui_explorer._screenshot_ui(
            output_prefix="minimal_test",
            min_size=50,
            max_depth=3,
            focus_only=False
        )
        print(f"✅ Minimal screenshot saved: {image_path}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    print(f"\n📋 Test completed! Compare the different screenshots to see the difference:")
    print("- selective_test_*.png - New default (balanced)")
    print("- detailed_test_*.png - Old behavior (everything)")
    print("- focus_test_*.png - Foreground window only")
    print("- minimal_test_*.png - Large elements only")


if __name__ == "__main__":
    asyncio.run(test_screenshot_filtering()) 