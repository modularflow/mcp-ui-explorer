#!/usr/bin/env python3
"""
Standalone Macro Player for MCP UI Explorer

This script allows you to play back recorded macros independently of the MCP server.
Useful for testing recorded workflows.

Usage:
    python play_macro.py --file "macros/My Workflow.json"
    python play_macro.py --file "macros/Login Workflow.json" --speed 2.0
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.mcp_ui_explorer.services.macro_player import MacroPlayer
from src.mcp_ui_explorer.services.ui_tars import UITarsService
from src.mcp_ui_explorer.utils.logging import setup_logging, get_logger
from src.mcp_ui_explorer.hierarchical_ui_explorer import analyze_ui_hierarchy, visualize_ui_hierarchy
import pyautogui


class StandaloneMacroPlayer:
    """Standalone macro player for testing."""
    
    def __init__(self):
        self.logger = setup_logging()
        
        # Initialize UI-TARS service (optional for verification)
        self.ui_tars_service = UITarsService()
        
        # Initialize the macro player
        self.player = MacroPlayer(
            screenshot_function=self.screenshot_ui,
            ui_tars_service=self.ui_tars_service
        )
        
        print(f"\n🎭 Standalone Macro Player")
        print(f"🎮 Ready to play back recorded macros")
    
    async def screenshot_ui(self, **kwargs):
        """Take a screenshot for verification purposes."""
        try:
            # Simple screenshot implementation
            screen_width, screen_height = pyautogui.size()
            region_coords = (0, 0, screen_width, screen_height)
            
            # Analyze UI elements
            ui_hierarchy = analyze_ui_hierarchy(
                region=region_coords,
                max_depth=4,
                focus_only=True,
                min_size=20,
                visible_only=True
            )
            
            # Create visualization
            image_path = visualize_ui_hierarchy(ui_hierarchy, "playback_screenshot", True)
            
            # Load the image and return it
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Return image data, path, and cursor position
            cursor_x, cursor_y = pyautogui.position()
            cursor_info = {
                "success": True,
                "position": {
                    "absolute": {"x": cursor_x, "y": cursor_y},
                    "normalized": {"x": cursor_x / screen_width, "y": cursor_y / screen_height}
                }
            }
            
            return (image_data, image_path, cursor_info)
            
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            raise
    
    async def play_macro_file(
        self,
        macro_path: str,
        speed_multiplier: float = 1.0,
        verify_ui_context: bool = True,
        stop_on_verification_failure: bool = False,
        dry_run: bool = False
    ):
        """Play a macro file."""
        macro_file = Path(macro_path)
        
        if not macro_file.exists():
            print(f"❌ Error: Macro file not found: {macro_path}")
            return False
        
        print(f"\n📂 Loading macro: {macro_file.name}")
        print(f"🎯 Speed multiplier: {speed_multiplier}x")
        print(f"🔍 UI verification: {'Enabled' if verify_ui_context else 'Disabled'}")
        print(f"🛑 Stop on verification failure: {'Yes' if stop_on_verification_failure else 'No'}")
        
        if dry_run:
            print(f"🧪 DRY RUN MODE: No actual actions will be performed")
        
        # Countdown before starting
        print(f"\n⏰ Starting playback in:")
        for i in range(3, 0, -1):
            print(f"   {i}...")
            await asyncio.sleep(1)
        
        print(f"\n🎬 PLAYBACK STARTED!")
        
        try:
            result = await self.player.play_macro(
                macro_path=str(macro_file),
                speed_multiplier=speed_multiplier,
                verify_ui_context=verify_ui_context,
                stop_on_verification_failure=stop_on_verification_failure
            )
            
            if result["success"]:
                print(f"\n✅ PLAYBACK COMPLETED SUCCESSFULLY!")
                print(f"   Events executed: {result.get('events_executed', 0)}")
                print(f"   Total duration: {result.get('total_duration', 0):.2f} seconds")
                
                if result.get('verification_results'):
                    passed = sum(1 for v in result['verification_results'] if v.get('passed', False))
                    total = len(result['verification_results'])
                    print(f"   Verification: {passed}/{total} passed")
                
                return True
            else:
                print(f"\n❌ PLAYBACK FAILED!")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                print(f"   Events executed: {result.get('events_executed', 0)}")
                
                if result.get('failed_event'):
                    failed_event = result['failed_event']
                    print(f"   Failed at event: {failed_event.get('type', 'Unknown')} at {failed_event.get('timestamp', 'Unknown time')}")
                
                return False
                
        except KeyboardInterrupt:
            print(f"\n\n⌨️  Playback interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Playback error: {e}")
            return False


def list_available_macros():
    """List all available macro files."""
    macros_dir = Path("macros")
    
    if not macros_dir.exists():
        print("📁 No macros directory found")
        return []
    
    json_files = list(macros_dir.glob("*.json"))
    
    if not json_files:
        print("📁 No macro files found in macros directory")
        return []
    
    print(f"\n📁 Available macros in {macros_dir}:")
    for i, macro_file in enumerate(json_files, 1):
        print(f"   {i}. {macro_file.name}")
    
    return json_files


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Play back recorded UI macros",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python play_macro.py --file "macros/Login Workflow.json"
  python play_macro.py --file "macros/File Upload.json" --speed 2.0
  python play_macro.py --list
  python play_macro.py --file "macros/Test.json" --no-verify --dry-run
        """
    )
    
    parser.add_argument(
        "--file", "-f",
        help="Path to the macro file to play"
    )
    
    parser.add_argument(
        "--speed", "-s",
        type=float,
        default=1.0,
        help="Speed multiplier for playback (default: 1.0)"
    )
    
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Disable UI context verification (faster but less reliable)"
    )
    
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop playback immediately if verification fails"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually performing actions"
    )
    
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available macro files"
    )
    
    args = parser.parse_args()
    
    # List available macros if requested
    if args.list:
        list_available_macros()
        return
    
    # Validate arguments
    if not args.file:
        print("❌ Error: No macro file specified")
        print("\nUse --list to see available macros or --help for usage information")
        sys.exit(1)
    
    if args.speed <= 0:
        print("❌ Error: Speed multiplier must be positive")
        sys.exit(1)
    
    # Create and run the player
    player = StandaloneMacroPlayer()
    
    try:
        success = asyncio.run(player.play_macro_file(
            macro_path=args.file,
            speed_multiplier=args.speed,
            verify_ui_context=not args.no_verify,
            stop_on_verification_failure=args.stop_on_failure,
            dry_run=args.dry_run
        ))
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 