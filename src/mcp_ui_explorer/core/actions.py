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

    async def find_ui_elements(
        self,
        control_type: Optional[str] = None,
        text: Optional[str] = None,
        automation_id: Optional[str] = None,
        class_name: Optional[str] = None,
        focus_only: bool = True,
        visible_only: bool = True,
        max_depth: int = 8,
        min_size: int = 5
    ) -> Dict[str, Any]:
        """Find UI elements using accessibility APIs with various filter criteria."""
        try:
            # Get UI hierarchy with specified filters
            region = None
            if focus_only:
                # Use full screen but only focus window
                screen_width, screen_height = pyautogui.size()
                region = (0, 0, screen_width, screen_height)
            
            ui_hierarchy = analyze_ui_hierarchy(
                region=region,
                max_depth=max_depth,
                focus_only=focus_only,
                min_size=min_size,
                visible_only=visible_only
            )
            
            # Flatten hierarchy and apply filters
            matching_elements = []
            
            def search_element(element, path="", depth=0):
                """Recursively search through element hierarchy."""
                # Check if element matches criteria
                matches = True
                
                # Control type filter
                if control_type and element.get('control_type') != control_type:
                    matches = False
                
                # Text filter (case-insensitive partial match)
                if text and text.lower() not in element.get('text', '').lower():
                    matches = False
                
                # Automation ID filter
                if automation_id:
                    elem_auto_id = element.get('properties', {}).get('automation_id', '')
                    if automation_id.lower() not in elem_auto_id.lower():
                        matches = False
                
                # Class name filter
                if class_name:
                    elem_class = element.get('properties', {}).get('class_name', '')
                    if class_name.lower() not in elem_class.lower():
                        matches = False
                
                if matches:
                    # Create enhanced element info with clickable data
                    element_copy = element.copy()
                    element_copy['hierarchy_path'] = path
                    element_copy['depth'] = depth
                    
                    # Add center coordinates for easy clicking
                    pos = element['position']
                    center_x = (pos['left'] + pos['right']) / 2
                    center_y = (pos['top'] + pos['bottom']) / 2
                    
                    screen_width, screen_height = pyautogui.size()
                    element_copy['click_coordinates'] = {
                        "absolute": {"x": int(center_x), "y": int(center_y)},
                        "normalized": {"x": center_x / screen_width, "y": center_y / screen_height}
                    }
                    
                    matching_elements.append(element_copy)
                
                # Search children
                for i, child in enumerate(element.get('children', [])):
                    child_path = f"{path}.children.{i}" if path else f"{i}"
                    search_element(child, child_path, depth + 1)
            
            # Search all root elements
            for i, element in enumerate(ui_hierarchy):
                search_element(element, str(i), 0)
            
            return {
                "success": True,
                "elements": matching_elements,
                "total_found": len(matching_elements),
                "search_criteria": {
                    "control_type": control_type,
                    "text": text,
                    "automation_id": automation_id,
                    "class_name": class_name,
                    "focus_only": focus_only,
                    "visible_only": visible_only
                }
            }
            
        except Exception as e:
            self.logger.error(f"Find UI elements failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def click_ui_element_by_accessibility(
        self,
        control_type: Optional[str] = None,
        text: Optional[str] = None,
        automation_id: Optional[str] = None,
        class_name: Optional[str] = None,
        element_index: int = 0,
        fallback_to_coordinates: bool = True,
        wait_time: float = None,
        auto_verify: bool = None,
        verification_query: Optional[str] = None,
        verification_timeout: float = None
    ) -> Dict[str, Any]:
        """Click on a UI element using accessibility APIs, with coordinate fallback."""
        wait_time = wait_time or self.settings.ui.default_wait_time
        auto_verify = auto_verify if auto_verify is not None else self.settings.ui.auto_verify
        verification_timeout = verification_timeout or self.settings.ui.default_verification_timeout
        
        try:
            # First, find matching elements
            find_result = await self.find_ui_elements(
                control_type=control_type,
                text=text,
                automation_id=automation_id,
                class_name=class_name,
                focus_only=True,
                visible_only=True
            )
            
            if not find_result["success"]:
                return find_result
            
            if not find_result["elements"]:
                return {
                    "success": False,
                    "error": "No matching elements found",
                    "search_criteria": find_result["search_criteria"]
                }
            
            if element_index >= len(find_result["elements"]):
                return {
                    "success": False,
                    "error": f"Element index {element_index} out of range. Found {len(find_result['elements'])} matching elements.",
                    "available_elements": len(find_result["elements"])
                }
            
            target_element = find_result["elements"][element_index]
            
            # Take a before screenshot if auto-verification is enabled
            before_image_path = None
            if auto_verify:
                try:
                    _, before_image_path, _ = await self.screenshot_ui(
                        output_prefix="before_accessibility_click"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to take before screenshot: {str(e)}")
                    before_image_path = None
            
            # Wait before clicking
            time.sleep(wait_time)
            
            # Try to click using accessibility API first
            accessibility_success = False
            error_msg = ""
            
            try:
                # Attempt to find and click the actual pywinauto element
                from pywinauto import Desktop
                desktop = Desktop(backend="uia")
                
                # Try to find the element using the accessibility API
                found_element = None
                
                # Get windows to search
                if find_result["search_criteria"]["focus_only"]:
                    import win32gui
                    foreground_hwnd = win32gui.GetForegroundWindow()
                    windows = [w for w in desktop.windows() if w.handle == foreground_hwnd and w.is_visible()]
                else:
                    windows = [w for w in desktop.windows() if w.is_visible()]
                
                # Search for the element using hierarchy path or properties
                for window in windows:
                    found_element = self._find_element_in_window(
                        window, target_element, control_type, text, automation_id, class_name
                    )
                    if found_element:
                        break
                
                if found_element:
                    # Try to click the element directly
                    try:
                        found_element.click()
                        accessibility_success = True
                        self.logger.info(f"Successfully clicked element using accessibility API: {target_element['control_type']} '{target_element['text']}'")
                    except Exception as click_error:
                        error_msg = f"Accessibility click failed: {str(click_error)}"
                        self.logger.warning(error_msg)
                else:
                    error_msg = "Could not find element in accessibility tree"
                    self.logger.warning(error_msg)
                    
            except Exception as e:
                error_msg = f"Accessibility API error: {str(e)}"
                self.logger.warning(error_msg)
            
            # Fallback to coordinate clicking if accessibility failed and fallback is enabled
            coordinate_result = None
            if not accessibility_success and fallback_to_coordinates:
                self.logger.info("Falling back to coordinate-based clicking")
                coordinate_result = await self.click_ui_element(
                    x=target_element["click_coordinates"]["absolute"]["x"],
                    y=target_element["click_coordinates"]["absolute"]["y"],
                    wait_time=0,  # Already waited above
                    normalized=False,
                    auto_verify=False,  # We'll handle verification ourselves
                    verification_query=None,
                    verification_timeout=verification_timeout
                )
            
            # Determine overall success
            overall_success = accessibility_success or (coordinate_result and coordinate_result.get("success", False))
            
            # Build result
            result = {
                "success": overall_success,
                "element": target_element,
                "accessibility_click": {
                    "attempted": True,
                    "success": accessibility_success,
                    "error": error_msg if not accessibility_success else None
                },
                "coordinate_fallback": {
                    "attempted": not accessibility_success and fallback_to_coordinates,
                    "success": coordinate_result.get("success", False) if coordinate_result else False,
                    "result": coordinate_result if coordinate_result else None
                },
                "click_method": "accessibility" if accessibility_success else ("coordinates" if coordinate_result and coordinate_result.get("success", False) else "failed"),
                "wait_time": wait_time
            }
            
            if overall_success:
                result["message"] = f"Successfully clicked {target_element['control_type']} '{target_element['text']}' using {result['click_method']} method"
            else:
                result["message"] = f"Failed to click {target_element['control_type']} '{target_element['text']}'"
                if not fallback_to_coordinates:
                    result["message"] += " (coordinate fallback disabled)"
            
            # Perform automatic verification if enabled and we succeeded
            if auto_verify and overall_success:
                try:
                    # Generate verification query if not provided
                    if not verification_query:
                        verification_query = f"UI change or response from clicking {target_element['control_type']} '{target_element['text']}'"
                    
                    # Perform verification
                    verification_result = await self.verification_service.verify_action(
                        action_description=f"Clicked {target_element['control_type']} '{target_element['text']}' using {result['click_method']} method",
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
            
            return result
            
        except Exception as e:
            self.logger.error(f"Click UI element by accessibility failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _find_element_in_window(self, window, target_element, control_type, text, automation_id, class_name):
        """Find a specific element within a window using pywinauto."""
        try:
            def search_recursively(element, depth=0, max_depth=10):
                if depth > max_depth:
                    return None
                
                try:
                    # Check if current element matches
                    element_control_type = element.element_info.control_type if hasattr(element, 'element_info') else ''
                    element_text = ''
                    if hasattr(element, 'window_text') and callable(element.window_text):
                        element_text = element.window_text()
                    
                    element_automation_id = ''
                    element_class_name = ''
                    if hasattr(element, 'element_info'):
                        element_automation_id = getattr(element.element_info, 'automation_id', '')
                        element_class_name = getattr(element.element_info, 'class_name', '')
                    
                    # Check if this element matches our criteria
                    matches = True
                    if control_type and element_control_type != control_type:
                        matches = False
                    if text and text.lower() not in element_text.lower():
                        matches = False
                    if automation_id and automation_id.lower() not in element_automation_id.lower():
                        matches = False
                    if class_name and class_name.lower() not in element_class_name.lower():
                        matches = False
                    
                    if matches:
                        # Additional check: verify position matches roughly
                        try:
                            rect = element.rectangle()
                            target_pos = target_element['position']
                            
                            # Allow some tolerance in position matching (within 10 pixels)
                            if (abs(rect.left - target_pos['left']) <= 10 and
                                abs(rect.top - target_pos['top']) <= 10 and
                                abs(rect.right - target_pos['right']) <= 10 and
                                abs(rect.bottom - target_pos['bottom']) <= 10):
                                return element
                        except:
                            # If we can't get position, still consider it a match
                            return element
                    
                    # Search children
                    if hasattr(element, 'children') and callable(element.children):
                        for child in element.children():
                            result = search_recursively(child, depth + 1, max_depth)
                            if result:
                                return result
                
                except Exception as e:
                    # Element might not be accessible, continue search
                    pass
                
                return None
            
            return search_recursively(window)
            
        except Exception as e:
            self.logger.debug(f"Error searching in window: {str(e)}")
            return None 