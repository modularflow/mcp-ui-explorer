# UI Explorer MCP Server

An MCP server that provides tools for exploring and interacting with UI elements on your screen.

## Features

- Explore UI hierarchies: Scan and analyze all UI elements on your screen
- Screenshot UI with highlights: Visualize UI elements with boundaries and hierarchy
- Control mouse clicks: Click on UI elements based on coordinates
- Explore specific regions: Focus on parts of the screen like top-left, center, etc.
- **🎬 Macro Recording**: Record and playback UI workflows independently or through MCP

## 🚀 Quick Start: Standalone Macro Recording

**New!** You can now record UI workflows without running the MCP server:

```bash
# Record a workflow
python record_macro.py --name "Login Workflow"

# Play it back
python play_macro.py --file "macros/Login Workflow.json"
```

**Windows users can use the batch files:**
```cmd
record_macro.bat "My Workflow"
play_macro.bat "macros/My Workflow.json"
```

👉 **See [QUICK_START.md](QUICK_START.md) for a 2-minute tutorial**
👉 **See [MACRO_TOOLS.md](MACRO_TOOLS.md) for complete documentation**

### What Gets Recorded?
- ✅ Mouse clicks with exact coordinates
- ✅ Keyboard input with smart text buffering  
- ✅ UI context for reliable playback
- ✅ Screenshots for verification
- ✅ Timing information for natural replay

### Recording Controls
- **F9**: Start/Stop recording
- **F10**: Pause/Resume
- **ESC**: Emergency stop

## Installation Options

### Option 1: Using pip (recommended)

Install the package globally or in a virtual environment:

```bash
pip install mcp-ui-explorer
```

### Option 2: Using git clone

1. Clone the repository:
```bash
git clone https://github.com/modularflow/mcp-ui-explorer
cd mcp-ui-explorer
```

2. Install the package:
   - Using pip in development mode:
   ```bash
   pip install -e .
   ```
   
   - OR using uv (recommended for development):
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e .
   ```

## MCP Server Configuration

After installing the package, you need to configure your MCP client to use the UI Explorer server.

### For Roo in Cursor

Add this JSON to your MCP Server config at: 
`C:\Users\<user_name>\AppData\Roaming\Cursor\User\globalStorage\rooveterinaryinc.roo-cline\settings\mcp_settings.json`

```json
{
  "mcpServers": {
    "ui-explorer": {
      "command": "uvx",
      "args": [
        "mcp-ui-explorer"
      ]
    }
  }
}
```

### For Claude Desktop App

Add the server configuration to:
`C:\Users\<user_name>\AppData\Roaming\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ui-explorer": {
      "command": "uvx",
      "args": [
        "mcp-ui-explorer"
      ]
    }
  }
}
```

### For Direct Use with uvx

If you've installed the package (either globally or in a virtual environment), you can directly use `uvx` to run the server without additional configuration:

```bash
uvx mcp-ui-explorer
```

## MCP Tools

The UI Explorer provides several MCP tools for UI automation and exploration. These tools are available when using the MCP server interface.

## Usage Guide

### 1. Explore UI Structure

Use the `explore_ui` tool to get a complete hierarchy of UI elements:

Parameters:
- `region`: Screen region to analyze ("screen", "top", "bottom", "left", "right", "center", etc.)
- `depth`: Maximum hierarchy depth to analyze (default: 5)
- `min_size`: Minimum element size to include (default: 5px)
- `focus_window`: Only analyze the foreground window (default: False)
- `visible_only`: Only include elements visible on screen (default: True)
- `control_type`: Type of control to search for (default: "Button")
- `text`: Filter elements by text content (optional)

### 2. Take a Screenshot with UI Elements Highlighted

Use the `screenshot_ui` tool to visualize the UI elements:

Parameters:
- `region`: Screen region to analyze
- `highlight_levels`: Use different colors for hierarchy levels (default: True)
- `output_prefix`: Prefix for output files (default: "ui_hierarchy")

### 3. Click at Screen Coordinates

Use the `click_ui_element` tool to click at specific coordinates:

Parameters:
- `x`: X coordinate to click (required)
- `y`: Y coordinate to click (required)
- `wait_time`: Seconds to wait before clicking (default: 2.0)

### 4. Keyboard Input and Shortcuts

The tool also provides options for keyboard input and shortcuts. See the UI Explorer guide in the MCP interface for details.

## Example Workflow

1. First, explore the UI to understand what's on the screen:
   ```
   explore_ui(region="screen", control_type="Button")
   ```

2. Take a screenshot to visualize the elements:
   ```
   screenshot_ui(region="screen")
   ```

3. Note the coordinates of elements you want to click, then click at those coordinates:
   ```
   click_ui_element(x=500, y=300)
   ```

4. Type text or use keyboard shortcuts as needed:
   ```
   keyboard_input(text="Hello world", press_enter=true)
   ```

## Requirements

- Windows operating system
- Python 3.10+
- MCP 1.6.0+
- PyAutoGUI
- PyWinAuto
- Pillow
- Pydantic 2.0+
