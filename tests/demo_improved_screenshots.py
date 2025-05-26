#!/usr/bin/env python3
"""
Demonstration of improved screenshot filtering
"""
import asyncio
import os
import sys

# Add the src directory to the path so we can import our module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_ui_explorer.mcp_ui_explorer import UIExplorer


async def demo_improved_screenshots():
    """Demonstrate the improved screenshot functionality"""
    
    print("✨ Improved Screenshot Functionality Demo")
    print("=" * 45)
    
    ui_explorer = UIExplorer()
    
    print("\n🎯 NEW: Default behavior is now more selective!")
    print("   - Only shows elements >= 20 pixels")
    print("   - Maximum depth of 4 levels")
    print("   - Focus on visible, meaningful elements")
    
    # Take a selective screenshot
    image_data, image_path, cursor_pos = await ui_explorer._screenshot_ui(
        output_prefix="demo_selective"
    )
    print(f"\n✅ Selective screenshot saved: {image_path}")
    
    print("\n🔧 You can still get the old detailed view when needed:")
    print("   - Set min_size=5 for tiny elements")
    print("   - Set max_depth=8 for deep nesting")
    
    # Take a detailed screenshot for comparison
    image_data2, image_path2, cursor_pos2 = await ui_explorer._screenshot_ui(
        output_prefix="demo_detailed",
        min_size=5,
        max_depth=8
    )
    print(f"\n✅ Detailed screenshot saved: {image_path2}")
    
    print("\n🎯 NEW: Focus mode for just the active window:")
    image_data3, image_path3, cursor_pos3 = await ui_explorer._screenshot_ui(
        output_prefix="demo_focus",
        focus_only=True
    )
    print(f"\n✅ Focus screenshot saved: {image_path3}")
    
    print("\n📋 Summary:")
    print("   ✅ More useful screenshots by default")
    print("   ✅ Less visual clutter")
    print("   ✅ Better for UI-TARS model analysis")
    print("   ✅ Still configurable for detailed analysis when needed")
    
    print(f"\n🖼️  Compare the screenshots:")
    print(f"   - {image_path} (NEW default - clean)")
    print(f"   - {image_path2} (detailed - busy)")
    print(f"   - {image_path3} (focus only - minimal)")


if __name__ == "__main__":
    asyncio.run(demo_improved_screenshots()) 