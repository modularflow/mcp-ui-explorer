import os
import sys
import logging
import json
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

You can use this tool to explore and interact with UI elements on the screen. Here's how:

    1. **Explore the UI structure** with the `explore_ui` tool:
    - This returns elements matching your criteria (control_type is required, defaults to "Button")
    - You can specify regions like "screen", "top-left", etc.
    - Filter by text content with the text parameter (case-insensitive, partial match)
    - When filtering by control_type or text, results are automatically flattened
    
    Example:
    ```
    explore_ui(region="screen", control_type="Button")
    explore_ui(region="top-left", min_size=10, control_type="Window", text="firefox")
    ```

    2. **Visualize the UI** with the `screenshot_ui` tool:
    - This returns an image showing detected UI elements
    - Elements are highlighted with their boundaries
    - Different colors can represent hierarchy levels
    - Also supports text filtering for finding specific elements
    
    Example:
    ```
    screenshot_ui(region="screen", control_type="Button")
    screenshot_ui(region="bottom-right", control_type="Edit", text="search")
    ```

    3. **Click on UI elements** with the `click_ui_element` tool:
    - Control type is required (e.g., "Button")
    - You can filter by text content
    - Or use a specific path from the hierarchy
    
    Example:
    ```
    click_ui_element(control_type="Button", text="Submit")
    click_ui_element(control_type="Window", text="firefox")
    click_ui_element(control_type="Button", element_path="0.children.3.children.2", wait_time=1.0)
    ```
    
    4. **Type text** with the `keyboard_input` tool:
    - Send text to the currently focused element
    - Control typing speed and behavior
    
    Example:
    ```
    keyboard_input(text="Hello world", delay=0.5, press_enter=true)
    keyboard_input(text="user@example.com", interval=0.1)
    ```
    
    5. **Press keyboard keys** with the `press_key` tool:
    - Press special keys like Enter, Tab, Escape, etc.
    - Control timing and repetition
    
    Example:
    ```
    press_key(key="tab", presses=3)
    press_key(key="space", delay=1.0)
    ```
    
    6. **Use keyboard shortcuts** with the `hot_key` tool:
    - Press key combinations like Ctrl+C, Alt+Tab, etc.
    
    Example:
    ```
    hot_key(keys=["ctrl", "c"])
    hot_key(keys=["alt", "tab"], delay=0.5)
    ```

    Example workflow:
    1. First explore the UI to find buttons: explore_ui(control_type="Button")
    2. Find specific elements: explore_ui(control_type="Window", text="firefox")
    3. Take a screenshot to visualize specific elements: screenshot_ui(control_type="Button", text="submit")
    4. Click on a specific element: click_ui_element(control_type="Button", text="Submit")
    5. Type text or use keyboard shortcuts as needed
        """

# Define enums for input validation
class RegionType(str, Enum):
    SCREEN = "screen"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
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
    depth: int = Field(default=5, description="Maximum depth to analyze")
    min_size: int = Field(default=5, description="Minimum element size to include")
    focus_window: bool = Field(default=False, description="Only analyze the foreground window")
    visible_only: bool = Field(default=True, description="Only include elements visible on screen")
    control_type: ControlType = Field(default=ControlType.BUTTON, description="Only include elements of this control type (default: Button)")
    text: Optional[str] = Field(default=None, description="Only include elements containing this text (case-insensitive, partial match)")

class ScreenshotUIInput(BaseModel):
    region: Optional[Union[RegionType, str]] = Field(
        default=None, 
        description="Region to analyze: predefined regions or custom 'left,top,right,bottom' coordinates"
    )
    highlight_levels: bool = Field(default=True, description="Use different colors for hierarchy levels")
    output_prefix: str = Field(default="ui_hierarchy", description="Prefix for output files")
    control_type: ControlType = Field(default=ControlType.BUTTON, description="Only include elements of this control type (default: Button)")
    text: Optional[str] = Field(default=None, description="Only include elements containing this text (case-insensitive, partial match)")

class ClickUIElementInput(BaseModel):
    control_type: ControlType = Field(
        description="Control type to search for (e.g., 'Button')"
    )
    text: Optional[str] = Field(default=None, description="Text content to search for")
    element_path: Optional[str] = Field(default=None, description="Path to element (e.g., '0.children.3.children.2')")
    wait_time: float = Field(default=2.0, description="Seconds to wait before clicking")
    hierarchy_data: Optional[Dict[str, Any]] = Field(default=None, description="Hierarchy data from explore_ui (if not provided, will run explore_ui)")

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

class UIExplorer:
    def __init__(self):
        self.regions: Dict[str, Any] = {}

    async def _explore_ui(
        self,
        region: Optional[Union[RegionType, str]] = None,
        depth: int = 5,
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
            depth: Maximum depth to analyze (default: 5)
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
        
        # Return the hierarchy and stats
        return {
            "hierarchy": filtered_hierarchy,
            "stats": {
                "total_matches": total_matches,
                "control_type": control_type.value if control_type else "all",
                "text_filter": text if text else None
            }
        }

    async def _screenshot_ui(
        self,
        region: Optional[Union[RegionType, str]] = None,
        highlight_levels: bool = True,
        output_prefix: str = "ui_hierarchy",
        control_type: ControlType = ControlType.BUTTON,
        text: Optional[str] = None
    ) -> bytes:
        """
        Take a screenshot with UI elements highlighted and return it as an image.
        
        Args:
            region: Region to analyze: predefined regions or custom 'left,top,right,bottom' coordinates
            highlight_levels: Use different colors for hierarchy levels (default: True)
            output_prefix: Prefix for output files (default: "ui_hierarchy")
            control_type: Only include elements of this control type (default: Button)
            text: Only include elements containing this text (case-insensitive, partial match)
        
        Returns:
            Screenshot with UI elements highlighted
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
        
        # Analyze UI elements
        ui_hierarchy = analyze_ui_hierarchy(
            region=region_coords,
            max_depth=5,
            focus_only=False,
            min_size=5,
            visible_only=True
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
        
        # Create visualization
        image_path = visualize_ui_hierarchy(filtered_hierarchy, output_prefix, highlight_levels)
        
        # Load the image and return it
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Clean up the temporary file
        try:
            os.remove(image_path)
        except:
            pass
        
        return image_data

    async def _click_ui_element(
        self,
        control_type: ControlType,
        text: Optional[str] = None, 
        element_path: Optional[str] = None,
        wait_time: Optional[float] = 2.0,
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
        # Get hierarchy data if not provided
        hierarchy = None
        if hierarchy_data and "hierarchy" in hierarchy_data:
            hierarchy = hierarchy_data["hierarchy"]
        else:
            result = await self._explore_ui(visible_only=True)
            if "hierarchy" in result:
                hierarchy = result["hierarchy"]
            else:
                return {"error": "Failed to get UI hierarchy"}
        
        # Find matching elements
        matches = []
        
        def search_element(element, current_path=""):
            # Skip elements without control_type
            if 'control_type' not in element:
                return
                
            # Check if this element matches
            control_type_match = element['control_type'] == control_type.value
                
            text_match = False
            if text:
                if text.lower() in element['text'].lower():
                    text_match = True
            else:
                text_match = True
                
            if control_type_match and text_match:
                matches.append((element, current_path))
                
            # Search children
            if 'children' in element:
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
                        
                # Skip if element doesn't have control_type
                if 'control_type' not in element:
                    return {"error": f"Element at path {element_path} has no control_type"}
                    
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
        
        # Verify element has required fields
        if 'control_type' not in selected:
            return {"error": "Selected element has no control_type"}
            
        if 'position' not in selected:
            return {"error": "Selected element has no position data"}
        
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
                "message": f"Clicked {selected['control_type']} element at ({x}, {y})",
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
                description="Take a screenshot with UI elements highlighted and return it as an image. Control type is required.",
                inputSchema=ScreenshotUIInput.model_json_schema(),
            ),
            Tool(
                name="click_ui_element",
                description="Click on a UI element based on search criteria. Control type is required.",
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
            image_data = await ui_explorer._screenshot_ui(
                args.region,
                args.highlight_levels,
                args.output_prefix,
                args.control_type,
                args.text
            )
            return [types.TextContent(type="image", image=image_data)]
        
        elif name == "click_ui_element":
            args = ClickUIElementInput(**arguments)
            result = await ui_explorer._click_ui_element(
                args.control_type,
                args.text,
                args.element_path,
                args.wait_time,
                args.hierarchy_data
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