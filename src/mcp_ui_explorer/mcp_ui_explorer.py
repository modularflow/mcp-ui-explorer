from fastmcp import FastMCP, Image
import io
import os
import json
import pyautogui
from PIL import Image as PILImage
from .hierarchical_ui_explorer import (
    get_predefined_regions,
    analyze_ui_hierarchy,
    visualize_ui_hierarchy
)
from typing import Optional, List, Dict, Any

# Create the MCP server
mcp = FastMCP("UI Explorer")

@mcp.tool()
def explore_ui(
    region: Optional[str] = None,
    depth: int = 5,
    min_size: int = 5,
    focus_window: bool = False,
    visible_only: bool = True
) -> Dict[str, Any]:
    """
    Explore UI elements hierarchically and return the hierarchy data.
    
    Args:
        region: Region to analyze: "screen", "top", "bottom", "left", "right", 
               "top-left", "top-right", "bottom-left", "bottom-right", 
               or custom "left,top,right,bottom" coordinates
        depth: Maximum depth to analyze (default: 5)
        min_size: Minimum element size to include (default: 5)
        focus_window: Only analyze the foreground window (default: False)
        visible_only: Only include elements visible on screen (default: True)
    
    Returns:
        UI hierarchy data
    """
    # Parse region if provided
    region_coords = None
    if region:
        predefined_regions = get_predefined_regions()
        if region.lower() in predefined_regions:
            region_coords = predefined_regions[region.lower()]
        elif region.lower() == "screen":
            screen_width, screen_height = pyautogui.size()
            region_coords = (0, 0, screen_width, screen_height)
        else:
            try:
                region_coords = tuple(map(int, region.split(',')))
                if len(region_coords) != 4:
                    raise ValueError("Region must be 4 values: left,top,right,bottom")
            except Exception as e:
                return {"error": f"Error parsing region: {str(e)}"}
    
    # Analyze UI elements
    ui_hierarchy = analyze_ui_hierarchy(
        region=region_coords,
        max_depth=depth, 
        focus_only=focus_window,
        min_size=min_size,
        visible_only=visible_only
    )
    
    # Calculate stats
    total_windows = len(ui_hierarchy)
    
    # Return the hierarchy and stats
    return {
        "hierarchy": ui_hierarchy,
        "stats": {
            "total_windows": total_windows,
        }
    }

@mcp.tool()
def screenshot_ui(
    region: Optional[str] = None,
    highlight_levels: bool = True,
    output_prefix: str = "ui_hierarchy"
) -> Image:
    """
    Take a screenshot with UI elements highlighted and return it as an image.
    
    Args:
        region: Region to analyze: "screen", "top", "bottom", "left", "right", etc.
        highlight_levels: Use different colors for hierarchy levels (default: True)
        output_prefix: Prefix for output files (default: "ui_hierarchy")
    
    Returns:
        Screenshot with UI elements highlighted
    """
    # Parse region
    region_coords = None
    if region:
        predefined_regions = get_predefined_regions()
        if region.lower() in predefined_regions:
            region_coords = predefined_regions[region.lower()]
        elif region.lower() == "screen":
            screen_width, screen_height = pyautogui.size()
            region_coords = (0, 0, screen_width, screen_height)
        else:
            try:
                region_coords = tuple(map(int, region.split(',')))
                if len(region_coords) != 4:
                    raise ValueError("Region must be 4 values: left,top,right,bottom")
            except Exception as e:
                # Instead of returning a dict, raise an exception
                raise ValueError(f"Error parsing region: {str(e)}")
    
    # Analyze UI elements
    ui_hierarchy = analyze_ui_hierarchy(
        region=region_coords,
        max_depth=5,  # Use default depth 
        focus_only=False,
        min_size=5,
        visible_only=True
    )
    
    # Create visualization
    image_path = visualize_ui_hierarchy(ui_hierarchy, output_prefix, highlight_levels)
    
    # Load the image and return it
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # Clean up the temporary file
    try:
        os.remove(image_path)
    except:
        pass
    
    return Image(data=image_data, format="png")

@mcp.tool()
def click_ui_element(
    control_type: Optional[str] = None,
    text: Optional[str] = None, 
    element_path: Optional[str] = None,
    wait_time: float = 2.0,
    hierarchy_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Click on a UI element based on search criteria.
    
    Args:
        control_type: Control type to search for (e.g., "Button")
        text: Text content to search for
        element_path: Path to element (e.g., "0.children.3.children.2")
        wait_time: Seconds to wait before clicking (default: 2)
        hierarchy_data: Hierarchy data from explore_ui (if not provided, will run explore_ui)
    
    Returns:
        Result of the click operation
    """
    if not control_type and not text and not element_path:
        return {"error": "You must specify at least one search criteria (control_type, text, or element_path)"}
    
    # Get hierarchy data if not provided
    hierarchy = None
    if hierarchy_data and "hierarchy" in hierarchy_data:
        hierarchy = hierarchy_data["hierarchy"]
    else:
        result = explore_ui(visible_only=True)
        if "hierarchy" in result:
            hierarchy = result["hierarchy"]
        else:
            return {"error": "Failed to get UI hierarchy"}
    
    # Find matching elements
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
            search_element(child, f"{current_path}.children.{i}")
    
    # If path is provided, navigate directly to that element
    if element_path:
        try:
            element = hierarchy
            for part in element_path.split('.'):
                if part.isdigit():
                    element = element[int(part)]
                else:
                    element = element[part]
            matches.append((element, element_path))
        except Exception as e:
            return {"error": f"Error navigating to path {element_path}: {str(e)}"}
    else:
        # Otherwise search the whole hierarchy
        for i, window in enumerate(hierarchy):
            search_element(window, str(i))
    
    if not matches:
        return {"error": "No matching elements found"}
    
    # Use the first match
    selected, path = matches[0]
    
    # Prepare element info for the response
    element_info = {
        "type": selected['control_type'],
        "text": selected['text'],
        "path": path,
        "position": selected['position']
    }
    
    # Wait before clicking
    import time
    time.sleep(wait_time)
    
    # Click the element
    position = selected['position']
    x = position['left'] + position['width'] // 2
    y = position['top'] + position['height'] // 2
    
    try:
        pyautogui.click(x, y)
        return {
            "success": True,
            "message": f"Clicked element at ({x}, {y})",
            "element": element_info,
            "all_matches": len(matches)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to click: {str(e)}",
            "element": element_info,
            "all_matches": len(matches)
        }

@mcp.resource("ui://regions")
def get_available_regions() -> Dict[str, Any]:
    """Get the list of predefined screen regions that can be used for UI exploration."""
    regions = get_predefined_regions()
    result = {}
    
    for name, coords in regions.items():
        result[name] = {
            "coordinates": coords,
            "description": f"Region covering the {name} of the screen"
        }
    
    return result

@mcp.prompt()
def ui_exploration_guide() -> str:
    """A guide for exploring and interacting with UI elements."""
    return """
# UI Exploration Guide

You can use this tool to explore and interact with UI elements on the screen. Here's how:

1. **Explore the UI structure** with the `explore_ui` tool:
   - This returns the complete hierarchy of UI elements
   - You can specify regions like "screen", "top-left", etc.
   - Use parameters like `depth` and `focus_window` to refine the search

2. **Visualize the UI** with the `screenshot_ui` tool:
   - This returns an image showing all detected UI elements
   - Elements are highlighted with their boundaries
   - Different colors can represent hierarchy levels

3. **Click on UI elements** with the `click_ui_element` tool:
   - Search by control type (e.g., "Button")
   - Search by text content
   - Or use a specific path from the hierarchy

Example workflow:
1. First explore the UI to understand what's available
2. Take a screenshot to visualize the elements
3. Click on a specific element based on what you found
    """

if __name__ == "__main__":
    mcp.run() 