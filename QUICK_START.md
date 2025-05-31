# 🚀 Quick Start: Record Your First Macro

Get started with macro recording in under 2 minutes!

## ⚡ Super Quick Start

### Windows Users (Easy Way)
```cmd
# Record a macro
record_macro.bat "My First Macro"

# Play it back
play_macro.bat "macros/My_First_Macro_20250130_143022/macro.json"
```

### All Users (Command Line)
```bash
# Record a macro
python record_macro.py --name "My First Macro"

# Play it back
python play_macro.py --file "macros/My_First_Macro_20250130_143022/macro.json"
```

## 🎬 Recording Your First Workflow

1. **Start the recorder:**
   ```bash
   python record_macro.py --name "Login to Gmail"
   ```

2. **You'll see this interface:**
   ```
   🎬 Standalone Macro Recorder
   📝 Macro Name: Login to Gmail
   📄 Description: 
   
   🎮 Controls:
      F9  - Start/Stop recording
      F10 - Pause/Resume recording
      ESC - Emergency stop and exit
   
   ⚠️  Note: Recording captures ALL mouse and keyboard input!
      Make sure to only perform the actions you want to record.
   
   🎮 Hotkey controls active!
   🚀 Starting macro recorder...
      Press F9 to start recording when ready
   ⚪ Status: IDLE | Events: 0
   ```

3. **Press F9 to start recording** - you'll see:
   ```
   🔴 RECORDING STARTED: Login to Gmail
      Perform your workflow now...
   🔴 Status: RECORDING | Events: 0
   ```

4. **Perform your workflow** (e.g., open browser, navigate to Gmail, enter credentials)

5. **Press F9 again to stop** - you'll see:
   ```
   ⏹️  RECORDING STOPPED
      Events recorded: 15
      Files saved:
        📁 macros/Login_to_Gmail_20250130_143022/macro.json
        📁 macros/Login_to_Gmail_20250130_143022/macro.py
        📁 macros/Login_to_Gmail_20250130_143022/README.md
        📁 macros/Login_to_Gmail_20250130_143022.zip
   
   ✅ Macro 'Login to Gmail' saved successfully!
   ```

## 📦 What You Get: Complete Package

Your macro is saved as an **organized package** with everything included:

```
macros/
└── Login_to_Gmail_20250130_143022/
    ├── macro.json                    # 📄 Complete macro data
    ├── macro.py                      # 🐍 Executable Python script  
    ├── README.md                     # 📚 Documentation
    └── screenshots/                  # 📸 Enhanced action screenshots
        ├── 001_initial_state.png    # Initial UI state
        ├── 002_click.png            # Button click with green highlight
        ├── 003_type.png             # Text input with blue highlight
        └── 004_final_state.png      # Final result
```

## 🎭 Playing Back Your Macro

1. **Test your recording:**
   ```bash
   python play_macro.py --file "macros/Login_to_Gmail_20250130_143022/macro.json"
   ```

2. **Or run the Python script directly:**
   ```bash
   python "macros/Login_to_Gmail_20250130_143022/macro.py"
   ```

3. **You'll see:**
   ```
   🎭 Standalone Macro Player
   🎮 Ready to play back recorded macros
   
   📂 Loading macro: macro.json
   🎯 Speed multiplier: 1.0x
   🔍 UI verification: Enabled
   🛑 Stop on verification failure: No
   
   ⏰ Starting playback in:
      3...
      2...
      1...
   
   🎬 PLAYBACK STARTED!
   ```

4. **Watch your workflow replay automatically!**

## 🎯 What Gets Recorded?

- ✅ **Mouse clicks** - Exact coordinates and timing with **focused screenshots**
- ✅ **Keyboard input** - Smart text buffering (records final URLs, etc.)
- ✅ **UI context** - Information about what you clicked on
- ✅ **Enhanced screenshots** - Visual verification with highlights and indicators
- ✅ **Timing** - Natural delays between actions

## 📸 Enhanced Screenshots

Each action gets a **smart screenshot** that shows:

- **🟢 Green highlights** around clickable elements (buttons, links)
- **🔵 Blue highlights** around input fields (text boxes, forms)  
- **🔴 Red dots** showing exact click positions
- **📐 Element boundaries** for context
- **🎯 Action indicators** (cursors, focus indicators)

Screenshots are **cropped to show only relevant UI elements** - no more giant full-screen images!

## 📦 Package Benefits

### **Everything Organized**
- All files in one directory
- Screenshots numbered and named by action
- Complete documentation included
- ZIP file for easy sharing

### **Visual Verification**  
- See exactly what was clicked
- Understand the UI context
- Debug issues easily
- Share with visual proof

### **Multiple Ways to Use**
- JSON file for programmatic playback
- Python script for direct execution  
- ZIP package for sharing
- README for documentation

## 🔧 Troubleshooting

### "pynput not available"
```bash
pip install pynput
```

### "PIL/Pillow not available"  
```bash
pip install pillow
```

### Hotkeys not working
- Make sure the terminal window has focus
- Try running as administrator on Windows
- Check if other software is intercepting F9/F10/ESC

### Recording seems stuck
- Press ESC for emergency stop
- Check the status line at the bottom
- Make sure you pressed F9 to start

### Screenshots not generated
- Check that Pillow is installed: `pip install pillow`
- Look for error messages in the console
- Ensure you have write permissions in the macros directory

## 🎮 Pro Tips

1. **Start simple** - Record a 3-4 step workflow first
2. **Wait for UI** - Give pages time to load before clicking
3. **Test immediately** - Play back right after recording
4. **Use meaningful names** - You'll thank yourself later
5. **Add descriptions** - Helps remember what the macro does
6. **Review screenshots** - Check the generated images to verify they captured the right elements

## 🔄 Next Steps

Once you've recorded and tested a macro:

1. **Share the package** - Send the ZIP file to others
2. **Use with MCP Server** - Your macros work with the full MCP UI Explorer
3. **Build complex automations** - Chain multiple macros together
4. **Customize playback** - Adjust speed, verification, etc.
5. **Archive workflows** - Keep packages for future use

## 📚 Need More Help?

- Read the full [MACRO_TOOLS.md](MACRO_TOOLS.md) documentation
- Check the troubleshooting section
- Look at the generated README.md in your macro package
- Examine the screenshots to understand what was recorded

Happy automating! 🤖 