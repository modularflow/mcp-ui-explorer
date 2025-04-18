# UI Explorer MCP Server

An MCP server that provides tools for exploring and interacting with UI elements on your screen.

## Features

- Explore UI hierarchies: Scan and analyze all UI elements on your screen
- Screenshot UI with highlights: Visualize UI elements with boundaries and hierarchy
- Control mouse clicks: Click on UI elements based on type, text, or position
- Explore specific regions: Focus on parts of the screen like top-left, center, etc.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/modularflow/mcp-ui-explorer
cd mcp-ui-explorer
uv venv
source .venv/bin/activate #.venv/Scripts/activate on Windows
uv pip install -e .
```

## Usage

### Method 1: Run as a development server

```bash
fastmcp dev mcp_ui_explorer.py
```

This will start the server in development mode with an interactive testing environment.

### Method 2: Install in Claude Desktop

```bash
fastmcp install mcp_ui_explorer.py --name "UI Explorer"
```

This will install the server for persistent use within the Claude Desktop app.

### Method 3: Run the server directly

```bash
python mcp_ui_explorer.py
```

## How to Use

### 1. Explore UI Structure

Use the `explore_ui` tool to get a complete hierarchy of UI elements:

Parameters:
- `region`: Screen region to analyze ("screen", "top", "bottom", "left", "right", etc.)
- `depth`: Maximum hierarchy depth to analyze (default: 5)
- `min_size`: Minimum element size to include (default: 5px)
- `focus_window`: Only analyze the foreground window (default: False)
- `visible_only`: Only include elements visible on screen (default: True)

### 2. Take a Screenshot with UI Elements Highlighted

Use the `screenshot_ui` tool to visualize the UI elements:

Parameters:
- `region`: Screen region to analyze
- `highlight_levels`: Use different colors for hierarchy levels (default: True)
- `output_prefix`: Prefix for output files (default: "ui_hierarchy")

### 3. Click on UI Elements

Use the `click_ui_element` tool to interact with the UI:

Parameters:
- `control_type`: Control type to search for (e.g., "Button")
- `text`: Text content to search for
- `element_path`: Path to element (e.g., "0.children.3.children.2")
- `wait_time`: Seconds to wait before clicking (default: 2)
- `hierarchy_data`: Hierarchy data from explore_ui (optional)

## Example Workflow

1. First, explore the UI to understand what's on the screen:
   ```
   explore_ui(region="screen")
   ```

2. Take a screenshot to visualize the elements:
   ```
   screenshot_ui(region="screen")
   ```

3. Click on a specific button:
   ```
   click_ui_element(control_type="Button", text="Submit")
   ```

## Requirements

- Windows operating system
- Python 3.10+
- FastMCP 2.0+
- PyAutoGUI
- PyWinAuto
- Pillow 
