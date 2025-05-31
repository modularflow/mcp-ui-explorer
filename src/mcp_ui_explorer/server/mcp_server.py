"""MCP server implementation for UI Explorer."""

import json
import asyncio
from typing import List, Dict, Any

from mcp import Tool
from mcp.server import InitializationOptions
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

from ..core.ui_explorer import UIExplorer
from ..models import *
from ..hierarchical_ui_explorer import get_predefined_regions
from ..utils.logging import get_logger


# Prompt template for the UI Explorer
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

## 🎯 **CORE WORKFLOW: Accessibility-First + Visual AI + Memory Learning**

The most effective approach uses accessibility APIs first, with visual AI and coordinate clicking as fallback:

    1. **FIRST: Find and click using accessibility** with the `click_ui_element_by_accessibility` tool:
    - Most reliable method for Windows applications
    - Finds elements by control type, text, automation ID, or class name
    - Works even if UI layout changes or screen resolution differs
    - Automatically falls back to coordinates if accessibility method fails
    
    Example:
    ```
    click_ui_element_by_accessibility(control_type="Button", text="login")
    click_ui_element_by_accessibility(text="submit")
    click_ui_element_by_accessibility(automation_id="loginBtn")
    click_ui_element_by_accessibility(class_name="submit-button")
    ```

    2. **FIRST ALTERNATIVE: Find elements using accessibility** with the `find_ui_elements` tool:
    - Use when you need to see all available elements before choosing
    - Returns element hierarchy and click coordinates
    - Helps understand the UI structure without clicking
    
    Example:
    ```
    find_ui_elements(control_type="Button", text="login")
    find_ui_elements(text="submit")  # Find any element containing "submit"
    find_ui_elements(automation_id="loginBtn")
    find_ui_elements(class_name="submit-button")
    ```

    3. **FALLBACK: Use visual AI** with the `ui_tars_analyze` tool + `screenshot_ui`:
    - Use when accessibility methods don't find the element
    - Take screenshot first, then use AI to locate elements visually
    - Describe what you're looking for in natural language
    
    Example:
    ```
    # Take screenshot for visual analysis
    screenshot_ui(region="screen")
    
    # Use AI to find elements visually
    ui_tars_analyze(image_path="ui_hierarchy_20250524_143022.png", query="login button")
    ui_tars_analyze(image_path="screenshot.png", query="submit button in the form")
    ```

    4. **LAST RESORT: Click by coordinates** with the `click_ui_element` tool:
    - Use coordinates from ui_tars_analyze or find_ui_elements
    - UI-TARS provides both absolute and normalized coordinates
    - Use only when accessibility methods fail
    
    Example:
    ```
    click_ui_element(x=500, y=300)  # Absolute coordinates
    click_ui_element(x=0.5, y=0.3, normalized=true)  # Normalized coordinates (0-1)
    ```

    5. **Interact with text and keyboard** as needed:
    - Type text: `keyboard_input(text="Hello world", press_enter=true)`
    - Press keys: `press_key(key="tab")`  
    - Shortcuts: `hot_key(keys=["ctrl", "c"])`

    6. **VERIFY the action worked** with the `verify_ui_action` tool:
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

    7. **SAVE MEMORY after each verified action**:
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
            "Action: Clicked login button using accessibility API (control_type=Button, text=login)",
            "Result: SUCCESS - Login dialog opened as expected",
            "App: Chrome browser on login page",
            "Verification: Found 'username and password fields' in dialog",
            "Timing: 2.0 seconds wait time worked well",
            "Method: Accessibility API successful, no fallback needed",
            "Screenshot: Only taken when needed for verification"
        ]
    }])
    
    # Link actions together in workflows
    mcp_memory_create_relations([{
        "from": "Website_Navigation_Workflow",
        "to": "Login_Button_Click_Action_2024", 
        "relationType": "INCLUDES_STEP"
    }])
    ```

📋 **ADDITIONAL TOOLS** (use as needed):

    8. **Take screenshots** with the `screenshot_ui` tool:
    - Use when you need to see the current UI state
    - Helpful for understanding complex interfaces
    - Required for visual AI analysis when accessibility methods fail
    - Returns highlighted UI elements for analysis
    
    Example:
    ```
    screenshot_ui(region="screen")  # Full screen with element highlighting
    screenshot_ui(region="top", focus_only=true)  # Top half, focused window only
    ```

    9. **Find elements near cursor** with the `find_elements_near_cursor` tool:
    - Finds UI elements closest to current cursor position
    - Returns absolute pixel coordinates
    - Useful when you know roughly where an element is
    
    Example:
    ```
    find_elements_near_cursor(max_distance=100, control_type="Button")
    ```

⚙️ **COORDINATE FORMATS**:
- `find_ui_elements` returns: `{"click_coordinates": {"absolute": {"x": 960, "y": 432}, "normalized": {"x": 0.5, "y": 0.3}}}`
- UI-TARS returns: `{"normalized": {"x": 0.5, "y": 0.3}, "absolute": {"x": 960, "y": 432}}`
- Other tools return: `{"coordinates": {"absolute": {...}, "normalized": {...}}}`
- Click tools accept: Both `{"x": 960, "y": 432}` and `{"x": 0.5, "y": 0.3, "normalized": true}`

🎯 **RECOMMENDED WORKFLOW SEQUENCE**:
    0. **Search memory first**: `mcp_memory_search_nodes("similar task keywords")`
    1. **Try accessibility clicking**: `click_ui_element_by_accessibility(control_type="Button", text="what you want")`
    2. **If accessibility fails, use visual AI**: `screenshot_ui()` then `ui_tars_analyze(image_path="screenshot.png", query="what you want")`
    3. **If visual AI fails, use coordinates**: `click_ui_element(x=absolute_x, y=absolute_y)`
    4. Interact as needed: `keyboard_input(text="...")` or `press_key(...)`
    5. Verify it worked: `verify_ui_action(action_description="...", expected_result="...", verification_query="...")`
    6. **Save memory**: `mcp_memory_create_entities([action_memory])` + `mcp_memory_create_relations([workflow_link])`

## 🧠 **MEMORY MANAGEMENT PATTERNS**

### **Entity Types to Create:**
- `UI_Action`: Individual clicks, typing, key presses with results and methods used
- `UI_Workflow`: Complete sequences of actions (login, file-open, etc.)  
- `UI_Element`: Specific buttons, fields, menus with accessibility properties
- `App_Context`: Application-specific behavior patterns
- `Troubleshooting`: Failed actions with solutions

### **Memory Structure Example:**
```
# Workflow entity
"Website_Login_Workflow_Chrome" (UI_Workflow)
  ├─ INCLUDES_STEP → "Navigate_To_Login_Page" (UI_Action)
  ├─ INCLUDES_STEP → "Click_Login_Button_Accessibility" (UI_Action) 
  ├─ INCLUDES_STEP → "Enter_Username" (UI_Action)
  └─ INCLUDES_STEP → "Enter_Password" (UI_Action)

# Action entity with detailed observations
"Click_Login_Button_Accessibility" (UI_Action)
  - "Method: Accessibility API successful (control_type=Button, text=login)"
  - "Fallback: Coordinate method not needed"
  - "Coordinates: absolute (960, 432) = normalized (0.5, 0.3)"
  - "Verification: SUCCESS - Login dialog appeared"
  - "Timing: 2.0s wait worked well"
  - "Context: Chrome browser, login page loaded"
  - "Element: automation_id=loginBtn, class_name=submit-button"
```

### **Search Strategies:**
- **By task**: `mcp_memory_search_nodes("login workflow")`
- **By app**: `mcp_memory_search_nodes("Chrome browser actions")`
- **By element**: `mcp_memory_search_nodes("submit button clicking")`
- **By method**: `mcp_memory_search_nodes("accessibility API successful")`
- **By failure**: `mcp_memory_search_nodes("verification failed solutions")`

### **Learning from Failures:**
```
# Document failures for future reference
mcp_memory_create_entities([{
    "name": "Login_Button_Accessibility_Failed_2024",
    "entityType": "Troubleshooting", 
    "observations": [
        "FAILED: Accessibility API couldn't find button (control_type=Button, text=login)",
        "Cause: Dynamic content or iframe",
        "Solution: Used UI-TARS to find actual position (0.52, 0.28)",
        "Lesson: Try UI-TARS when accessibility APIs fail",
        "App: Chrome browser with dynamic login form"
    ]
}])
```

## 🔧 **METHOD SELECTION GUIDE**

**Use Accessibility Methods When:**
- Element has clear control type (Button, Edit, CheckBox, etc.)
- Element has visible text or automation ID
- Working with standard Windows applications
- Need reliable clicking even if UI layout changes
- Want fastest, most reliable interaction

**Use Visual AI (UI-TARS) When:**
- Accessibility methods can't find the element
- Working with custom controls or web applications
- Element has no clear text but is visually distinct
- Need to find elements based on visual appearance
- Dealing with canvas-based or graphic applications

**Use Screenshots When:**
- Need to understand the current UI state
- Visual AI analysis is required
- Debugging why accessibility methods failed
- Documenting UI state for memory/learning

**Use Coordinate Clicking When:**
- Both accessibility and visual AI methods fail
- Very simple, one-time actions
- Elements are in fixed positions that won't change
- Legacy applications with poor accessibility support

**Element Finding Priority:**
1. `click_ui_element_by_accessibility` (accessibility API with built-in fallback)
2. `find_ui_elements` (accessibility API for exploration)
3. `ui_tars_analyze` (visual AI analysis)
4. `find_elements_near_cursor` (coordinate-based proximity)

**Clicking Priority:**
1. `click_ui_element_by_accessibility` (accessibility API with automatic coordinate fallback)
2. `click_ui_element` (coordinates from UI-TARS or other sources)
        """


def create_server() -> Server:
    """Create and configure the MCP server."""
    logger = get_logger(__name__)
    ui_explorer = UIExplorer()
    mcp = Server("UI Explorer")
    
    logger.debug("Registering handlers")

    @mcp.list_resources()
    async def handle_list_resources() -> List[types.Resource]:
        return [
            types.Resource(
                uri=types.AnyUrl("mcp://ui_explorer/regions"),
                name="Regions",
                description="Regions that can be used for UI exploration",
                mimeType="application/json",
            )
        ]

    @mcp.read_resource()
    async def handle_read_resource(uri: types.AnyUrl) -> str:
        logger.debug(f"Handling read_resource request for URI: {uri}")
        if uri.scheme != "mcp" or uri.path != "//ui_explorer/regions":
            logger.error(f"Unsupported URI: {uri}")
            raise ValueError(f"Unsupported URI: {uri}")
        
        return json.dumps(get_predefined_regions())

    @mcp.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="screenshot_ui",
                description="Take a screenshot with UI elements highlighted and return confirmation message.",
                inputSchema=ScreenshotUIInput.model_json_schema(),
            ),
            Tool(
                name="click_ui_element",
                description="Click at specific X,Y coordinates on the screen with automatic UI-TARS verification.",
                inputSchema=ClickUIElementInput.model_json_schema(),
            ),
            Tool(
                name="keyboard_input",
                description="Send keyboard input (type text) with automatic UI-TARS verification.",
                inputSchema=KeyboardInputInput.model_json_schema(),
            ),
            Tool(
                name="press_key",
                description="Press a specific keyboard key (like Enter, Tab, Escape, etc.) with automatic UI-TARS verification.",
                inputSchema=PressKeyInput.model_json_schema(),
            ),
            Tool(
                name="hot_key",
                description="Press a keyboard shortcut combination (like Ctrl+C, Alt+Tab, etc.) with automatic UI-TARS verification.",
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
            ),
            Tool(
                name="create_memory_summary",
                description="Create a memory summary of the current session actions and save to memory.",
                inputSchema=CreateMemorySummaryInput.model_json_schema(),
            ),
            Tool(
                name="document_step",
                description="Document a planned step for progress tracking and stuck detection.",
                inputSchema=DocumentStepInput.model_json_schema(),
            ),
            Tool(
                name="get_step_status",
                description="Get current step status and progress information.",
                inputSchema=GetStepStatusInput.model_json_schema(),
            ),
            Tool(
                name="start_macro_recording",
                description="Start recording a macro that captures user interactions with UI context information.",
                inputSchema=StartMacroRecordingInput.model_json_schema(),
            ),
            Tool(
                name="stop_macro_recording",
                description="Stop macro recording and save the recorded interactions to file(s).",
                inputSchema=StopMacroRecordingInput.model_json_schema(),
            ),
            Tool(
                name="pause_macro_recording",
                description="Pause or resume macro recording without stopping it completely.",
                inputSchema=PauseMacroRecordingInput.model_json_schema(),
            ),
            Tool(
                name="get_macro_status",
                description="Get the current status of macro recording including recorded events.",
                inputSchema=GetMacroStatusInput.model_json_schema(),
            ),
            Tool(
                name="play_macro",
                description="Play back a recorded macro file with optional speed control and UI verification.",
                inputSchema=PlayMacroInput.model_json_schema(),
            ),
            Tool(
                name="find_ui_elements",
                description="Find UI elements using accessibility APIs with various filter criteria (control type, text, automation ID, class name).",
                inputSchema=FindUIElementsInput.model_json_schema(),
            ),
            Tool(
                name="click_ui_element_by_accessibility",
                description="Click on a UI element using accessibility APIs to find it, with coordinate fallback. More reliable than coordinate clicking for most UI elements.",
                inputSchema=ClickUIElementByAccessibilityInput.model_json_schema(),
            )
        ]

    @mcp.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        logger.debug(f"Calling tool: {name} with arguments: {arguments}")
        
        try:
            if name == "screenshot_ui":
                args = ScreenshotUIInput(**arguments)
                result = await ui_explorer.screenshot_ui(
                    region=args.region,
                    highlight_levels=args.highlight_levels,
                    output_prefix=args.output_prefix,
                    min_size=args.min_size,
                    max_depth=args.max_depth,
                    focus_only=args.focus_only
                )
                return [
                    types.TextContent(type="text", text=f"Screenshot saved to: {result['image_path']}"),
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            
            elif name == "click_ui_element":
                args = ClickUIElementInput(**arguments)
                result = await ui_explorer.click_ui_element(
                    x=args.x,
                    y=args.y,
                    wait_time=args.wait_time,
                    normalized=args.normalized,
                    auto_verify=args.auto_verify,
                    verification_query=args.verification_query,
                    verification_timeout=args.verification_timeout
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "keyboard_input":
                args = KeyboardInputInput(**arguments)
                result = await ui_explorer.keyboard_input(
                    text=args.text,
                    delay=args.delay,
                    interval=args.interval,
                    press_enter=args.press_enter,
                    auto_verify=args.auto_verify,
                    verification_query=args.verification_query,
                    verification_timeout=args.verification_timeout
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "press_key":
                args = PressKeyInput(**arguments)
                result = await ui_explorer.press_key(
                    key=args.key,
                    delay=args.delay,
                    presses=args.presses,
                    interval=args.interval,
                    auto_verify=args.auto_verify,
                    verification_query=args.verification_query,
                    verification_timeout=args.verification_timeout
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "hot_key":
                args = HotKeyInput(**arguments)
                result = await ui_explorer.hot_key(
                    keys=args.keys,
                    delay=args.delay,
                    auto_verify=args.auto_verify,
                    verification_query=args.verification_query,
                    verification_timeout=args.verification_timeout
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "find_elements_near_cursor":
                args = FindNearCursorInput(**arguments)
                result = await ui_explorer.find_elements_near_cursor(
                    max_distance=args.max_distance,
                    control_type=args.control_type,
                    limit=args.limit
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "ui_tars_analyze":
                args = UITarsInput(**arguments)
                result = await ui_explorer.ui_tars_analyze(
                    image_path=args.image_path,
                    query=args.query,
                    api_url=args.api_url,
                    model_name=args.model_name
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "verify_ui_action":
                args = UIVerificationInput(**arguments)
                result = await ui_explorer.verify_ui_action(
                    action_description=args.action_description,
                    expected_result=args.expected_result,
                    verification_query=args.verification_query,
                    timeout=args.timeout,
                    comparison_image=args.comparison_image
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "create_memory_summary":
                args = CreateMemorySummaryInput(**arguments)
                result = await ui_explorer.create_memory_summary(
                    force_summary=args.force_summary
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "document_step":
                args = DocumentStepInput(**arguments)
                result = await ui_explorer.document_step(
                    step_description=args.step_description,
                    mark_previous_complete=args.mark_previous_complete,
                    completion_notes=args.completion_notes
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "get_step_status":
                args = GetStepStatusInput(**arguments)
                result = await ui_explorer.get_step_status(
                    show_all_steps=args.show_all_steps
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "start_macro_recording":
                args = StartMacroRecordingInput(**arguments)
                result = await ui_explorer.start_macro_recording(
                    macro_name=args.macro_name,
                    description=args.description,
                    capture_ui_context=args.capture_ui_context,
                    capture_screenshots=args.capture_screenshots,
                    mouse_move_threshold=args.mouse_move_threshold,
                    keyboard_commit_events=args.keyboard_commit_events
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "stop_macro_recording":
                args = StopMacroRecordingInput(**arguments)
                result = await ui_explorer.stop_macro_recording(
                    save_macro=args.save_macro,
                    output_format=args.output_format
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "pause_macro_recording":
                args = PauseMacroRecordingInput(**arguments)
                result = await ui_explorer.pause_macro_recording(
                    pause=args.pause
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "get_macro_status":
                args = GetMacroStatusInput(**arguments)
                result = await ui_explorer.get_macro_status(
                    include_events=args.include_events
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "play_macro":
                args = PlayMacroInput(**arguments)
                result = await ui_explorer.play_macro(
                    macro_path=args.macro_path,
                    speed_multiplier=args.speed_multiplier,
                    verify_ui_context=args.verify_ui_context,
                    stop_on_verification_failure=args.stop_on_verification_failure
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "find_ui_elements":
                args = FindUIElementsInput(**arguments)
                result = await ui_explorer.find_ui_elements(
                    control_type=args.control_type,
                    text=args.text,
                    automation_id=args.automation_id,
                    class_name=args.class_name,
                    focus_only=args.focus_only,
                    visible_only=args.visible_only,
                    max_depth=args.max_depth,
                    min_size=args.min_size
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "click_ui_element_by_accessibility":
                args = ClickUIElementByAccessibilityInput(**arguments)
                result = await ui_explorer.click_ui_element_by_accessibility(
                    control_type=args.control_type,
                    text=args.text,
                    automation_id=args.automation_id,
                    class_name=args.class_name,
                    element_index=args.element_index,
                    fallback_to_coordinates=args.fallback_to_coordinates,
                    wait_time=args.wait_time,
                    auto_verify=args.auto_verify,
                    verification_query=args.verification_query,
                    verification_timeout=args.verification_timeout
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            else:
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
                
        except Exception as e:
            logger.error(f"Tool {name} failed: {str(e)}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    @mcp.get_prompt()
    async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        logger.debug(f"Handling get_prompt request for {name} with args {arguments}")
        if name != "mcp-demo":
            logger.error(f"Unknown prompt: {name}")
            raise ValueError(f"Unknown prompt: {name}")

        logger.debug(f"Returning UI Explorer prompt")
        return types.GetPromptResult(
            description=f"UI Explorer Guide",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=PROMPT_TEMPLATE.strip()),
                )
            ],
        )

    return mcp


async def run_server():
    """Run the MCP server."""
    logger = get_logger(__name__)
    mcp = create_server()
    
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await mcp.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ui_explorer",
                server_version="0.2.0",
                capabilities=mcp.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


class ServerWrapper:
    """A wrapper to compat with mcp[cli]"""
    
    def run(self):
        asyncio.run(run_server()) 