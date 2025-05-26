#!/usr/bin/env python3
"""
Test script for the UI-TARS analyze function
"""
import asyncio
import os
import sys
import json
from pathlib import Path

# Add the src directory to the path so we can import our module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_ui_explorer.mcp_ui_explorer import UIExplorer
import pyautogui


async def test_ui_tars():
    """Test the UI-TARS analyze function"""
    
    print("🧪 Testing UI-TARS Integration")
    print("=" * 50)
    
    # Create UIExplorer instance
    ui_explorer = UIExplorer()
    
    # Step 1: Take a screenshot first
    print("📸 Taking a screenshot...")
    try:
        image_data, image_path, cursor_pos = await ui_explorer._screenshot_ui(
            region="screen",
            output_prefix="test_ui_tars"
        )
        print(f"✅ Screenshot saved to: {image_path}")
    except Exception as e:
        print(f"❌ Failed to take screenshot: {e}")
        return
    
    # Step 2: Test UI-TARS analysis
    print("\n🤖 Testing UI-TARS analysis...")
    
    # Test cases
    test_queries = [
        "start button",
        "taskbar",
        "desktop",
        "windows logo",
        "system tray"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test {i}: Looking for '{query}' ---")
        
        try:
            result = await ui_explorer._ui_tars_analyze(
                image_path=image_path,
                query=query,
                api_url="http://127.0.0.1:1234/v1",
                model_name="ui-tars-7b-dpo"
            )
            
            print(f"Success: {result['success']}")
            
            if result['success'] and result.get('found'):
                coords = result['coordinates']
                print(f"✅ Found '{query}'!")
                print(f"   Normalized coordinates: ({coords['normalized']['x']:.3f}, {coords['normalized']['y']:.3f})")
                print(f"   Absolute coordinates: ({coords['absolute']['x']}, {coords['absolute']['y']})")
                print(f"   Model response: {result['response']}")
            elif result['success'] and not result.get('found'):
                print(f"⚠️  '{query}' not found or couldn't parse coordinates")
                print(f"   Model response: {result['response']}")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Exception during analysis: {e}")
        
        # Small delay between requests
        await asyncio.sleep(1)
    
    print(f"\n📋 Test completed! Screenshot available at: {image_path}")


async def test_simple_ui_tars():
    """Simple test with one query"""
    print("🎯 Simple UI-TARS Test")
    print("=" * 30)
    
    ui_explorer = UIExplorer()
    
    # Take screenshot
    print("Taking screenshot...")
    image_data, image_path, cursor_pos = await ui_explorer._screenshot_ui()
    
    # Test with a simple query
    result = await ui_explorer._ui_tars_analyze(
        image_path=image_path,
        query="taskbar"
    )
    
    print("\n📊 Result:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Full test (multiple queries)")
    print("2. Simple test (single query)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(test_ui_tars())
    elif choice == "2":
        asyncio.run(test_simple_ui_tars())
    else:
        print("Invalid choice. Running simple test...")
        asyncio.run(test_simple_ui_tars()) 