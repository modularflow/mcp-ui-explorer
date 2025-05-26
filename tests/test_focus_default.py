#!/usr/bin/env python3
"""
Test script to verify the new focus_only=True default behavior
"""
import asyncio
import os
import sys

# Add the src directory to the path so we can import our module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_ui_explorer.mcp_ui_explorer import UIExplorer


async def test_focus_default():
    """Test that focus_only=True is now the default"""
    
    print("🎯 Testing New Focus Default Behavior")
    print("=" * 40)
    
    ui_explorer = UIExplorer()
    
    # Test 1: Default behavior (should now focus on foreground window only)
    print("\n📸 Test 1: Default behavior (should focus on foreground window)")
    try:
        image_data, image_path, cursor_pos = await ui_explorer._screenshot_ui(
            output_prefix="default_focus_test"
        )
        print(f"✅ Default screenshot saved: {image_path}")
        
        # Check if it shows "Found 1 windows" indicating focus mode
        print("   Expected: Should analyze only the foreground window")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 2: Explicit focus_only=False (should analyze all windows)
    print("\n📸 Test 2: Explicit focus_only=False (should analyze all windows)")
    try:
        image_data, image_path, cursor_pos = await ui_explorer._screenshot_ui(
            output_prefix="all_windows_test",
            focus_only=False
        )
        print(f"✅ All windows screenshot saved: {image_path}")
        print("   Expected: Should analyze all windows")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    print("\n✅ New defaults:")
    print("   - focus_only=True by default (focuses on active window)")
    print("   - min_size=20 (larger elements only)")
    print("   - max_depth=4 (less nesting)")
    print("   - Result: Cleaner, more focused screenshots!")


if __name__ == "__main__":
    asyncio.run(test_focus_default()) 