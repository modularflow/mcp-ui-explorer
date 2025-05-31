"""UI action implementations for MCP UI Explorer."""

import time
from typing import Dict, Any, List, Optional, Union, Tuple
import pyautogui

from ..config import get_settings
from ..utils.logging import get_logger
from ..utils.coordinates import CoordinateConverter
from ..models.enums import RegionType, ControlType
from ..hierarchical_ui_explorer import (
    get_predefined_regions,
    analyze_ui_hierarchy,
    visualize_ui_hierarchy
)
from ..services.ui_tars import UITarsService
from ..services.verification import VerificationService
from ..services.macro_recorder import MacroRecorder
from ..services.macro_player import MacroPlayer


class UIActions:
    """Core UI action implementations."""
    
    def __init__(self, ui_tars_service: UITarsService, verification_service: VerificationService):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.ui_tars_service = ui_tars_service
        self.verification_service = verification_service
        
        # Initialize macro recorder with screenshot function
        self.macro_recorder = MacroRecorder(screenshot_function=self.screenshot_ui)
        
        # Initialize macro player with screenshot function and UI-TARS service
        self.macro_player = MacroPlayer(
            screenshot_function=self.screenshot_ui,
            ui_tars_service=self.ui_tars_service
        )
    
    async def get_cursor_position(self) -> Dict[str, Any]:
        """Get the current position of the mouse cursor."""
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
            self.logger.error(f"Failed to get cursor position: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get cursor position: {str(e)}"
            }
    
    async def screenshot_ui(
        self,
        region: Optional[Union[RegionType, str]] = None,
        highlight_levels: bool = True,
        output_prefix: str = None,
        min_size: int = 20,
        max_depth: int = 4,
        focus_only: bool = True
    ) -> Tuple[bytes, str, Dict[str, Any]]:
        """Take a screenshot with UI elements highlighted."""
        output_prefix = output_prefix or self.settings.ui.screenshot_prefix
        
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
        
        # Return both the image data and path
        return (image_data, image_path, await self.get_cursor_position())
    
    async def click_ui_element(
        self,
        x: float,
        y: float,
        wait_time: float = None,
        normalized: bool = False,
        auto_verify: bool = None,
        verification_query: Optional[str] = None,
        verification_timeout: float = None
    ) -> Dict[str, Any]:
        """Click at specific coordinates with optional automatic verification."""
        wait_time = wait_time or self.settings.ui.default_wait_time
        auto_verify = auto_verify if auto_verify is not None else self.settings.ui.auto_verify
        verification_timeout = verification_timeout or self.settings.ui.default_verification_timeout
        
        # Convert coordinates
        coord_info = CoordinateConverter.create_coordinate_info(x, y, normalized)
        abs_x = coord_info["coordinates"]["absolute"]["x"]
        abs_y = coord_info["coordinates"]["absolute"]["y"]
        
        # Take a before screenshot if auto-verification is enabled
        before_image_path = None
        if auto_verify:
            try:
                _, before_image_path, _ = await self.screenshot_ui(
                    output_prefix="before_click"
                )
            except Exception as e:
                self.logger.warning(f"Failed to take before screenshot: {str(e)}")
                before_image_path = None
        
        # Wait before clicking
        time.sleep(wait_time)
        
        try:
            pyautogui.click(abs_x, abs_y)
            
            # Base result
            result = {
                "success": True,
                "message": f"Clicked at {coord_info['input']['type']} coordinates ({x}, {y}) -> absolute ({abs_x}, {abs_y})",
                "coordinates": coord_info["coordinates"],
                "wait_time": wait_time
            }
            
            # Perform automatic verification if enabled
            if auto_verify:
                try:
                    # Generate verification query if not provided
                    if not verification_query:
                        verification_query = f"UI change or response from clicking at coordinates ({abs_x}, {abs_y})"
                    
                    # Perform verification
                    verification_result = await self.verification_service.verify_action(
                        action_description=f"Clicked at {coord_info['input']['type']} coordinates ({x}, {y})",
                        expected_result="UI should respond to the click action",
                        verification_query=verification_query,
                        timeout=verification_timeout,
                        comparison_image=before_image_path,
                        screenshot_function=self.screenshot_ui
                    )
                    
                    # Add verification results to the response
                    result["auto_verification"] = {
                        "enabled": True,
                        "verification_passed": verification_result.get("verification_passed", False),
                        "verification_details": verification_result.get("verification_details", {}),
                        "verification_screenshot": verification_result.get("verification_screenshot"),
                        "verification_query": verification_query,
                        "before_screenshot": before_image_path
                    }
                    
                    # Update success status based on verification
                    if not verification_result.get("verification_passed", False):
                        result["message"] += " (WARNING: Auto-verification failed - click may not have had expected effect)"
                    else:
                        result["message"] += " (Auto-verification: SUCCESS)"
                        
                except Exception as e:
                    result["auto_verification"] = {
                        "enabled": True,
                        "verification_passed": False,
                        "error": f"Verification failed: {str(e)}",
                        "verification_query": verification_query,
                        "before_screenshot": before_image_path
                    }
                    result["message"] += f" (Auto-verification error: {str(e)})"
            else:
                result["auto_verification"] = {"enabled": False}
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to click: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to click at coordinates ({x}, {y}): {str(e)}",
                "auto_verification": {"enabled": auto_verify, "verification_passed": False}
            }
    
    async def keyboard_input(
        self,
        text: str,
        delay: float = 0.1,
        interval: float = 0.0,
        press_enter: bool = False,
        auto_verify: bool = None,
        verification_query: Optional[str] = None,
        verification_timeout: float = None
    ) -> Dict[str, Any]:
        """Send keyboard input to the active window with optional automatic verification."""
        auto_verify = auto_verify if auto_verify is not None else self.settings.ui.auto_verify
        verification_timeout = verification_timeout or self.settings.ui.default_verification_timeout
        
        # Take a before screenshot if auto-verification is enabled
        before_image_path = None
        if auto_verify:
            try:
                _, before_image_path, _ = await self.screenshot_ui(
                    output_prefix="before_typing"
                )
            except Exception as e:
                self.logger.warning(f"Failed to take before screenshot: {str(e)}")
                before_image_path = None
        
        # Wait before typing
        time.sleep(delay)
        
        try:
            # Type the text
            pyautogui.write(text, interval=interval)
            
            # Press Enter if requested
            if press_enter:
                pyautogui.press('enter')
            
            # Base result
            result = {
                "success": True,
                "message": f"Typed text: '{text}'" + (" and pressed Enter" if press_enter else ""),
                "text": text,
                "press_enter": press_enter
            }
            
            # Perform automatic verification if enabled
            if auto_verify:
                try:
                    # Generate verification query if not provided
                    if not verification_query:
                        if press_enter:
                            verification_query = f"text '{text}' was entered and form was submitted or action was triggered"
                        else:
                            verification_query = f"text '{text}' appears in the input field or text area"
                    
                    # Perform verification
                    verification_result = await self.verification_service.verify_action(
                        action_description=f"Typed text '{text}'" + (" and pressed Enter" if press_enter else ""),
                        expected_result="Text should appear in the UI or trigger expected action",
                        verification_query=verification_query,
                        timeout=verification_timeout,
                        comparison_image=before_image_path,
                        screenshot_function=self.screenshot_ui
                    )
                    
                    # Add verification results to the response
                    result["auto_verification"] = {
                        "enabled": True,
                        "verification_passed": verification_result.get("verification_passed", False),
                        "verification_details": verification_result.get("verification_details", {}),
                        "verification_screenshot": verification_result.get("verification_screenshot"),
                        "verification_query": verification_query,
                        "before_screenshot": before_image_path
                    }
                    
                    # Update success status based on verification
                    if not verification_result.get("verification_passed", False):
                        result["message"] += " (WARNING: Auto-verification failed - typing may not have had expected effect)"
                    else:
                        result["message"] += " (Auto-verification: SUCCESS)"
                        
                except Exception as e:
                    result["auto_verification"] = {
                        "enabled": True,
                        "verification_passed": False,
                        "error": f"Verification failed: {str(e)}",
                        "verification_query": verification_query,
                        "before_screenshot": before_image_path
                    }
                    result["message"] += f" (Auto-verification error: {str(e)})"
            else:
                result["auto_verification"] = {"enabled": False}
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to type text: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to type text: {str(e)}",
                "auto_verification": {"enabled": auto_verify, "verification_passed": False}
            }
    
    async def press_key(
        self,
        key: str,
        delay: float = 0.1,
        presses: int = 1,
        interval: float = 0.0,
        auto_verify: bool = None,
        verification_query: Optional[str] = None,
        verification_timeout: float = None
    ) -> Dict[str, Any]:
        """Press a specific keyboard key with optional automatic verification."""
        auto_verify = auto_verify if auto_verify is not None else self.settings.ui.auto_verify
        verification_timeout = verification_timeout or self.settings.ui.default_verification_timeout
        
        # Take a before screenshot if auto-verification is enabled
        before_image_path = None
        if auto_verify:
            try:
                _, before_image_path, _ = await self.screenshot_ui(
                    output_prefix="before_keypress"
                )
            except Exception as e:
                self.logger.warning(f"Failed to take before screenshot: {str(e)}")
                before_image_path = None
        
        # Wait before pressing
        time.sleep(delay)
        
        try:
            # Press the key the specified number of times
            pyautogui.press(key, presses=presses, interval=interval)
            
            # Base result
            result = {
                "success": True,
                "message": f"Pressed key '{key}' {presses} time(s)",
                "key": key,
                "presses": presses
            }
            
            # Perform automatic verification if enabled
            if auto_verify:
                try:
                    # Generate verification query if not provided
                    if not verification_query:
                        if key.lower() in ['enter', 'return']:
                            verification_query = "form was submitted or action was triggered by pressing Enter"
                        elif key.lower() == 'tab':
                            verification_query = "focus moved to next element or field"
                        elif key.lower() == 'escape':
                            verification_query = "dialog closed or action was cancelled"
                        elif key.lower() in ['backspace', 'delete']:
                            verification_query = "text was deleted or removed from input field"
                        else:
                            verification_query = f"UI responded to pressing the '{key}' key"
                    
                    # Perform verification
                    verification_result = await self.verification_service.verify_action(
                        action_description=f"Pressed key '{key}' {presses} time(s)",
                        expected_result=f"UI should respond to the '{key}' key press",
                        verification_query=verification_query,
                        timeout=verification_timeout,
                        comparison_image=before_image_path,
                        screenshot_function=self.screenshot_ui
                    )
                    
                    # Add verification results to the response
                    result["auto_verification"] = {
                        "enabled": True,
                        "verification_passed": verification_result.get("verification_passed", False),
                        "verification_details": verification_result.get("verification_details", {}),
                        "verification_screenshot": verification_result.get("verification_screenshot"),
                        "verification_query": verification_query,
                        "before_screenshot": before_image_path
                    }
                    
                    # Update success status based on verification
                    if not verification_result.get("verification_passed", False):
                        result["message"] += " (WARNING: Auto-verification failed - key press may not have had expected effect)"
                    else:
                        result["message"] += " (Auto-verification: SUCCESS)"
                        
                except Exception as e:
                    result["auto_verification"] = {
                        "enabled": True,
                        "verification_passed": False,
                        "error": f"Verification failed: {str(e)}",
                        "verification_query": verification_query,
                        "before_screenshot": before_image_path
                    }
                    result["message"] += f" (Auto-verification error: {str(e)})"
            else:
                result["auto_verification"] = {"enabled": False}
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to press key: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to press key: {str(e)}",
                "auto_verification": {"enabled": auto_verify, "verification_passed": False}
            }
    
    async def hot_key(
        self,
        keys: List[str],
        delay: float = 0.1,
        auto_verify: bool = None,
        verification_query: Optional[str] = None,
        verification_timeout: float = None
    ) -> Dict[str, Any]:
        """Press a keyboard shortcut (multiple keys together) with optional automatic verification."""
        auto_verify = auto_verify if auto_verify is not None else self.settings.ui.auto_verify
        verification_timeout = verification_timeout or self.settings.ui.default_verification_timeout
        
        # Take a before screenshot if auto-verification is enabled
        before_image_path = None
        if auto_verify:
            try:
                _, before_image_path, _ = await self.screenshot_ui(
                    output_prefix="before_hotkey"
                )
            except Exception as e:
                self.logger.warning(f"Failed to take before screenshot: {str(e)}")
                before_image_path = None
        
        # Wait before pressing
        time.sleep(delay)
        
        try:
            # Press the keys together
            pyautogui.hotkey(*keys)
            
            # Format the key combination for the message
            key_combo = "+".join(keys)
            
            # Base result
            result = {
                "success": True,
                "message": f"Pressed keyboard shortcut: {key_combo}",
                "keys": keys
            }
            
            # Perform automatic verification if enabled
            if auto_verify:
                try:
                    # Generate verification query if not provided
                    if not verification_query:
                        key_combo_lower = key_combo.lower()
                        if 'ctrl+c' in key_combo_lower or 'cmd+c' in key_combo_lower:
                            verification_query = "content was copied to clipboard"
                        elif 'ctrl+v' in key_combo_lower or 'cmd+v' in key_combo_lower:
                            verification_query = "content was pasted from clipboard"
                        elif 'ctrl+z' in key_combo_lower or 'cmd+z' in key_combo_lower:
                            verification_query = "last action was undone"
                        elif 'ctrl+s' in key_combo_lower or 'cmd+s' in key_combo_lower:
                            verification_query = "file was saved or save dialog appeared"
                        elif 'ctrl+o' in key_combo_lower or 'cmd+o' in key_combo_lower:
                            verification_query = "open dialog appeared"
                        elif 'alt+tab' in key_combo_lower or 'cmd+tab' in key_combo_lower:
                            verification_query = "application switcher appeared or focus changed"
                        elif 'ctrl+a' in key_combo_lower or 'cmd+a' in key_combo_lower:
                            verification_query = "all content was selected"
                        else:
                            verification_query = f"UI responded to the {key_combo} keyboard shortcut"
                    
                    # Perform verification
                    verification_result = await self.verification_service.verify_action(
                        action_description=f"Pressed keyboard shortcut: {key_combo}",
                        expected_result=f"UI should respond to the {key_combo} shortcut",
                        verification_query=verification_query,
                        timeout=verification_timeout,
                        comparison_image=before_image_path,
                        screenshot_function=self.screenshot_ui
                    )
                    
                    # Add verification results to the response
                    result["auto_verification"] = {
                        "enabled": True,
                        "verification_passed": verification_result.get("verification_passed", False),
                        "verification_details": verification_result.get("verification_details", {}),
                        "verification_screenshot": verification_result.get("verification_screenshot"),
                        "verification_query": verification_query,
                        "before_screenshot": before_image_path
                    }
                    
                    # Update success status based on verification
                    if not verification_result.get("verification_passed", False):
                        result["message"] += " (WARNING: Auto-verification failed - hotkey may not have had expected effect)"
                    else:
                        result["message"] += " (Auto-verification: SUCCESS)"
                        
                except Exception as e:
                    result["auto_verification"] = {
                        "enabled": True,
                        "verification_passed": False,
                        "error": f"Verification failed: {str(e)}",
                        "verification_query": verification_query,
                        "before_screenshot": before_image_path
                    }
                    result["message"] += f" (Auto-verification error: {str(e)})"
            else:
                result["auto_verification"] = {"enabled": False}
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to press hotkey: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to press hotkey: {str(e)}",
                "auto_verification": {"enabled": auto_verify, "verification_passed": False}
            }
    
    # Macro recording methods
    
    async def start_macro_recording(
        self,
        macro_name: str,
        description: Optional[str] = None,
        capture_ui_context: bool = True,
        capture_screenshots: bool = True,
        mouse_move_threshold: float = 50.0,
        keyboard_commit_events: List[str] = None
    ) -> Dict[str, Any]:
        """Start recording a new macro."""
        try:
            result = self.macro_recorder.start_recording(
                macro_name=macro_name,
                description=description,
                capture_ui_context=capture_ui_context,
                capture_screenshots=capture_screenshots,
                mouse_move_threshold=mouse_move_threshold,
                keyboard_commit_events=keyboard_commit_events
            )
            
            if result["success"]:
                self.logger.info(f"Started macro recording: {macro_name}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to start macro recording: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to start macro recording: {str(e)}"
            }
    
    async def stop_macro_recording(
        self,
        save_macro: bool = True,
        output_format: str = "both"
    ) -> Dict[str, Any]:
        """Stop recording and optionally save the macro."""
        try:
            result = self.macro_recorder.stop_recording(
                save_macro=save_macro,
                output_format=output_format
            )
            
            if result["success"]:
                self.logger.info(f"Stopped macro recording: {result.get('macro_name', 'Unknown')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to stop macro recording: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to stop macro recording: {str(e)}"
            }
    
    async def pause_macro_recording(self, pause: bool = True) -> Dict[str, Any]:
        """Pause or resume macro recording."""
        try:
            result = self.macro_recorder.pause_recording(pause=pause)
            
            action = "paused" if pause else "resumed"
            if result["success"]:
                self.logger.info(f"Macro recording {action}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to pause/resume macro recording: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to pause/resume macro recording: {str(e)}"
            }
    
    async def get_macro_status(self, include_events: bool = False) -> Dict[str, Any]:
        """Get current macro recording status."""
        try:
            status = self.macro_recorder.get_status(include_events=include_events)
            
            return {
                "success": True,
                **status
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get macro status: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get macro status: {str(e)}"
            }

    async def play_macro(
        self,
        macro_path: str,
        speed_multiplier: float = 1.0,
        verify_ui_context: bool = True,
        stop_on_verification_failure: bool = True
    ) -> Dict[str, Any]:
        """Play a recorded macro."""
        try:
            result = await self.macro_player.play_macro(
                macro_path=macro_path,
                speed_multiplier=speed_multiplier,
                verify_ui_context=verify_ui_context,
                stop_on_verification_failure=stop_on_verification_failure
            )
            
            if result["success"]:
                self.logger.info(f"Played macro from: {macro_path}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to play macro: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to play macro: {str(e)}"
            } 