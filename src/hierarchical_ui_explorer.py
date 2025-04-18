import sys
import os
import json
import time
import argparse
import pyautogui
from pywinauto import Desktop
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import xml.dom.minidom as minidom
from xml.etree import ElementTree as ET

def create_parser():
    parser = argparse.ArgumentParser(description='Explore UI elements hierarchically and export to JSON')
    parser.add_argument('--output', type=str, default='', help='Output filename prefix')
    parser.add_argument('--region', type=str, help='Region to analyze: "screen", "top", "bottom", "left", "right", "top-left", "top-right", "bottom-left", "bottom-right", or custom "left,top,right,bottom" coordinates')
    parser.add_argument('--depth', type=int, default=5, help='Maximum depth to analyze')
    parser.add_argument('--min-size', type=int, default=5, help='Minimum element size to include')
    parser.add_argument('--focus-window', action='store_true', help='Only analyze the foreground window')
    parser.add_argument('--highlight-levels', action='store_true', help='Use different colors for hierarchy levels')
    parser.add_argument('--format', choices=['json', 'xml', 'both'], default='json', help='Output format (json, xml, or both)')
    parser.add_argument('--visible-only', action='store_true', help='Only include elements visible on screen')
    return parser

# Define predefined regions
def get_predefined_regions():
    screen_width, screen_height = pyautogui.size()
    half_width = screen_width // 2
    half_height = screen_height // 2
    
    return {
        "screen": (0, 0, screen_width, screen_height),
        "top": (0, 0, screen_width, half_height),
        "bottom": (0, half_height, screen_width, screen_height),
        "left": (0, 0, half_width, screen_height),
        "right": (half_width, 0, screen_width, screen_height),
        "top-left": (0, 0, half_width, half_height),
        "top-right": (half_width, 0, screen_width, half_height),
        "bottom-left": (0, half_height, half_width, screen_height),
        "bottom-right": (half_width, half_height, screen_width, screen_height),
        "center": (screen_width//4, screen_height//4, screen_width*3//4, screen_height*3//4)
    }

def get_all_windows(focus_only=False):
    """Get all visible windows or just the focused one"""
    desktop = Desktop(backend="uia")
    
    if focus_only:
        import win32gui
        foreground_hwnd = win32gui.GetForegroundWindow()
        windows = [w for w in desktop.windows() if w.handle == foreground_hwnd and w.is_visible()]
    else:
        windows = [w for w in desktop.windows() if w.is_visible()]
        
    return windows

def element_to_dict(element, region=None, min_size=5, visible_only=False):
    """Convert a UI element to a dictionary with its properties"""
    try:
        # Get element position
        rect = element.rectangle()
        
        # Skip elements outside region if region is specified
        if region:
            left, top, right, bottom = region
            if (rect.right < left or rect.left > right or 
                rect.bottom < top or rect.top > bottom):
                return None
        
        # Skip elements that are too small
        if rect.width() < min_size or rect.height() < min_size:
            return None
        
        # Skip elements that are not visible on screen if visible_only is True
        if visible_only:
            # Check if element is within screen boundaries
            screen_width, screen_height = pyautogui.size()
            if (rect.right < 0 or rect.left > screen_width or 
                rect.bottom < 0 or rect.top > screen_height):
                return None
            
            # Check if element is visible (has non-zero size and not hidden)
            if hasattr(element, 'is_visible') and callable(element.is_visible):
                if not element.is_visible():
                    return None
            
            # Check if element is enabled/interactive if possible
            if hasattr(element, 'is_enabled') and callable(element.is_enabled):
                if not element.is_enabled():
                    return None
            
        # Get element text
        text = ""
        if hasattr(element, 'window_text') and callable(element.window_text):
            text = element.window_text()
        
        # Get control type
        control_type = element.element_info.control_type
        
        # Get class name and automation id if available
        class_name = element.element_info.class_name if hasattr(element.element_info, 'class_name') else ''
        automation_id = element.element_info.automation_id if hasattr(element.element_info, 'automation_id') else ''
        
        # Create basic element info
        element_info = {
            'control_type': control_type,
            'text': text,
            'position': {
                'left': rect.left,
                'top': rect.top,
                'right': rect.right,
                'bottom': rect.bottom,
                'width': rect.width(),
                'height': rect.height()
            },
            'properties': {
                'class_name': class_name,
                'automation_id': automation_id
            },
            'children': []  # Will be populated with child elements
        }
        
        return element_info
    except Exception as e:
        print(f"Error converting element to dict: {str(e)}")
        return None

def build_element_tree(element, depth=0, max_depth=5, region=None, min_size=5, visible_only=False):
    """Build a hierarchical tree of UI elements"""
    if depth > max_depth:
        return None
        
    # Convert element to dictionary
    element_dict = element_to_dict(element, region, min_size, visible_only)
    if not element_dict:
        return None
        
    # Add children recursively
    if hasattr(element, 'children') and callable(element.children):
        try:
            children = element.children()
            for child in children:
                child_dict = build_element_tree(child, depth + 1, max_depth, region, min_size, visible_only)
                if child_dict:
                    element_dict['children'].append(child_dict)
        except Exception as e:
            print(f"Error processing children: {str(e)}")
    
    return element_dict

def analyze_ui_hierarchy(region=None, max_depth=5, focus_only=False, min_size=5, visible_only=False):
    """Analyze UI elements hierarchically"""
    # Get windows to analyze
    windows = get_all_windows(focus_only)
    print(f"Found {len(windows)} windows to analyze")
    
    # Build hierarchy for each window
    ui_hierarchy = []
    for window in windows:
        try:
            window_dict = build_element_tree(window, 0, max_depth, region, min_size, visible_only)
            if window_dict:
                ui_hierarchy.append(window_dict)
        except Exception as e:
            print(f"Error processing window: {str(e)}")
    
    return ui_hierarchy

def draw_element_hierarchy(image, element, draw, highlight_levels=False, current_depth=0, level_colors=None):
    """Recursively draw element hierarchy on image"""
    if not level_colors:
        # Define colors for different hierarchy levels if highlighting levels
        level_colors = [
            "red", "blue", "green", "purple", "orange", 
            "cyan", "magenta", "yellow", "pink", "lime"
        ]
    
    # Get element position
    position = element['position']
    left = position['left']
    top = position['top']
    right = position['right']
    bottom = position['bottom']
    
    # Choose color based on element type or depth level
    if highlight_levels:
        color = level_colors[current_depth % len(level_colors)]
    else:
        # Color by control type
        control_type = element['control_type']
        color_map = {
            "Button": "red",
            "Edit": "blue",
            "Text": "green",
            "Window": "purple",
            "Pane": "orange",
            "CheckBox": "cyan",
            "ComboBox": "magenta",
            "List": "yellow",
            "Menu": "pink",
            "Tab": "lime",
            "MenuItem": "brown"
        }
        color = color_map.get(control_type, "white")
    
    # Draw rectangle
    line_width = max(1, 3 - current_depth // 2)  # Thicker lines for parent elements
    draw.rectangle([(left, top), (right, bottom)], outline=color, width=line_width)
    
    # Draw label (position + type + text)
    text = element['text']
    if len(text) > 20:  # Truncate long text
        text = text[:17] + "..."
        
    label = f"{control_type}"
    if text:
        label += f": {text}"
        
    # Draw text background for readability
    text_x = left + 5
    text_y = max(top - 15, 0)  # Place above if possible
    
    text_width = len(label) * 6  # Approximate width
    draw.rectangle(
        [(text_x - 2, text_y - 2), (text_x + text_width + 4, text_y + 14)],
        fill="black"
    )
    
    # Draw text
    draw.text((text_x, text_y), label, fill=color)
    
    # Draw children
    for child in element['children']:
        draw_element_hierarchy(image, child, draw, highlight_levels, current_depth + 1, level_colors)

def visualize_ui_hierarchy(hierarchy, output_prefix="ui_hierarchy", highlight_levels=False):
    """Create visualization of UI hierarchy"""
    # Take a screenshot
    screenshot = pyautogui.screenshot()
    draw = ImageDraw.Draw(screenshot)
    
    # Draw each top-level window
    for window in hierarchy:
        draw_element_hierarchy(screenshot, window, draw, highlight_levels)
    
    # Save the image
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    image_path = f"{output_prefix}_{timestamp}.png"
    screenshot.save(image_path)
    
    # Return the path
    return image_path

def calculate_nesting_level(element):
    """Calculate maximum nesting level in an element hierarchy"""
    if not element['children']:
        return 0
    
    child_levels = [calculate_nesting_level(child) for child in element['children']]
    return 1 + max(child_levels) if child_levels else 0

def count_elements(element):
    """Count total elements in a hierarchy"""
    count = 1  # Count this element
    for child in element['children']:
        count += count_elements(child)
    return count

def convert_to_xml(hierarchy):
    """Convert UI hierarchy to XML format"""
    root = ET.Element("UIHierarchy")
    
    def add_element_to_xml(parent_xml, element_dict):
        # Create element
        element = ET.SubElement(parent_xml, element_dict['control_type'].replace(' ', '_'))
        
        # Add text and position attributes
        if element_dict['text']:
            element.set('text', element_dict['text'])
            
        pos = element_dict['position']
        element.set('left', str(pos['left']))
        element.set('top', str(pos['top']))
        element.set('right', str(pos['right']))
        element.set('bottom', str(pos['bottom']))
        element.set('width', str(pos['width']))
        element.set('height', str(pos['height']))
        
        # Add other properties
        props = ET.SubElement(element, "Properties")
        for key, value in element_dict['properties'].items():
            if value:  # Only add non-empty properties
                prop = ET.SubElement(props, key.replace(' ', '_'))
                prop.text = str(value)
        
        # Add children
        if element_dict['children']:
            children = ET.SubElement(element, "Children")
            for child in element_dict['children']:
                add_element_to_xml(children, child)
    
    # Add all windows
    for window in hierarchy:
        add_element_to_xml(root, window)
    
    # Convert to pretty-printed XML string
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def process_element_positions(element):
    pos = element['position']
    pos['left'] = int(pos['left'])
    pos['top'] = int(pos['top'])
    pos['right'] = int(pos['right'])
    pos['bottom'] = int(pos['bottom'])
    pos['width'] = int(pos['width'])
    pos['height'] = int(pos['height'])
    
    for child in element['children']:
        process_element_positions(child)

def main():
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Create output prefix
    if not args.output:
        args.output = "ui_hierarchy"
    
    # Parse region if provided
    region = None
    if args.region:
        # Get predefined regions
        predefined_regions = get_predefined_regions()
        
        # Check if region is a predefined name
        if args.region.lower() in predefined_regions:
            region = predefined_regions[args.region.lower()]
            print(f"Using predefined region '{args.region}': {region}")
        elif args.region.lower() == "screen":
            # Use full screen (already defined in predefined_regions, but keeping for compatibility)
            screen_width, screen_height = pyautogui.size()
            region = (0, 0, screen_width, screen_height)
        else:
            try:
                # Parse as left,top,right,bottom
                region = tuple(map(int, args.region.split(',')))
                if len(region) != 4:
                    raise ValueError("Region must be 4 values: left,top,right,bottom")
            except Exception as e:
                print(f"Error parsing region: {str(e)}")
                print(f"Available predefined regions: {', '.join(get_predefined_regions().keys())}")
                return
    
    print("Analyzing UI hierarchy...")
    
    # Analyze UI elements
    ui_hierarchy = analyze_ui_hierarchy(
        region=region,
        max_depth=args.depth, 
        focus_only=args.focus_window,
        min_size=args.min_size,
        visible_only=args.visible_only
    )
    
    # Print stats
    total_windows = len(ui_hierarchy)
    total_elements = sum(count_elements(window) for window in ui_hierarchy)
    max_nesting = max(calculate_nesting_level(window) for window in ui_hierarchy) if ui_hierarchy else 0
    
    print(f"Analysis complete:")
    print(f"- Found {total_windows} top-level windows")
    print(f"- Total of {total_elements} UI elements")
    print(f"- Maximum nesting level: {max_nesting}")
    
    # Create visualization
    print("Creating visualization...")
    image_path = visualize_ui_hierarchy(ui_hierarchy, args.output, args.highlight_levels)
    
    # Timestamp for file naming
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save in requested format(s)
    if args.format in ['json', 'both']:
        json_path = f"{args.output}_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(ui_hierarchy, f, indent=2, ensure_ascii=False)
        print(f"UI hierarchy JSON saved to: {os.path.abspath(json_path)}")
    
    if args.format in ['xml', 'both']:
        xml_path = f"{args.output}_{timestamp}.xml"
        xml_content = convert_to_xml(ui_hierarchy)
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        print(f"UI hierarchy XML saved to: {os.path.abspath(xml_path)}")
    
    print(f"Visualization saved to: {os.path.abspath(image_path)}")
    
    # Try to open the image
    try:
        import subprocess
        if os.name == 'nt':  # Windows
            os.startfile(os.path.abspath(image_path))
        elif os.name == 'posix':  # macOS or Linux
            subprocess.call(('open' if sys.platform == 'darwin' else 'xdg-open', os.path.abspath(image_path)))
    except:
        print("Please open the image manually to view the results")
    
    # Create a script for clicking on elements from the hierarchy
    click_script_path = create_click_script(args.output, json_path if args.format in ['json', 'both'] else None)
    print(f"Click helper script created: {os.path.abspath(click_script_path)}")

def create_click_script(output_prefix, json_path=None):
    """Create a script for clicking on elements from the JSON hierarchy"""
    script_path = f"{output_prefix}_click.py"
    
    # If no JSON path is available (when only XML is exported), use a placeholder
    if not json_path:
        json_path = f"{output_prefix}_YYYYMMDD_HHMMSS.json"
    
    script_content = f'''import json
import sys
import argparse
import pyautogui
import time

def create_parser():
    parser = argparse.ArgumentParser(description='Click on a UI element from the hierarchy')
    parser.add_argument('--json', default='{os.path.basename(json_path)}', help='Path to JSON hierarchy file')
    parser.add_argument('--type', help='Control type to search for (e.g., Button)')
    parser.add_argument('--text', help='Text content to search for')
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
        for i, child in enumerate(element['children']):
            search_element(child, f"{{current_path}}.children.{{i}}")
    
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
            print(f"Error navigating to path {{path}}: {{str(e)}}")
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
    
    print(f"Clicking at ({{x}}, {{y}})")
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
        print(f"Error reading JSON file: {{str(e)}}")
        return
    
    # Find matching elements
    matches = find_elements_by_criteria(hierarchy, args.type, args.text, args.path)
    
    if not matches:
        print("No matching elements found.")
        return
    
    # Display matches
    print(f"Found {{len(matches)}} matching elements:")
    for i, (element, path) in enumerate(matches):
        text = element['text']
        if len(text) > 30:
            text = text[:27] + "..."
        print(f"{{i+1}}. Type: {{element['control_type']}}, Text: {{text}}")
        print(f"   Path: {{path}}")
        print(f"   Position: {{element['position']}}")
    
    # If multiple matches, prompt user to select one
    selected, path = matches[0]  # Default to first match
    if len(matches) > 1:
        choice = input(f"Enter number to select element (1-{{len(matches)}}) or press Enter for first match: ")
        if choice and choice.isdigit() and 1 <= int(choice) <= len(matches):
            selected, path = matches[int(choice)-1]
    
    # Print selection details
    print(f"Selected element:")
    print(f"- Type: {{selected['control_type']}}")
    print(f"- Text: {{selected['text']}}")
    print(f"- Path: {{path}}")
    print(f"- Position: {{selected['position']}}")
    
    # Wait before clicking
    print(f"Waiting {{args.wait}} seconds before clicking...")
    time.sleep(args.wait)
    
    # Click the element
    click_element(selected)

if __name__ == "__main__":
    main()
'''
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    return script_path

if __name__ == "__main__":
    main() 