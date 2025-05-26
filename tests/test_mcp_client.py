#!/usr/bin/env python3
"""
Test the UI-TARS functionality through MCP client
"""
import asyncio
import json
import subprocess
import sys
import os

async def test_mcp_tools():
    """Test MCP tools including UI-TARS"""
    
    print("🔧 Testing MCP UI Explorer Tools")
    print("=" * 40)
    
    # First, let's start the MCP server in the background and test tools
    from mcp_ui_explorer.mcp_ui_explorer import UIExplorer
    
    ui_explorer = UIExplorer()
    
    # Test 1: Take a screenshot
    print("📸 Test 1: Taking screenshot...")
    try:
        image_data, image_path, cursor_pos = await ui_explorer._screenshot_ui(
            output_prefix="mcp_test"
        )
        print(f"✅ Screenshot saved: {image_path}")
    except Exception as e:
        print(f"❌ Screenshot failed: {e}")
        return
    
    # Test 2: Use UI-TARS to find an element
    print("\n🤖 Test 2: Using UI-TARS to find start button...")
    try:
        result = await ui_explorer._ui_tars_analyze(
            image_path=image_path,
            query="start button"
        )
        
        if result['success'] and result.get('found'):
            coords = result['coordinates']
            print(f"✅ Found start button!")
            print(f"   Absolute coords: ({coords['absolute']['x']}, {coords['absolute']['y']})")
            
            # Test 3: Click on the found coordinates
            print(f"\n🖱️  Test 3: Clicking on found coordinates...")
            click_result = await ui_explorer._click_ui_element(
                x=coords['absolute']['x'],
                y=coords['absolute']['y'],
                wait_time=0.5
            )
            
            if click_result['success']:
                print(f"✅ Click successful!")
                print(f"   Message: {click_result['message']}")
            else:
                print(f"❌ Click failed: {click_result.get('error')}")
                
        else:
            print(f"❌ UI-TARS analysis failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ UI-TARS test failed: {e}")
    
    print("\n📋 MCP Tools Test Completed!")

if __name__ == "__main__":
    # Add the src directory to the path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    asyncio.run(test_mcp_tools()) 