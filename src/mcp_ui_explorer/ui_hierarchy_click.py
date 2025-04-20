import json
import sys
import argparse
import pyautogui
import time

def create_parser():
    parser = argparse.ArgumentParser(description='Click on a UI element from the hierarchy')
    parser.add_argument('--json', default='ui_hierarchy_20250419_182127.json', help='Path to JSON hierarchy file')
    parser.add_argument('--wait', type=float, default=2, help='Seconds to wait before clicking')
    parser.add_argument('--path', help='Path to element (e.g., 0.children.3.children.2)')
    return parser

def find_elements_by_criteria(hierarchy, control_type=None, text=None, path=None):
    """Find elements matching criteria"""
    matches = []
    
    def search_element(element, current_path=""):
        # Check if this element matches
        if control_type and element['control_type'] == control_type:
            if not text or (text.lower() in element['text'].lower()):
                matches.append((element, current_path))
        elif text and text.lower() in element['text'].lower():
            matches.append((element, current_path))
            
        # Search children
        if 'children' in element:
            for i, child in enumerate(element['children']):
                search_element(child, f"{current_path}.children.{i}")
    
    # If path is provided, navigate directly to that element
    if path:
        try:
            element = hierarchy
            for part in path.split('.'):
                if part.isdigit():
                    element = element[int(part)]
                else:
                    element = element[part]
            matches.append((element, path))
        except Exception as e:
            print(f"Error navigating to path {path}: {str(e)}")
    else:
        # Otherwise search the whole hierarchy
        for i, window in enumerate(hierarchy):
            search_element(window, str(i))
    
    return matches

def click_element(element):
    """Click on an element using its coordinates"""
    position = element['position']
    x = position['left'] + position['width'] // 2
    y = position['top'] + position['height'] // 2
    
    print(f"Clicking at ({x}, {y})")
    pyautogui.click(x, y)

def main():
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Validate inputs
    if not args.type and not args.text and not args.path:
        print("Error: You must specify at least one search criteria (--type, --text, or --path)")
        return
    
    # Load the JSON file
    try:
        with open(args.json, 'r', encoding='utf-8') as f:
            hierarchy = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {str(e)}")
        return
    
    # Find matching elements
    matches = find_elements_by_criteria(hierarchy, args.type, args.text, args.path)
    
    if not matches:
        print("No matching elements found.")
        return
    
    # Display matches
    print(f"Found {len(matches)} matching elements:")
    for i, (element, path) in enumerate(matches):
        text = element['text']
        if len(text) > 30:
            text = text[:27] + "..."
        print(f"{i+1}. Type: {element['control_type']}, Text: {text}")
        print(f"   Path: {path}")
        print(f"   Position: {element['position']}")
    
    # If multiple matches, prompt user to select one
    selected, path = matches[0]  # Default to first match
    if len(matches) > 1:
        choice = input(f"Enter number to select element (1-{len(matches)}) or press Enter for first match: ")
        if choice and choice.isdigit() and 1 <= int(choice) <= len(matches):
            selected, path = matches[int(choice)-1]
    
    # Print selection details
    print(f"Selected element:")
    print(f"- Type: {selected['control_type']}")
    print(f"- Text: {selected['text']}")
    print(f"- Path: {path}")
    print(f"- Position: {selected['position']}")
    
    # Wait before clicking
    print(f"Waiting {args.wait} seconds before clicking...")
    time.sleep(args.wait)
    
    # Click the element
    click_element(selected)

if __name__ == "__main__":
    main()
