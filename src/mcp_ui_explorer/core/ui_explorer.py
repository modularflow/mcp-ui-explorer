"""Main UI Explorer class that coordinates all components."""

from typing import Dict, Any, Optional, Union, List
from datetime import datetime

from ..config import get_settings
from ..utils.logging import get_logger, setup_logging
from ..utils.system import setup_unicode_encoding
from ..models.enums import RegionType, ControlType
from ..services.ui_tars import UITarsService
from ..services.memory import MemoryService
from ..services.verification import VerificationService
from ..core.actions import UIActions
from ..core.tracking import ToolUsageTracker, ActionLogger, StepTracker
from ..hierarchical_ui_explorer import analyze_ui_hierarchy


class UIExplorer:
    """Main UI Explorer class that coordinates all functionality."""
    
    def __init__(self):
        # Set up system configuration
        setup_unicode_encoding()
        
        # Initialize settings and logging
        self.settings = get_settings()
        self.logger = setup_logging()
        
        # Initialize tracking components
        self.tool_usage_tracker = ToolUsageTracker()
        self.action_logger = ActionLogger()
        self.step_tracker = StepTracker()
        
        # Initialize services
        self.ui_tars_service = UITarsService()
        self.memory_service = MemoryService(self.action_logger)
        self.verification_service = VerificationService(self.ui_tars_service)
        
        # Initialize UI actions
        self.ui_actions = UIActions(self.ui_tars_service, self.verification_service)
        
        self.logger.info("UI Explorer initialized successfully")
    
    def _track_and_log(self, tool_name: str, arguments: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Track tool usage and log action, then add metadata to result."""
        # Track tool usage
        usage_stats = self.tool_usage_tracker.track_tool_usage(tool_name)
        
        # Track step progress
        step_progress = self.step_tracker.track_step_progress(tool_name)
        
        # Log action for summarization
        self.action_logger.log_action(tool_name, arguments, result)
        
        # Add metadata to result
        result["tool_usage_stats"] = usage_stats
        result["step_progress"] = step_progress
        
        return result
    
    async def _check_auto_summary(self) -> Optional[Dict[str, Any]]:
        """Check if we need to create an automatic summary."""
        return await self.memory_service.check_and_create_summary()
    
    # UI Action Methods
    
    async def screenshot_ui(
        self,
        region: Optional[Union[RegionType, str]] = None,
        highlight_levels: bool = True,
        output_prefix: str = None,
        min_size: int = 20,
        max_depth: int = 4,
        focus_only: bool = True
    ) -> Dict[str, Any]:
        """Take a screenshot with UI elements highlighted."""
        try:
            image_data, image_path, cursor_position = await self.ui_actions.screenshot_ui(
                region=region,
                highlight_levels=highlight_levels,
                output_prefix=output_prefix,
                min_size=min_size,
                max_depth=max_depth,
                focus_only=focus_only
            )
            
            result = {
                "success": True,
                "image_path": image_path,
                "cursor_position": cursor_position
            }
            
            # Track and add metadata
            result = self._track_and_log("screenshot_ui", locals(), result)
            
            # Check for auto-summary
            auto_summary = await self._check_auto_summary()
            if auto_summary:
                result["auto_summary_created"] = auto_summary
            
            return result
            
        except Exception as e:
            self.logger.error(f"Screenshot failed: {str(e)}")
            result = {"success": False, "error": str(e)}
            return self._track_and_log("screenshot_ui", locals(), result)
    
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
        result = await self.ui_actions.click_ui_element(
            x=x,
            y=y,
            wait_time=wait_time,
            normalized=normalized,
            auto_verify=auto_verify,
            verification_query=verification_query,
            verification_timeout=verification_timeout
        )
        
        # Track and add metadata
        result = self._track_and_log("click_ui_element", locals(), result)
        
        # Check for auto-summary
        auto_summary = await self._check_auto_summary()
        if auto_summary:
            result["auto_summary_created"] = auto_summary
        
        return result
    
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
        """Send keyboard input with optional automatic verification."""
        result = await self.ui_actions.keyboard_input(
            text=text,
            delay=delay,
            interval=interval,
            press_enter=press_enter,
            auto_verify=auto_verify,
            verification_query=verification_query,
            verification_timeout=verification_timeout
        )
        
        # Track and add metadata
        result = self._track_and_log("keyboard_input", locals(), result)
        
        # Check for auto-summary
        auto_summary = await self._check_auto_summary()
        if auto_summary:
            result["auto_summary_created"] = auto_summary
        
        return result
    
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
        result = await self.ui_actions.press_key(
            key=key,
            delay=delay,
            presses=presses,
            interval=interval,
            auto_verify=auto_verify,
            verification_query=verification_query,
            verification_timeout=verification_timeout
        )
        
        # Track and add metadata
        result = self._track_and_log("press_key", locals(), result)
        
        # Check for auto-summary
        auto_summary = await self._check_auto_summary()
        if auto_summary:
            result["auto_summary_created"] = auto_summary
        
        return result
    
    async def hot_key(
        self,
        keys: List[str],
        delay: float = 0.1,
        auto_verify: bool = None,
        verification_query: Optional[str] = None,
        verification_timeout: float = None
    ) -> Dict[str, Any]:
        """Press a keyboard shortcut with optional automatic verification."""
        result = await self.ui_actions.hot_key(
            keys=keys,
            delay=delay,
            auto_verify=auto_verify,
            verification_query=verification_query,
            verification_timeout=verification_timeout
        )
        
        # Track and add metadata
        result = self._track_and_log("hot_key", locals(), result)
        
        # Check for auto-summary
        auto_summary = await self._check_auto_summary()
        if auto_summary:
            result["auto_summary_created"] = auto_summary
        
        return result
    
    async def ui_tars_analyze(
        self,
        image_path: str,
        query: str,
        provider: Optional[str] = None,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Use UI-TARS model to identify coordinates of UI elements."""
        result = await self.ui_tars_service.analyze_image(
            image_path=image_path,
            query=query,
            provider=provider,
            api_url=api_url,
            model_name=model_name
        )
        
        # Track and add metadata
        result = self._track_and_log("ui_tars_analyze", locals(), result)
        
        # Check for auto-summary
        auto_summary = await self._check_auto_summary()
        if auto_summary:
            result["auto_summary_created"] = auto_summary
        
        return result
    
    async def verify_ui_action(
        self,
        action_description: str,
        expected_result: str,
        verification_query: str,
        timeout: float = None,
        comparison_image: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify that a UI action had the expected result."""
        result = await self.verification_service.verify_action(
            action_description=action_description,
            expected_result=expected_result,
            verification_query=verification_query,
            timeout=timeout,
            comparison_image=comparison_image,
            screenshot_function=self.ui_actions.screenshot_ui
        )
        
        # Track and add metadata
        result = self._track_and_log("verify_ui_action", locals(), result)
        
        # Check for auto-summary
        auto_summary = await self._check_auto_summary()
        if auto_summary:
            result["auto_summary_created"] = auto_summary
        
        return result
    
    async def find_elements_near_cursor(
        self,
        max_distance: int = 100,
        control_type: Optional[ControlType] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Find UI elements closest to the current cursor position."""
        try:
            # Get current cursor position
            cursor_pos = await self.ui_actions.get_cursor_position()
            if not cursor_pos["success"]:
                return self._track_and_log("find_elements_near_cursor", locals(), cursor_pos)
                
            cursor_x, cursor_y = cursor_pos["position"]["absolute"]["x"], cursor_pos["position"]["absolute"]["y"]
            
            # Get all UI elements
            import pyautogui
            screen_width, screen_height = pyautogui.size()
            ui_hierarchy = analyze_ui_hierarchy(
                region=(0, 0, screen_width, screen_height),
                max_depth=8,
                focus_only=False,
                min_size=5,
                visible_only=True
            )
            
            # Flatten hierarchy and calculate distances
            elements_with_distance = []
            
            def process_element(element):
                # Skip elements without position
                if 'position' not in element:
                    return
                    
                # Apply control type filter if specified
                if control_type and element['control_type'] != control_type.value:
                    return
                    
                # Calculate center point of element
                pos = element['position']
                if isinstance(pos, dict) and all(k in pos for k in ['left', 'top', 'right', 'bottom']):
                    element_center_x = (pos['left'] + pos['right']) / 2
                    element_center_y = (pos['top'] + pos['bottom']) / 2
                else:
                    return
                
                # Calculate Euclidean distance
                distance = ((element_center_x - cursor_x) ** 2 + (element_center_y - cursor_y) ** 2) ** 0.5
                
                # Add to list if within max_distance
                if distance <= max_distance:
                    from ..utils.coordinates import CoordinateConverter
                    
                    left, top, right, bottom = pos['left'], pos['top'], pos['right'], pos['bottom']
                    center_x = (left + right) / 2
                    center_y = (top + bottom) / 2
                    
                    coordinates = {
                        "absolute": {
                            "left": int(left), "top": int(top), 
                            "right": int(right), "bottom": int(bottom),
                            "center_x": int(center_x), "center_y": int(center_y)
                        },
                        "normalized": {
                            "left": left / screen_width, "top": top / screen_height,
                            "right": right / screen_width, "bottom": bottom / screen_height,
                            "center_x": center_x / screen_width, "center_y": center_y / screen_height
                        }
                    }
                    
                    element_copy = {
                        "control_type": element['control_type'],
                        "text": element['text'],
                        "position": pos,  # Keep original for backward compatibility
                        "coordinates": coordinates,  # New unified format
                        "distance": round(distance, 2),
                        "properties": element['properties']['automation_id'] if 'properties' in element and 'automation_id' in element['properties'] else ""
                    }
                    elements_with_distance.append(element_copy)
                
                # Process children
                if 'children' in element:
                    for child in element['children']:
                        process_element(child)
            
            # Process all root elements
            for element in ui_hierarchy:
                process_element(element)
                
            # Sort by distance and limit results
            elements_with_distance.sort(key=lambda x: x['distance'])
            closest_elements = elements_with_distance[:limit]
            
            result = {
                "success": True,
                "cursor_position": cursor_pos["position"],
                "elements": closest_elements,
                "total_found": len(elements_with_distance),
                "showing": min(len(elements_with_distance), limit)
            }
            
            # Track and add metadata
            result = self._track_and_log("find_elements_near_cursor", locals(), result)
            
            # Check for auto-summary
            auto_summary = await self._check_auto_summary()
            if auto_summary:
                result["auto_summary_created"] = auto_summary
            
            return result
            
        except Exception as e:
            self.logger.error(f"Find elements near cursor failed: {str(e)}")
            result = {"success": False, "error": str(e)}
            return self._track_and_log("find_elements_near_cursor", locals(), result)
    
    # Memory and tracking methods
    
    async def create_memory_summary(self, force_summary: bool = False) -> Dict[str, Any]:
        """Create a memory summary of the current session."""
        result = await self.memory_service.create_summary(force_summary=force_summary)
        
        # Don't log this action to avoid noise, but add usage stats
        usage_stats = self.tool_usage_tracker.track_tool_usage("create_memory_summary")
        result["tool_usage_stats"] = usage_stats
        
        return result
    
    async def document_step(
        self,
        step_description: str,
        mark_previous_complete: bool = False,
        completion_notes: str = ""
    ) -> Dict[str, Any]:
        """Document a planned step for tracking progress."""
        try:
            if mark_previous_complete:
                self.step_tracker.complete_current_step(success=True, notes=completion_notes)
            
            step_info = self.step_tracker.track_step_progress("document_step", step_description)
            
            result = {
                "success": True,
                "message": f"Documented step: {step_description}",
                "step_info": step_info,
                "all_steps": [
                    {
                        "index": step["step_index"],
                        "description": step["description"],
                        "status": step["status"],
                        "attempts": step["attempts"]
                    }
                    for step in self.step_tracker.planned_steps
                ]
            }
            
            # Don't log this action to avoid noise, but add usage stats
            usage_stats = self.tool_usage_tracker.track_tool_usage("document_step")
            result["tool_usage_stats"] = usage_stats
            
            return result
            
        except Exception as e:
            self.logger.error(f"Document step failed: {str(e)}")
            result = {"success": False, "error": str(e)}
            usage_stats = self.tool_usage_tracker.track_tool_usage("document_step")
            result["tool_usage_stats"] = usage_stats
            return result
    
    async def get_step_status(self, show_all_steps: bool = False) -> Dict[str, Any]:
        """Get current step status and progress."""
        try:
            result = self.step_tracker.get_step_status(show_all_steps=show_all_steps)
            
            # Don't log this action to avoid noise, but add usage stats
            usage_stats = self.tool_usage_tracker.track_tool_usage("get_step_status")
            result["tool_usage_stats"] = usage_stats
            
            return result
            
        except Exception as e:
            self.logger.error(f"Get step status failed: {str(e)}")
            result = {"success": False, "error": str(e)}
            usage_stats = self.tool_usage_tracker.track_tool_usage("get_step_status")
            result["tool_usage_stats"] = usage_stats
            return result 