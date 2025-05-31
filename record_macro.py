#!/usr/bin/env python3
"""
Standalone Macro Recorder for MCP UI Explorer

This script allows you to record UI interactions independently of the MCP server.
The recorded macros can later be played back through the MCP server.

Usage:
    python record_macro.py --name "My Workflow" --description "Login to website"
    
Controls during recording:
    - F9: Start/Stop recording
    - F10: Pause/Resume recording
    - ESC: Emergency stop
"""

import argparse
import asyncio
import sys
import time
import threading
import queue
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.mcp_ui_explorer.services.macro_recorder import MacroRecorder
from src.mcp_ui_explorer.models.enums import MacroState
from src.mcp_ui_explorer.utils.logging import setup_logging, get_logger

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("Warning: pynput not available. Install with: pip install pynput")


class StandaloneMacroRecorder:
    """Standalone macro recorder with keyboard controls."""
    
    def __init__(self, macro_name: str, description: str = ""):
        self.logger = setup_logging()
        self.macro_name = macro_name
        self.description = description
        
        # Initialize the macro recorder
        self.recorder = MacroRecorder()
        
        # Control state
        self.is_running = True
        self.hotkey_listener = None
        
        # Thread-safe communication using standard queue
        self.pending_actions = queue.Queue()
        
        print(f"\n🎬 Standalone Macro Recorder")
        print(f"📝 Macro Name: {macro_name}")
        print(f"📄 Description: {description}")
        print(f"\n🎮 Controls:")
        print(f"   F9  - Start/Stop recording")
        print(f"   F10 - Pause/Resume recording")
        print(f"   ESC - Emergency stop and exit")
        print(f"\n⚠️  Note: Recording captures ALL mouse and keyboard input!")
        print(f"   Make sure to only perform the actions you want to record.")
    
    def start_hotkey_listener(self):
        """Start listening for hotkey controls."""
        if not PYNPUT_AVAILABLE:
            print("\n❌ Hotkey controls not available (pynput not installed)")
            print("   You'll need to manually control recording via the console")
            return
        
        def on_key_press(key):
            try:
                if key == keyboard.Key.f9:
                    # Use thread-safe method to queue the action
                    self.queue_action("toggle_recording")
                elif key == keyboard.Key.f10:
                    self.queue_action("toggle_pause")
                elif key == keyboard.Key.esc:
                    self.queue_action("emergency_stop")
            except Exception as e:
                self.logger.error(f"Hotkey error: {e}")
        
        self.hotkey_listener = keyboard.Listener(on_press=on_key_press)
        self.hotkey_listener.start()
        print("🎮 Hotkey controls active!")
    
    def queue_action(self, action: str):
        """Queue an action to be processed by the main loop (thread-safe)."""
        try:
            # Use standard queue which is thread-safe
            self.pending_actions.put(action, block=False)
        except Exception as e:
            self.logger.error(f"Failed to queue action {action}: {e}")
    
    async def process_pending_actions(self):
        """Process any pending actions from the hotkey listener."""
        try:
            # Process all pending actions
            while True:
                try:
                    # Non-blocking get
                    action = self.pending_actions.get(block=False)
                    
                    if action == "toggle_recording":
                        await self.toggle_recording()
                    elif action == "toggle_pause":
                        await self.toggle_pause()
                    elif action == "emergency_stop":
                        await self.emergency_stop()
                        
                    # Mark task as done
                    self.pending_actions.task_done()
                    
                except queue.Empty:
                    # No more actions to process
                    break
                    
        except Exception as e:
            self.logger.error(f"Error processing action: {e}")
    
    async def toggle_recording(self):
        """Toggle recording on/off."""
        current_state = self.recorder.state
        
        if current_state == MacroState.IDLE:
            # Start recording
            result = self.recorder.start_recording(
                macro_name=self.macro_name,
                description=self.description,
                capture_ui_context=True,
                capture_screenshots=True,
                mouse_move_threshold=50.0,
                keyboard_commit_events=["enter", "tab", "escape"]
            )
            
            if result["success"]:
                print(f"\n🔴 RECORDING STARTED: {self.macro_name}")
                print("   Perform your workflow now...")
            else:
                print(f"\n❌ Failed to start recording: {result.get('error', 'Unknown error')}")
                
        elif current_state == MacroState.RECORDING:
            # Stop recording
            result = self.recorder.stop_recording(save_macro=True, output_format="both")
            
            if result["success"]:
                print(f"\n⏹️  RECORDING STOPPED")
                print(f"   Events recorded: {result.get('events_recorded', 0)}")
                if 'saved_files' in result:
                    print(f"   Files saved:")
                    for file_path in result['saved_files']:
                        print(f"     📁 {file_path}")
                print(f"\n✅ Macro '{self.macro_name}' saved successfully!")
                self.is_running = False
            else:
                print(f"\n❌ Failed to stop recording: {result.get('error', 'Unknown error')}")
    
    async def toggle_pause(self):
        """Toggle pause/resume."""
        current_state = self.recorder.state
        
        if current_state == MacroState.RECORDING:
            result = self.recorder.pause_recording(pause=True)
            if result["success"]:
                print(f"\n⏸️  RECORDING PAUSED")
                print("   Press F10 again to resume...")
        elif current_state == MacroState.PAUSED:
            result = self.recorder.pause_recording(pause=False)
            if result["success"]:
                print(f"\n▶️  RECORDING RESUMED")
                print("   Continue your workflow...")
    
    async def emergency_stop(self):
        """Emergency stop and exit."""
        current_state = self.recorder.state
        
        if current_state in [MacroState.RECORDING, MacroState.PAUSED]:
            result = self.recorder.stop_recording(save_macro=True, output_format="both")
            if result["success"]:
                print(f"\n🛑 EMERGENCY STOP - Recording saved")
                if 'saved_files' in result:
                    for file_path in result['saved_files']:
                        print(f"     📁 {file_path}")
            else:
                print(f"\n🛑 EMERGENCY STOP - Recording may not be saved")
        
        print(f"\n👋 Exiting macro recorder...")
        self.is_running = False
    
    def show_status(self):
        """Show current recording status."""
        status = self.recorder.get_status()
        state = status["state"]
        events = status["events_recorded"]
        
        status_emoji = {
            "idle": "⚪",
            "recording": "🔴",
            "paused": "⏸️",
            "stopped": "⏹️"
        }
        
        print(f"\r{status_emoji.get(state, '❓')} Status: {state.upper()} | Events: {events}", end="", flush=True)
    
    async def run(self):
        """Run the standalone recorder."""
        print(f"\n🚀 Starting macro recorder...")
        print(f"   Press F9 to start recording when ready")
        
        # Start hotkey listener
        self.start_hotkey_listener()
        
        try:
            # Main loop
            while self.is_running:
                # Process any pending hotkey actions
                await self.process_pending_actions()
                
                # Show status
                self.show_status()
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print(f"\n\n⌨️  Keyboard interrupt received")
            await self.emergency_stop()
        
        finally:
            # Cleanup
            if self.hotkey_listener:
                self.hotkey_listener.stop()
            print(f"\n\n✅ Macro recorder stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Record UI macros for MCP UI Explorer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python record_macro.py --name "Login Workflow"
  python record_macro.py --name "File Upload" --description "Upload a file to the website"
  
The recorded macro will be saved in the 'macros' directory and can be played back
using the MCP UI Explorer server's play_macro tool.
        """
    )
    
    parser.add_argument(
        "--name", "-n",
        required=True,
        help="Name for the macro (required)"
    )
    
    parser.add_argument(
        "--description", "-d",
        default="",
        help="Description of what the macro does"
    )
    
    parser.add_argument(
        "--no-ui-context",
        action="store_true",
        help="Disable UI context capture (faster but less reliable playback)"
    )
    
    parser.add_argument(
        "--no-screenshots",
        action="store_true",
        help="Disable screenshot capture (faster recording)"
    )
    
    parser.add_argument(
        "--mouse-threshold",
        type=float,
        default=50.0,
        help="Minimum mouse movement distance to record (default: 50 pixels)"
    )
    
    args = parser.parse_args()
    
    # Validate macro name
    if not args.name.strip():
        print("❌ Error: Macro name cannot be empty")
        sys.exit(1)
    
    # Create and run the recorder
    recorder = StandaloneMacroRecorder(
        macro_name=args.name.strip(),
        description=args.description.strip()
    )
    
    try:
        asyncio.run(recorder.run())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 