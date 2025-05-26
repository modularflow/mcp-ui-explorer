import os
import sys
import logging
import json
import base64
import io
import re
from openai import OpenAI
from mcp import Tool
import pyautogui
from PIL import Image as PILImage
from .hierarchical_ui_explorer import (
    get_predefined_regions,
    analyze_ui_hierarchy,
    visualize_ui_hierarchy
)
from typing import Optional, List, Dict, Any, Union, Literal
from enum import Enum
from mcp.server import InitializationOptions
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types
from pydantic import BaseModel, Field

# reconfigure UnicodeEncodeError prone default (i.e. windows-1252) to utf-8
if sys.platform == "win32" and os.environ.get('PYTHONIOENCODING') is None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logger = logging.getLogger('mcp_ui_explorer')
logger.info("Starting UI Explorer")

PROMPT_TEMPLATE = """
# UI Exploration Guide

🧠 **MEMORY-ENHANCED WORKFLOW: Learn & Improve Over Time**

This system now includes memory capabilities to learn from successful workflows and avoid repeating failures.

## 🔍 **START EVERY CONVERSATION: Check Memory First**

Before starting any UI task, search memory for similar workflows:

```
# Search for relevant past workflows
search_memory("login workflow", "button clicking", "form filling", etc.)

# Look for specific UI elements or applications  
search_memory("Chrome browser", "settings dialog", "file menu", etc.)

# Check for troubleshooting patterns
search_memory("click failed", "verification failed", "timeout issues", etc.)
```

## 🎯 **CORE WORKFLOW: Visual AI + Memory Learning**

The most effective approach combines visual AI with memory learning:

    1. **FIRST: Take a screenshot** with the `screenshot_ui` tool:
    - Captures the current state of the UI with element boundaries highlighted
    - By default, focuses on the foreground window only (focus_only=true)  
    - Shows only meaningful elements (min_size=20, max_depth=4)
    - Returns the screenshot file path for AI analysis
    
    Example:
    ```
    screenshot_ui(region="screen")  # Default: clean, focused screenshot
    ```

    2. **SECOND: Use AI vision to find elements** with the `ui_tars_analyze` tool:
    - Use the UI-TARS model to identify specific UI elements in the screenshot
    - Describe what you're looking for in natural language
    - Returns both normalized (0-1) and absolute pixel coordinates
    - Most reliable method for finding UI elements
    
    Example:
    ```
    ui_tars_analyze(image_path="ui_hierarchy_20250524_143022.png", query="login button")
    ui_tars_analyze(image_path="screenshot.png", query="submit button in the form")
    ```

    3. **THIRD: Click on found elements** with the `click_ui_element` tool:
    - Use either absolute or normalized coordinates
    - UI-TARS provides both formats - use whichever is convenient
    - Specify wait_time if needed (default: 2.0 seconds)
    
    Example:
    ```
    click_ui_element(x=500, y=300)  # Absolute coordinates
    click_ui_element(x=0.5, y=0.3, normalized=true)  # Normalized coordinates (0-1)
    ```

    4. **Interact with text and keyboard** as needed:
    - Type text: `keyboard_input(text="Hello world", press_enter=true)`
    - Press keys: `press_key(key="tab")`  
    - Shortcuts: `hot_key(keys=["ctrl", "c"])`

    5. **VERIFY the action worked** with the `verify_ui_action` tool:
    - Check that your action had the expected result
    - Uses AI vision to confirm the UI state changed as expected
    - Essential for reliable automation workflows
    
    Example:
    ```
    verify_ui_action(
        action_description="Clicked the login button", 
        expected_result="Login dialog should have opened",
        verification_query="login dialog box with username and password fields"
    )
    ```

    6. **SAVE MEMORY after each verified action**:
    - Document what was done and whether it worked
    - Build knowledge for future similar tasks
    - Create workflow chains for complex sequences
    
    Example:
    ```
    # Create memory entity for the action
    mcp_memory_create_entities([{
        "name": "Login_Button_Click_Action_2024",
        "entityType": "UI_Action",
        "observations": [
            "Action: Clicked login button at normalized coords (0.5, 0.3)",
            "Result: SUCCESS - Login dialog opened as expected",
            "App: Chrome browser on login page",
            "Verification: Found 'username and password fields' in dialog",
            "Timing: 2.0 seconds wait time worked well",
            "Screenshot: verification_20241201_143022.png"
        ]
    }])
    
    # Link actions together in workflows
    mcp_memory_create_relations([{
        "from": "Website_Navigation_Workflow",
        "to": "Login_Button_Click_Action_2024", 
        "relationType": "INCLUDES_STEP"
    }])
    ```

📋 **BACKUP METHODS** (use only when visual approach doesn't work):

    5. **Text-based UI exploration** with the `explore_ui` tool:
    - Returns structured data about UI elements
    - Filter by control_type and text content
    - Returns absolute pixel coordinates in position field
    
    Example:
    ```
    explore_ui(region="screen", control_type="Button", text="submit")
    ```

    6. **Find elements near cursor** with the `find_elements_near_cursor` tool:
    - Finds UI elements closest to current cursor position
    - Returns absolute pixel coordinates
    
    Example:
    ```
    find_elements_near_cursor(max_distance=100, control_type="Button")
    ```

⚙️ **COORDINATE FORMATS**:
- UI-TARS returns: `{"normalized": {"x": 0.5, "y": 0.3}, "absolute": {"x": 960, "y": 432}}`
- Other tools return: `{"coordinates": {"absolute": {...}, "normalized": {...}}}`
- Click tool accepts: Both `{"x": 960, "y": 432}` and `{"x": 0.5, "y": 0.3, "normalized": true}`

🎯 **MEMORY-ENHANCED WORKFLOW**:
    0. **Search memory first**: `mcp_memory_search_nodes("similar task keywords")`
    1. Take a screenshot: `screenshot_ui(region="screen")`  
    2. Find element with AI: `ui_tars_analyze(image_path="screenshot.png", query="what you want")`
    3. Click on element: `click_ui_element(x=absolute_x, y=absolute_y)`
    4. Interact as needed: `keyboard_input(text="...")` or `press_key(...)`
    5. Verify it worked: `verify_ui_action(action_description="...", expected_result="...", verification_query="...")`
    6. **Save memory**: `mcp_memory_create_entities([action_memory])` + `mcp_memory_create_relations([workflow_link])`

## 🧠 **MEMORY MANAGEMENT PATTERNS**

### **Entity Types to Create:**
- `UI_Action`: Individual clicks, typing, key presses with results
- `UI_Workflow`: Complete sequences of actions (login, file-open, etc.)  
- `UI_Element`: Specific buttons, fields, menus with locations
- `App_Context`: Application-specific behavior patterns
- `Troubleshooting`: Failed actions with solutions

### **Memory Structure Example:**
```
# Workflow entity
"Website_Login_Workflow_Chrome" (UI_Workflow)
  ├─ INCLUDES_STEP → "Navigate_To_Login_Page" (UI_Action)
  ├─ INCLUDES_STEP → "Click_Login_Button" (UI_Action) 
  ├─ INCLUDES_STEP → "Enter_Username" (UI_Action)
  └─ INCLUDES_STEP → "Enter_Password" (UI_Action)

# Action entity with detailed observations
"Click_Login_Button" (UI_Action)
  - "Coordinates: normalized (0.5, 0.3) = absolute (960, 432)"
  - "Verification: SUCCESS - Login dialog appeared"
  - "Timing: 2.0s wait worked well"
  - "Context: Chrome browser, login page loaded"
  - "Alternative: Also found at (0.48, 0.31) on different screen size"
```

### **Search Strategies:**
- **By task**: `mcp_memory_search_nodes("login workflow")`
- **By app**: `mcp_memory_search_nodes("Chrome browser actions")`
- **By element**: `mcp_memory_search_nodes("submit button clicking")`
- **By failure**: `mcp_memory_search_nodes("verification failed solutions")`

### **Learning from Failures:**
```
# Document failures for future reference
mcp_memory_create_entities([{
    "name": "Login_Button_Click_Failed_2024",
    "entityType": "Troubleshooting", 
    "observations": [
        "FAILED: Click at (0.5, 0.3) missed login button",
        "Cause: Button moved due to page resize",
        "Solution: Used UI-TARS to find actual position (0.52, 0.28)",
        "Lesson: Always use UI-TARS for dynamic layouts",
        "App: Chrome browser with responsive design"
    ]
}])
```

 💡 **PRO TIPS**:
- **Always search memory first** - learn from past successes and failures
- **Document everything** - coordinates, timing, context, results
- **Link actions into workflows** - build reusable automation sequences  
- **Save failures too** - they're valuable troubleshooting knowledge
- Be specific in UI-TARS queries: "red submit button" instead of just "button"  
- Use either absolute or normalized coordinates for clicking (both supported)
- Normalized coordinates (0-1) work across different screen resolutions
- **Always verify actions worked** - don't assume success without checking
- Use backup text methods only when visual approach fails

## 📋 **COMPLETE EXAMPLE: Memory-Enhanced Login Workflow**

### **Step 1: Check existing knowledge**
```
# Search for similar workflows
search_result = mcp_memory_search_nodes("website login Chrome browser")

# If found, review past approaches and adapt
# If not found, proceed with discovery and documentation
```

### **Step 2: Execute with memory capture**
```
# 1. Screenshot and find login button
screenshot_ui(region="screen")
login_coords = ui_tars_analyze(image_path="screenshot.png", query="login button")

# 2. Click login button  
click_result = click_ui_element(x=login_coords['normalized']['x'], y=login_coords['normalized']['y'], normalized=true)

# 3. Verify it worked
verification = verify_ui_action(
    action_description="Clicked main login button",
    expected_result="Login form should appear", 
    verification_query="username and password input fields"
)

# 4. Save the action to memory
mcp_memory_create_entities([{
    "name": f"Login_Button_Click_{timestamp}",
    "entityType": "UI_Action",
    "observations": [
        f"Action: Clicked login button at normalized ({login_coords['normalized']['x']:.3f}, {login_coords['normalized']['y']:.3f})",
        f"Result: {'SUCCESS' if verification['verification_passed'] else 'FAILED'} - {verification['expected_result']}",
        f"App: Chrome browser on website login page", 
        f"Verification query: {verification['verification_query']}",
        f"Wait time: {click_result['wait_time']}s worked well",
        f"Screenshot: {verification['verification_screenshot']}"
    ]
}])

# 5. Link to workflow (create workflow entity if needed)
mcp_memory_create_relations([{
    "from": "Website_Login_Workflow_Master",
    "to": f"Login_Button_Click_{timestamp}",
    "relationType": "INCLUDES_STEP"
}])
```

### **Step 3: Build workflow knowledge**
```
# If this is part of a larger workflow, document the sequence
mcp_memory_create_entities([{
    "name": "Website_Login_Workflow_Master", 
    "entityType": "UI_Workflow",
    "observations": [
        "Complete login workflow for web applications",
        "Step 1: Navigate to login page",
        "Step 2: Click login button (triggers login form)",
        "Step 3: Enter username credentials", 
        "Step 4: Enter password credentials",
        "Step 5: Submit login form",
        "Success rate: High with UI-TARS verification",
        "Common issues: Dynamic layouts, slow page loads"
    ]
}])
```

### **Benefits of Memory Integration:**
- 🧠 **Learning**: Each action builds knowledge for future tasks
- 🔄 **Reusability**: Successful workflows can be reused and adapted  
- 🐛 **Debugging**: Failed actions documented with solutions
- ⚡ **Speed**: Skip discovery phase for known workflows
- 🎯 **Accuracy**: Learn optimal coordinates and timing
- 📊 **Analytics**: Track success rates and common failure patterns
        """

# Define enums for input validation
class RegionType(str, Enum):
    SCREEN = "screen"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    # Custom region will be handled separately

class ControlType(str, Enum):
    BUTTON = "Button"
    TEXT = "Text"
    EDIT = "Edit"
    CHECKBOX = "CheckBox"
    RADIOBUTTON = "RadioButton"
    COMBOBOX = "ComboBox"
    LIST = "List"
    LISTITEM = "ListItem"
    MENU = "Menu"
    MENUITEM = "MenuItem"
    TREE = "Tree"
    TREEITEM = "TreeItem"
    TOOLBAR = "ToolBar"
    TAB = "Tab"
    TABITEM = "TabItem"
    WINDOW = "Window"
    DIALOG = "Dialog"
    PANE = "Pane"
    GROUP = "Group"
    DOCUMENT = "Document"
    STATUSBAR = "StatusBar"
    IMAGE = "Image"
    HYPERLINK = "Hyperlink"

# Pydantic models for input validation
class ExploreUIInput(BaseModel):
    region: Optional[Union[RegionType, str]] = Field(
        default=None, 
        description="Region to analyze: predefined regions or custom 'left,top,right,bottom' coordinates"
    )
    depth: int = Field(default=8, description="Maximum depth to analyze")
    min_size: int = Field(default=5, description="Minimum element size to include")
    focus_window: bool = Field(default=False, description="Only analyze the foreground window")
    visible_only: bool = Field(default=True, description="Only include elements visible on screen")
    control_type: ControlType = Field(default=ControlType.BUTTON, description="Only include elements of this control type (default: ALL)")
    text: Optional[str] = Field(default=None, description="Only include elements containing this text (case-insensitive, partial match)")

class FindNearCursorInput(BaseModel):
    max_distance: int = Field(default=100, description="Maximum distance from cursor to include elements")
    control_type: Optional[ControlType] = Field(default=None, description="Only include elements of this control type")
    limit: int = Field(default=5, description="Maximum number of elements to return")

class ScreenshotUIInput(BaseModel):
    region: Optional[Union[RegionType, str]] = Field(
        default=None, 
        description="Region to analyze: predefined regions or custom 'left,top,right,bottom' coordinates"
    )
    highlight_levels: bool = Field(default=True, description="Use different colors for hierarchy levels")
    output_prefix: str = Field(default="ui_hierarchy", description="Prefix for output files")
    min_size: int = Field(default=20, description="Minimum element size to include (default: 20)")
    max_depth: int = Field(default=4, description="Maximum depth to analyze (default: 4)")
    focus_only: bool = Field(default=True, description="Only analyze the foreground window")

class ClickUIElementInput(BaseModel):
    x: float = Field(description="X coordinate to click (absolute pixels or normalized 0-1)")
    y: float = Field(description="Y coordinate to click (absolute pixels or normalized 0-1)")
    wait_time: float = Field(default=2.0, description="Seconds to wait before clicking")
    normalized: bool = Field(default=False, description="Whether coordinates are normalized (0-1) or absolute pixels")

class KeyboardInputInput(BaseModel):
    text: str = Field(description="Text to type")
    delay: float = Field(default=0.1, description="Delay before starting to type in seconds")
    interval: float = Field(default=0.0, description="Interval between characters in seconds")
    press_enter: bool = Field(default=False, description="Whether to press Enter after typing")

class PressKeyInput(BaseModel):
    key: str = Field(description="Key to press (e.g., 'enter', 'tab', 'esc', 'space', 'backspace', 'delete', etc.)")
    delay: float = Field(default=0.1, description="Delay before pressing key in seconds")
    presses: int = Field(default=1, description="Number of times to press the key")
    interval: float = Field(default=0.0, description="Interval between keypresses in seconds")

class HotKeyInput(BaseModel):
    keys: List[str] = Field(description="List of keys to press together (e.g., ['ctrl', 'c'] for Ctrl+C)")
    delay: float = Field(default=0.1, description="Delay before pressing keys in seconds")

class UITarsInput(BaseModel):
    image_path: str = Field(description="Path to the screenshot image to analyze")
    query: str = Field(description="Description of what to find on the screen (e.g., 'the login button', 'the search box')")
    api_url: str = Field(default="http://127.0.0.1:1234/v1", description="Base URL for the UI-TARS API")
    model_name: str = Field(default="ui-tars-7b-dpo", description="Name of the UI-TARS model to use")

class UIVerificationInput(BaseModel):
    action_description: str = Field(description="Description of the action that was performed")
    expected_result: str = Field(description="What should have happened (e.g., 'window should open', 'text should appear')")
    verification_query: str = Field(description="What to look for in the screenshot to verify success")
    timeout: float = Field(default=3.0, description="How long to wait for the change to occur (seconds)")
    comparison_image: Optional[str] = Field(default=None, description="Optional: path to before image for comparison")

class UIExplorer:
    def __init__(self):
        self.regions: Dict[str, Any] = {}

    async def _get_cursor_position(self) -> Dict[str, Any]:
        """
        Get the current position of the mouse cursor.
        
        Returns:
            Dictionary with current cursor coordinates in both absolute and normalized formats
        """
        try:
            x, y = pyautogui.position()
            screen_width, screen_height = pyautogui.size()
            
            return {
                "success": True,
                "position": {
                    "absolute": {"x": x, "y": y},
                    "normalized": {"x": x / screen_width, "y": y / screen_height}
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get cursor position: {str(e)}"
            }

    async def _explore_ui(
        self,
        region: Optional[Union[RegionType, str]] = None,
        depth: int = 8,
        min_size: int = 5,
        focus_window: bool = False,
        visible_only: bool = True,
        control_type: ControlType = ControlType.BUTTON,
        text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explore UI elements hierarchically and return the hierarchy data.
        
        Args:
            region: Region to analyze: predefined regions or custom 'left,top,right,bottom' coordinates
            depth: Maximum depth to analyze (default: 8)
            min_size: Minimum element size to include (default: 5)
            focus_window: Only analyze the foreground window (default: False)
            visible_only: Only include elements visible on screen (default: True)
            control_type: Only include elements of this control type (default: Button)
            text: Only include elements containing this text (case-insensitive, partial match)
        
        Returns:
            UI hierarchy data
        """
        # Parse region if provided
        region_coords = None
        if region:
            predefined_regions = get_predefined_regions()
            if isinstance(region, RegionType):
                if region == RegionType.SCREEN:
                    screen_width, screen_height = pyautogui.size()
                    region_coords = (0, 0, screen_width, screen_height)
                elif region.value in predefined_regions:
                    region_coords = predefined_regions[region.value]
                else:
                    return {"error": f"Unknown region: {region.value}"}
            elif isinstance(region, str):
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
        
        # Filter by control type and text
        if control_type or text:
            flat_matches = []
            
            def collect_matches(element, parent_path=""):
                # Check control type match
                control_type_match = True
                if control_type:
                    control_type_match = element['control_type'] == control_type.value
                
                # Check text match
                text_match = True
                if text:
                    text_match = text.lower() in element['text'].lower()
                
                current_path = parent_path
                if current_path:
                    current_path += ".children"
                
                # If this element matches our criteria, add it to flat matches
                if control_type_match and text_match:
                    # Create a copy without children for flat listing
                    element_copy = element.copy()
                    element_copy['children'] = []  # Empty children list
                    flat_matches.append(element_copy)
                
                # Always process children to find all matches
                if 'children' in element:
                    for i, child in enumerate(element['children']):
                        child_path = f"{current_path}.{i}" if current_path else str(i)
                        collect_matches(child, child_path)
            
            # Process all elements to collect matches
            for i, element in enumerate(ui_hierarchy):
                collect_matches(element, str(i))
            
            # Create a new hierarchy with just these elements at the top level
            filtered_hierarchy = flat_matches
        else:
            filtered_hierarchy = ui_hierarchy
        
        # Calculate stats
        total_matches = len(filtered_hierarchy)
        
        # Add unique IDs to each element
        element_id = 0
        
        def add_ids(element):
            nonlocal element_id
            element['id'] = element_id
            element_id += 1
            if 'children' in element:
                for child in element['children']:
                    add_ids(child)
        
        # Process all elements to add IDs
        for element in filtered_hierarchy:
            add_ids(element)
        
        # Clean up elements to remove extra fields and add normalized coordinates
        screen_width, screen_height = pyautogui.size()
        simplified_hierarchy = []
        for element in filtered_hierarchy:
            # Convert position to both absolute and normalized coordinates
            pos = element['position']
            if isinstance(pos, dict) and all(k in pos for k in ['left', 'top', 'right', 'bottom']):
                left, top, right, bottom = pos['left'], pos['top'], pos['right'], pos['bottom']
                center_x = (left + right) / 2
                center_y = (top + bottom) / 2
                
                coordinates = {
                    "absolute": {
                        "left": int(left), "top": int(top), 
                        "right": int(right), "bottom": int(bottom),
                        "center_x": int(center_x), "center_y": int(center_y)
                    },
                    "normalized": {
                        "left": left / screen_width, "top": top / screen_height,
                        "right": right / screen_width, "bottom": bottom / screen_height,
                        "center_x": center_x / screen_width, "center_y": center_y / screen_height
                    }
                }
            else:
                coordinates = {"absolute": pos, "normalized": None}
            
            simplified = {
                "control_type": element['control_type'],
                "text": element['text'],
                "position": pos,  # Keep original for backward compatibility
                "coordinates": coordinates,  # New unified format
                "id": element['id'],
                "properties": element['properties']['automation_id']
            }
            simplified_hierarchy.append(simplified)
        
        # Return the hierarchy and stats
        return {
            "hierarchy": simplified_hierarchy,
            "stats": {
                "total_matches": total_matches,
                "control_type": control_type.value if control_type else "all",
                "text_filter": text if text else None
            },
            "cursor_position": (await self._get_cursor_position())["position"]
        }

    async def _screenshot_ui(
        self,
        region: Optional[Union[RegionType, str]] = None,
        highlight_levels: bool = True,
        output_prefix: str = "ui_hierarchy",
        min_size: int = 20,
        max_depth: int = 4,
        focus_only: bool = True
    ) -> tuple[bytes, str, Dict[str, Any]]:
        """
        Take a screenshot with UI elements highlighted and return it as an image.
        
        Args:
            region: Region to analyze: predefined regions or custom 'left,top,right,bottom' coordinates
            highlight_levels: Use different colors for hierarchy levels (default: True)
            output_prefix: Prefix for output files (default: "ui_hierarchy")
            min_size: Minimum element size to include (default: 20)
            max_depth: Maximum depth to analyze (default: 4)
            focus_only: Only analyze the foreground window (default: True)
        
        Returns:
            Tuple of (image_data, image_path, cursor_position)
        """
        # Parse region
        region_coords = None
        if region:
            predefined_regions = get_predefined_regions()
            if isinstance(region, RegionType):
                if region == RegionType.SCREEN:
                    screen_width, screen_height = pyautogui.size()
                    region_coords = (0, 0, screen_width, screen_height)
                elif region.value in predefined_regions:
                    region_coords = predefined_regions[region.value]
                else:
                    raise ValueError(f"Unknown region: {region.value}")
            elif isinstance(region, str):
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
        
        # Analyze UI elements - more selective by default
        ui_hierarchy = analyze_ui_hierarchy(
            region=region_coords,
            max_depth=max_depth,
            focus_only=focus_only,
            min_size=min_size,
            visible_only=True
        )   
        
        # Create visualization
        image_path = visualize_ui_hierarchy(ui_hierarchy, output_prefix, highlight_levels)
        
        # Load the image and return it
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Do not clean up the file so the user can access it
        # try:
        #     os.remove(image_path)
        # except:
        #     pass
        
        # Return both the image data and path
        return (image_data, image_path, await self._get_cursor_position())

    async def _click_ui_element(
        self,
        x: float,
        y: float,
        wait_time: float,
        normalized: bool = False
    ) -> Dict[str, Any]:
        """
        Click at specific coordinates.
        
        Args:
            x: X coordinate to click (absolute pixels or normalized 0-1)
            y: Y coordinate to click (absolute pixels or normalized 0-1)
            wait_time: Seconds to wait before clicking (default: 2)
            normalized: Whether coordinates are normalized (0-1) or absolute pixels
        
        Returns:
            Result of the click operation
        """
        # Convert normalized coordinates to absolute if needed
        if normalized:
            screen_width, screen_height = pyautogui.size()
            abs_x = int(x * screen_width)
            abs_y = int(y * screen_height)
            coord_type = "normalized"
            input_coords = f"({x:.3f}, {y:.3f})"
        else:
            abs_x = int(x)
            abs_y = int(y)
            coord_type = "absolute"
            input_coords = f"({x}, {y})"
        
        # Wait before clicking
        import time
        time.sleep(wait_time)
        
        try:
            pyautogui.click(abs_x, abs_y)
            return {
                "success": True,
                "message": f"Clicked at {coord_type} coordinates {input_coords} -> absolute ({abs_x}, {abs_y})",
                "coordinates": {
                    "input": {"x": x, "y": y, "type": coord_type},
                    "absolute": {"x": abs_x, "y": abs_y},
                    "normalized": {"x": abs_x / pyautogui.size()[0], "y": abs_y / pyautogui.size()[1]}
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to click at {coord_type} coordinates {input_coords}: {str(e)}"
            }

    async def _keyboard_input(
        self,
        text: str,
        delay: float = 0.1,
        interval: float = 0.0,
        press_enter: bool = False
    ) -> Dict[str, Any]:
        """
        Send keyboard input to the active window.
        
        Args:
            text: Text to type
            delay: Delay before starting to type in seconds (default: 0.1)
            interval: Interval between characters in seconds (default: 0.0)
            press_enter: Whether to press Enter after typing (default: False)
        
        Returns:
            Result of the keyboard input operation
        """
        # Wait before typing
        import time
        time.sleep(delay)
        
        try:
            # Type the text
            pyautogui.write(text, interval=interval)
            
            # Press Enter if requested
            if press_enter:
                pyautogui.press('enter')
                
            return {
                "success": True,
                "message": f"Typed text: '{text}'" + (" and pressed Enter" if press_enter else "")
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to type text: {str(e)}"
            }
        
    async def _press_key(
        self,
        key: str,
        delay: float = 0.1,
        presses: int = 1,
        interval: float = 0.0
    ) -> Dict[str, Any]:
        """
        Press a specific keyboard key.
        
        Args:
            key: Key to press (e.g., 'enter', 'tab', 'esc', etc.)
            delay: Delay before pressing key in seconds (default: 0.1)
            presses: Number of times to press the key (default: 1)
            interval: Interval between keypresses in seconds (default: 0.0)
        
        Returns:
            Result of the key press operation
        """
        # Wait before pressing
        import time
        time.sleep(delay)
        
        try:
            # Press the key the specified number of times
            pyautogui.press(key, presses=presses, interval=interval)
            
            return {
                "success": True,
                "message": f"Pressed key '{key}' {presses} time(s)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to press key: {str(e)}"
            }

    async def _hot_key(
        self,
        keys: List[str],
        delay: float = 0.1
    ) -> Dict[str, Any]:
        """
        Press a keyboard shortcut (multiple keys together).
        
        Args:
            keys: List of keys to press together (e.g., ['ctrl', 'c'] for Ctrl+C)
            delay: Delay before pressing keys in seconds (default: 0.1)
        
        Returns:
            Result of the hotkey operation
        """
        # Wait before pressing
        import time
        time.sleep(delay)
        
        try:
            # Press the keys together
            pyautogui.hotkey(*keys)
            
            # Format the key combination for the message
            key_combo = "+".join(keys)
            
            return {
                "success": True,
                "message": f"Pressed keyboard shortcut: {key_combo}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to press hotkey: {str(e)}"
            }

    async def _find_elements_near_cursor(
        self,
        max_distance: int = 100,
        control_type: Optional[ControlType] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Find UI elements closest to the current cursor position.
        
        Args:
            max_distance: Maximum distance from cursor to include elements (default: 100)
            control_type: Only include elements of this control type (default: None)
            limit: Maximum number of elements to return (default: 5)
        
        Returns:
            UI elements closest to the cursor position
        """
        # Get current cursor position
        cursor_pos = await self._get_cursor_position()
        if not cursor_pos["success"]:
            return cursor_pos
            
        cursor_x, cursor_y = cursor_pos["position"]["absolute"]["x"], cursor_pos["position"]["absolute"]["y"]
        
        # Get all UI elements
        screen_width, screen_height = pyautogui.size()
        ui_hierarchy = analyze_ui_hierarchy(
            region=(0, 0, screen_width, screen_height),
            max_depth=8,
            focus_only=False,
            min_size=5,
            visible_only=True
        )
        
        # Flatten hierarchy and calculate distances
        elements_with_distance = []
        
        def process_element(element):
            # Skip elements without position
            if 'position' not in element:
                return
                
            # Apply control type filter if specified
            if control_type and element['control_type'] != control_type.value:
                return
                
            # Calculate center point of element
            pos = element['position']
            if isinstance(pos, dict) and all(k in pos for k in ['left', 'top', 'right', 'bottom']):
                element_center_x = (pos['left'] + pos['right']) / 2
                element_center_y = (pos['top'] + pos['bottom']) / 2
            else:
                # Fallback for unexpected format
                return
            
            # Calculate Euclidean distance
            distance = ((element_center_x - cursor_x) ** 2 + (element_center_y - cursor_y) ** 2) ** 0.5
            
            # Add to list if within max_distance
            if distance <= max_distance:
                # Add normalized coordinates for consistency
                screen_width, screen_height = pyautogui.size()
                pos = element['position']
                
                if isinstance(pos, dict) and all(k in pos for k in ['left', 'top', 'right', 'bottom']):
                    left, top, right, bottom = pos['left'], pos['top'], pos['right'], pos['bottom']
                    center_x = (left + right) / 2
                    center_y = (top + bottom) / 2
                    
                    coordinates = {
                        "absolute": {
                            "left": int(left), "top": int(top), 
                            "right": int(right), "bottom": int(bottom),
                            "center_x": int(center_x), "center_y": int(center_y)
                        },
                        "normalized": {
                            "left": left / screen_width, "top": top / screen_height,
                            "right": right / screen_width, "bottom": bottom / screen_height,
                            "center_x": center_x / screen_width, "center_y": center_y / screen_height
                        }
                    }
                else:
                    coordinates = {"absolute": pos, "normalized": None}
                
                element_copy = {
                    "control_type": element['control_type'],
                    "text": element['text'],
                    "position": pos,  # Keep original for backward compatibility
                    "coordinates": coordinates,  # New unified format
                    "distance": round(distance, 2),
                    "properties": element['properties']['automation_id'] if 'properties' in element and 'automation_id' in element['properties'] else ""
                }
                elements_with_distance.append(element_copy)
            
            # Process children
            if 'children' in element:
                for child in element['children']:
                    process_element(child)
        
        # Process all root elements
        for element in ui_hierarchy:
            process_element(element)
            
        # Sort by distance and limit results
        elements_with_distance.sort(key=lambda x: x['distance'])
        closest_elements = elements_with_distance[:limit]
        
        return {
            "success": True,
            "cursor_position": cursor_pos["position"],
            "elements": closest_elements,
            "total_found": len(elements_with_distance),
            "showing": min(len(elements_with_distance), limit)
        }

    async def _ui_tars_analyze(
        self,
        image_path: str,
        query: str,
        api_url: str = "http://127.0.0.1:1234/v1",
        model_name: str = "ui-tars-7b-dpo"
    ) -> Dict[str, Any]:
        """
        Use UI-TARS model to identify coordinates of UI elements on screen.
        
        Args:
            image_path: Path to the screenshot image to analyze
            query: Description of what to find on the screen
            api_url: Base URL for the UI-TARS API (default: http://127.0.0.1:1234/v1)
            model_name: Name of the UI-TARS model to use (default: ui-tars-7b-dpo)
        
        Returns:
            Dictionary containing the analysis result with normalized coordinates
        """
        try:
            # Check if image file exists
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": f"Image file not found: {image_path}"
                }
            
            # Load and encode the image
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                
            # Convert to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Get screen dimensions for coordinate conversion
            screen_width, screen_height = pyautogui.size()
            
            # Initialize OpenAI client
            client = OpenAI(
                base_url=api_url,
                api_key="dummy"  # UI-TARS typically doesn't require a real API key
            )
            
            # Prepare the prompt for UI-TARS
            system_prompt = """You are UI-TARS, a specialized model for identifying UI elements in screenshots. 
When asked to find an element, respond with the coordinates of the center of the target element.
You can use any of these formats:
- <click>x,y</click> for normalized coordinates (0-1)
- <|box_start|>(x,y)<|box_end|> for absolute pixel coordinates
- (x,y) for coordinates
If you cannot find the element, respond with "Element not found"."""
            
            user_prompt = f"Find the {query} in this screenshot and provide its normalized coordinates."
            
            # Make the API call
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": user_prompt},
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
            
            # Parse the response
            response_text = response.choices[0].message.content.strip()
            
            # Extract coordinates from response - handle multiple formats
            # Format 1: <click>x,y</click>
            coordinate_pattern1 = r'<click>([0-9.]+),([0-9.]+)</click>'
            # Format 2: <|box_start|>(x,y)<|box_end|>
            coordinate_pattern2 = r'<\|box_start\|>\(([0-9.]+),([0-9.]+)\)<\|box_end\|>'
            # Format 3: Just coordinates in parentheses (x,y)
            coordinate_pattern3 = r'\(([0-9.]+),([0-9.]+)\)'
            
            match = re.search(coordinate_pattern1, response_text)
            if not match:
                match = re.search(coordinate_pattern2, response_text)
            if not match:
                match = re.search(coordinate_pattern3, response_text)
            
            if match:
                # Parse coordinates
                x, y = float(match.group(1)), float(match.group(2))
                
                # Determine if coordinates are normalized or absolute
                # If both values are <= 1, assume normalized; otherwise assume absolute
                if x <= 1.0 and y <= 1.0:
                    # Normalized coordinates
                    norm_x, norm_y = x, y
                    abs_x = int(norm_x * screen_width)
                    abs_y = int(norm_y * screen_height)
                else:
                    # Absolute coordinates
                    abs_x, abs_y = int(x), int(y)
                    norm_x = abs_x / screen_width
                    norm_y = abs_y / screen_height
                
                return {
                    "success": True,
                    "found": True,
                    "query": query,
                    "response": response_text,
                    "coordinates": {
                        "normalized": {"x": norm_x, "y": norm_y},
                        "absolute": {"x": abs_x, "y": abs_y}
                    },
                    "screen_dimensions": {"width": screen_width, "height": screen_height}
                }
            else:
                return {
                    "success": True,
                    "found": False,
                    "query": query,
                    "response": response_text,
                    "error": "Could not parse coordinates from response or element not found"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to analyze image with UI-TARS: {str(e)}"
            }

    async def _verify_ui_action(
        self,
        action_description: str,
        expected_result: str,
        verification_query: str,
        timeout: float = 3.0,
        comparison_image: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify that a UI action had the expected result.
        
        Args:
            action_description: Description of what action was performed
            expected_result: What should have happened
            verification_query: What to look for to verify success
            timeout: How long to wait for changes (seconds)
            comparison_image: Optional before image for comparison
        
        Returns:
            Verification result with success status and details
        """
        import time
        
        try:
            # Wait for the UI to settle after the action
            time.sleep(timeout)
            
            # Take a screenshot to verify the current state
            image_data, image_path, cursor_pos = await self._screenshot_ui(
                output_prefix="verification"
            )
            
            # Use UI-TARS to check if the expected element/state is present
            verification_result = await self._ui_tars_analyze(
                image_path=image_path,
                query=verification_query
            )
            
            # Analyze the verification result
            verification_success = False
            verification_details = {}
            
            if verification_result['success']:
                if verification_result.get('found'):
                    verification_success = True
                    verification_details = {
                        "found_element": True,
                        "coordinates": verification_result['coordinates'],
                        "ai_response": verification_result['response']
                    }
                else:
                    verification_details = {
                        "found_element": False,
                        "ai_response": verification_result['response'],
                        "search_query": verification_query
                    }
            else:
                verification_details = {
                    "ai_error": verification_result.get('error', 'Unknown error'),
                    "search_query": verification_query
                }
            
            # Optional: Compare with before image if provided
            comparison_details = None
            if comparison_image and os.path.exists(comparison_image):
                try:
                    # Basic file comparison (could be enhanced with image diff)
                    with open(comparison_image, 'rb') as f1, open(image_path, 'rb') as f2:
                        before_size = len(f1.read())
                        after_size = len(f2.read())
                        
                    comparison_details = {
                        "before_image": comparison_image,
                        "after_image": image_path,
                        "file_size_changed": before_size != after_size,
                        "before_size": before_size,
                        "after_size": after_size
                    }
                except Exception as e:
                    comparison_details = {"comparison_error": str(e)}
            
            return {
                "success": True,
                "verification_passed": verification_success,
                "action_description": action_description,
                "expected_result": expected_result,
                "verification_query": verification_query,
                "verification_details": verification_details,
                "comparison_details": comparison_details,
                "verification_screenshot": image_path,
                "waited_seconds": timeout,
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Verification failed: {str(e)}",
                "action_description": action_description,
                "expected_result": expected_result
            }

async def main():
    ui_explorer = UIExplorer()
    mcp = Server("UI Explorer")
    logger.debug("Registering handlers")

    @mcp.list_resources()
    async def handle_list_resources() -> Dict[str, Any]:
        return types.Resource(
            uri=types.AnyUrl("mcp://ui_explorer/regions"),
            name="Regions",
            description="Regions that can be used for UI exploration",
            mimeType="application/json",
            size=len(get_predefined_regions()),
            annotations={
                "mcp:ui_explorer": {
                    "regions": get_predefined_regions()
                }
            }
        )

    @mcp.read_resource()
    async def handle_read_resource(uri: types.AnyUrl) -> Dict[str, Any]:
        logger.debug(f"Handling read_resource request for URI: {uri}")
        if uri.scheme != "regions":
            logger.error(f"Unsupported URI scheme: {uri.scheme}")
            raise ValueError(f"Unsupported URI scheme: {uri.scheme}")
        
        if uri.path == "regions":
            return json.dumps(get_predefined_regions())
        else:
            logger.error(f"Unsupported resource path: {uri.path}")
            raise ValueError(f"Unsupported resource path: {uri.path}")

    @mcp.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="explore_ui",
                description="Explore UI elements hierarchically and return the hierarchy data. Control type is required.",
                inputSchema=ExploreUIInput.model_json_schema(),
            ),
            Tool(
                name="screenshot_ui",
                description="Take a screenshot with UI elements highlighted and return confirmation message.",
                inputSchema=ScreenshotUIInput.model_json_schema(),
            ),
            Tool(
                name="click_ui_element",
                description="Click at specific X,Y coordinates on the screen.",
                inputSchema=ClickUIElementInput.model_json_schema(),
            ),
            Tool(
                name="keyboard_input",
                description="Send keyboard input (type text).",
                inputSchema=KeyboardInputInput.model_json_schema(),
            ),
            Tool(
                name="press_key",
                description="Press a specific keyboard key (like Enter, Tab, Escape, etc.)",
                inputSchema=PressKeyInput.model_json_schema(),
            ),
            Tool(
                name="hot_key",
                description="Press a keyboard shortcut combination (like Ctrl+C, Alt+Tab, etc.)",
                inputSchema=HotKeyInput.model_json_schema(),
            ),
            Tool(
                name="find_elements_near_cursor",
                description="Find UI elements closest to the current cursor position.",
                inputSchema=FindNearCursorInput.model_json_schema(),
            ),
            Tool(
                name="ui_tars_analyze",
                description="Use UI-TARS model to identify coordinates of UI elements on screen from a screenshot.",
                inputSchema=UITarsInput.model_json_schema(),
            ),
            Tool(
                name="verify_ui_action",
                description="Verify the result of a UI action.",
                inputSchema=UIVerificationInput.model_json_schema(),
            )
        ]

    @mcp.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        if name == "explore_ui":
            args = ExploreUIInput(**arguments)
            result = await ui_explorer._explore_ui(
                args.region,
                args.depth,
                args.min_size,
                args.focus_window,
                args.visible_only,
                args.control_type,
                args.text
            )
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "screenshot_ui":
            args = ScreenshotUIInput(**arguments)
            image_data, image_path, cursor_position = await ui_explorer._screenshot_ui(
                args.region,
                args.highlight_levels,
                args.output_prefix,
                args.min_size,
                args.max_depth,
                args.focus_only
            )
            return [
                types.TextContent(type="text", text=f"Screenshot saved to: {image_path}"),
                types.TextContent(type="text", text=json.dumps(cursor_position, indent=2))
            ]
        
        elif name == "click_ui_element":
            args = ClickUIElementInput(**arguments)
            result = await ui_explorer._click_ui_element(
                x=args.x,
                y=args.y,
                wait_time=args.wait_time,
                normalized=args.normalized
            )
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "keyboard_input":
            args = KeyboardInputInput(**arguments)
            result = await ui_explorer._keyboard_input(
                args.text,
                args.delay,
                args.interval,
                args.press_enter
            )
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "press_key":
            args = PressKeyInput(**arguments)
            result = await ui_explorer._press_key(
                args.key,
                args.delay,
                args.presses,
                args.interval
            )
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "hot_key":
            args = HotKeyInput(**arguments)
            result = await ui_explorer._hot_key(
                args.keys,
                args.delay
            )
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "find_elements_near_cursor":
            args = FindNearCursorInput(**arguments)
            result = await ui_explorer._find_elements_near_cursor(
                max_distance=args.max_distance,
                control_type=args.control_type,
                limit=args.limit
            )
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "ui_tars_analyze":
            args = UITarsInput(**arguments)
            result = await ui_explorer._ui_tars_analyze(
                image_path=args.image_path,
                query=args.query,
                api_url=args.api_url,
                model_name=args.model_name
            )
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "verify_ui_action":
            args = UIVerificationInput(**arguments)
            result = await ui_explorer._verify_ui_action(
                args.action_description,
                args.expected_result,
                args.verification_query,
                args.timeout,
                args.comparison_image
            )
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    @mcp.get_prompt()
    async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        logger.debug(f"Handling get_prompt request for {name} with args {arguments}")
        if name != "mcp-demo":
            logger.error(f"Unknown prompt: {name}")
            raise ValueError(f"Unknown prompt: {name}")

        prompt = PROMPT_TEMPLATE

        logger.debug(f"Returning UI Explorer prompt")
        return types.GetPromptResult(
            description=f"UI Explorer Guide",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=prompt.strip()),
                )
            ],
        )

    async with stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await mcp.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ui_explorer",
                server_version="0.1.1",
                capabilities=mcp.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

class ServerWrapper():
    """A wrapper to compat with mcp[cli]"""
    def run(self):
        import asyncio
        asyncio.run(main())

wrapper = ServerWrapper()