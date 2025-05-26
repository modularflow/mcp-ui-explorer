#!/usr/bin/env python3
"""
Manual test of the UI-TARS API to verify it's working directly
"""
import base64
import json
from openai import OpenAI

def test_manual_api():
    """Test the UI-TARS API directly"""
    
    # Find the most recent screenshot
    import glob
    import os
    
    screenshot_files = glob.glob("test_ui_tars_*.png")
    if not screenshot_files:
        print("❌ No test screenshots found. Run the main test first!")
        return
    
    # Use the most recent screenshot
    image_path = max(screenshot_files, key=os.path.getctime)
    print(f"📸 Using screenshot: {image_path}")
    
    # Load and encode image
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # Initialize OpenAI client
    client = OpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="dummy"
    )
    
    # Test query
    query = "Find the Windows start button"
    
    print(f"🔍 Query: {query}")
    print("⏳ Sending request to UI-TARS...")
    
    try:
        response = client.chat.completions.create(
            model="ui-tars-7b-dpo",
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": query},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=150,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ Raw response: {result}")
        
        # Try to extract coordinates
        import re
        coord_match = re.search(r'\(([0-9.]+),([0-9.]+)\)', result)
        if coord_match:
            x, y = float(coord_match.group(1)), float(coord_match.group(2))
            print(f"📍 Extracted coordinates: ({x}, {y})")
        else:
            print("⚠️  Could not extract coordinates from response")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_manual_api() 