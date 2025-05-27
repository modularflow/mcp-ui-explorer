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

    5. **Find elements near cursor** with the `find_elements_near_cursor` tool:
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