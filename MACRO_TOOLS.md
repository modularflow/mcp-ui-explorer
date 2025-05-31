# Standalone Macro Recording Tools

This directory contains standalone tools for recording and playing back UI macros independently of the MCP server. These tools are perfect for testing and creating workflows that can later be used by the MCP UI Explorer.

## 🎬 Recording Macros

### Basic Usage

```bash
# Record a simple workflow
python record_macro.py --name "Login Workflow"

# Record with description
python record_macro.py --name "File Upload" --description "Upload a file to the website"
```

### Recording Controls

During recording, use these hotkeys:
- **F9**: Start/Stop recording
- **F10**: Pause/Resume recording  
- **ESC**: Emergency stop and save

### Recording Features

The macro recorder captures:
- ✅ **Mouse clicks** with exact coordinates and **focused screenshots**
- ✅ **Mouse position during actions** (clicks, scrolls) - no movement tracking
- ✅ **Keyboard input** with intelligent text buffering and error correction
- ✅ **UI context** information about elements being interacted with
- ✅ **Enhanced screenshots** with highlighted UI elements and action indicators
- ✅ **Timing** information for accurate playback

### Intelligent Input Recording

The recorder uses smart algorithms to capture only meaningful actions:

**Mouse Recording:**
- ❌ **No mouse movements** - movements are not recorded as separate events
- ✅ **Action positions only** - records mouse position when clicks or scrolls occur
- ✅ **Cleaner macros** - eliminates unnecessary movement noise

**Keyboard Recording:**
- ✅ **Text buffering** - accumulates keystrokes as you type
- ✅ **Error correction** - backspace and delete modify the text buffer instead of being recorded
- ✅ **Final text only** - records the committed text (e.g., URL after pressing Enter)
- ✅ **Smart commits** - automatically commits text on Enter, Tab, or Escape
- ❌ **No individual keystrokes** - eliminates typing noise and corrections

### Smart Text Handling

The recorder intelligently handles text input:
- Buffers keystrokes as you type (including corrections)
- Handles backspace and delete by modifying the text buffer
- Commits complete text when you press Enter, Tab, or Escape
- Records only the final committed text (like URLs after hitting Enter)
- Ignores navigation keys (arrows, home, end, page up/down)
- Preserves timing for natural playback

### 📦 **Package-Based Output**

Each recorded macro is saved as a complete **organized package**:

```
macros/
├── Login_Workflow_20250130_143022/          # 📁 Macro package directory
│   ├── macro.json                           # 📄 Complete macro data
│   ├── macro.py                             # 🐍 Executable Python script
│   ├── README.md                            # 📚 Package documentation
│   └── screenshots/                         # 📸 Action screenshots
│       ├── 001_initial_state.png           # Initial UI state
│       ├── 002_click.png                   # Focused click screenshot
│       ├── 003_type.png                    # Text input screenshot
│       └── 004_final_state.png             # Final UI state
└── Login_Workflow_20250130_143022.zip       # 📦 Complete package as ZIP

```

### 🎯 **Enhanced Screenshots**

Each action gets a **focused screenshot** that shows:

- **🟢 Green highlights** for clickable elements (buttons, links, etc.)
- **🔵 Blue highlights** for input fields (text boxes, forms, etc.)
- **🔴 Red dots** showing exact click positions
- **📐 UI element boundaries** for context
- **🎯 Action indicators** (click dots, text cursors, etc.)

Screenshots are:
- **Cropped to relevant UI elements** (not full screen)
- **Enhanced with visual indicators** 
- **Numbered sequentially** (001, 002, 003...)
- **Named by action type** (click, type, initial_state, final_state)

## 🎭 Playing Back Macros

### Basic Usage

```bash
# Play a recorded macro package
python play_macro.py --file "macros/Login_Workflow_20250130_143022/macro.json"

# Play at 2x speed
python play_macro.py --file "macros/File_Upload_20250130_143022/macro.json" --speed 2.0

# List available macros
python play_macro.py --list
```

### Direct Python Execution

```bash
# Run the generated Python script directly
python "macros/Login_Workflow_20250130_143022/macro.py"
```

### Playback Options

```bash
# Disable UI verification (faster)
python play_macro.py --file "macros/Test/macro.json" --no-verify

# Stop immediately if verification fails
python play_macro.py --file "macros/Critical/macro.json" --stop-on-failure

# Dry run (show what would happen without doing it)
python play_macro.py --file "macros/Test/macro.json" --dry-run
```

### Verification Features

The macro player can:
- ✅ **Verify UI context** using UI-TARS to ensure elements are still present
- ✅ **Adapt to UI changes** by finding similar elements if exact matches fail
- ✅ **Report verification results** for each action
- ✅ **Continue on failures** or stop based on your preference

## 🔧 Installation

Make sure you have the required dependencies:

```bash
# Install the main package dependencies
pip install -r requirements.txt

# Key dependencies for macro recording:
pip install pynput pillow
```

## 📁 File Structure

```
mcp-ui-explorer/
├── record_macro.py                          # Standalone recording tool
├── play_macro.py                           # Standalone playback tool
├── macros/                                 # Directory for saved macro packages
│   ├── Login_Workflow_20250130_143022/     # Individual macro package
│   │   ├── macro.json                      # Complete macro data
│   │   ├── macro.py                        # Executable Python script
│   │   ├── README.md                       # Package documentation
│   │   └── screenshots/                    # Action screenshots
│   │       ├── 001_initial_state.png      # UI state screenshots
│   │       ├── 002_click.png              # Focused action screenshots
│   │       └── ...
│   ├── Login_Workflow_20250130_143022.zip  # ZIP package for sharing
│   └── ...
└── screenshots/                            # Temporary screenshots (cleaned up)
```

## 🎯 Example Workflow

1. **Record a workflow:**
   ```bash
   python record_macro.py --name "Login to Gmail"
   # Press F9 to start recording
   # Perform your login steps
   # Press F9 to stop recording
   ```

2. **Check the package:**
   ```bash
   # View the generated README
   cat "macros/Login_to_Gmail_20250130_143022/README.md"
   
   # Look at the screenshots
   ls "macros/Login_to_Gmail_20250130_143022/screenshots/"
   ```

3. **Test the recording:**
   ```bash
   python play_macro.py --file "macros/Login_to_Gmail_20250130_143022/macro.json"
   ```

4. **Share the package:**
   ```bash
   # Send the ZIP file to someone else
   # They can extract and use it immediately
   unzip "macros/Login_to_Gmail_20250130_143022.zip" -d shared_macros/
   ```

## 🚀 Advanced Features

### Custom Recording Options

```bash
# Disable UI context capture (faster recording)
python record_macro.py --name "Simple Test" --no-ui-context

# Disable screenshots (faster recording, but no visual verification)
python record_macro.py --name "Quick Test" --no-screenshots

# Adjust mouse movement sensitivity
python record_macro.py --name "Precise Work" --mouse-threshold 10.0
```

### Package Management

```bash
# Extract a macro package
unzip "macros/My_Workflow_20250130_143022.zip" -d extracted/

# Run from extracted package
python "extracted/macro.py"

# Or use with player
python play_macro.py --file "extracted/macro.json"
```

## 🐛 Troubleshooting

### Common Issues

1. **"pynput not available"**
   ```bash
   pip install pynput
   ```

2. **"PIL/Pillow not available"**
   ```bash
   pip install pillow
   ```

3. **Recording not starting**
   - Make sure you press F9 to start recording
   - Check that pynput is installed correctly
   - Try running as administrator if on Windows

4. **Screenshots not generated**
   - Check that Pillow is installed
   - Ensure the macro package directory was created
   - Look for error messages in the console

5. **Playback fails**
   - UI might have changed since recording
   - Try with `--no-verify` to skip UI verification
   - Use `--dry-run` to see what would happen
   - Check the screenshots to understand what was recorded

### Tips for Better Recordings

1. **Keep it simple**: Record small, focused workflows
2. **Wait for UI**: Give UI elements time to load before interacting
3. **Use consistent timing**: Don't rush through the workflow
4. **Test immediately**: Play back the macro right after recording to verify it works
5. **Add descriptions**: Use meaningful names and descriptions for your macros
6. **Review screenshots**: Check the generated screenshots to ensure they captured the right elements

## 📦 Package Benefits

### **Organized Structure**
- All related files in one directory
- Screenshots organized and numbered
- Complete documentation included
- Easy to share and archive

### **Visual Verification**
- See exactly what was clicked/typed
- Understand the UI context
- Debug issues more easily
- Share workflows with visual proof

### **Multiple Formats**
- JSON for programmatic use
- Python for direct execution
- ZIP for easy sharing
- README for documentation

### **Self-Contained**
- No external dependencies for screenshots
- All paths are relative
- Works when moved or shared
- Complete audit trail

## 🔗 Integration with MCP Server

Once you've recorded and tested your macros with these standalone tools, you can use them with the MCP UI Explorer server:

```python
# Through the MCP server
await play_macro(
    macro_path="macros/Login_Workflow_20250130_143022/macro.json",
    speed_multiplier=1.0,
    verify_ui_context=True
)
```

The standalone tools and MCP server use the same underlying macro format, so workflows are fully compatible between both systems. 