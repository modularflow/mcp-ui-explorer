"""Macro playback service for replaying recorded macros."""

import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

import pyautogui

from ..models.enums import MacroEventType
from ..utils.logging import get_logger


class MacroPlayer:
    """Service for playing back recorded macros."""
    
    def __init__(self, screenshot_function: Optional[Callable] = None, ui_tars_service=None):
        self.logger = get_logger(__name__)
        self.screenshot_function = screenshot_function
        self.ui_tars_service = ui_tars_service
        
        # Playback state
        self.is_playing = False
        self.current_macro = None
        self.playback_stats = {}
    
    async def play_macro(
        self,
        macro_path: str,
        speed_multiplier: float = 1.0,
        verify_ui_context: bool = True,
        stop_on_verification_failure: bool = True
    ) -> Dict[str, Any]:
        """Play back a recorded macro."""
        try:
            # Load macro file
            macro_data = self._load_macro(macro_path)
            if not macro_data:
                return {
                    "success": False,
                    "error": f"Failed to load macro from {macro_path}"
                }
            
            self.current_macro = macro_data
            self.is_playing = True
            
            # Initialize playback stats
            self.playback_stats = {
                "total_events": len(macro_data.get("events", [])),
                "events_executed": 0,
                "events_skipped": 0,
                "verification_failures": 0,
                "start_time": time.time()
            }
            
            self.logger.info(f"Starting playback of macro: {macro_data.get('name', 'Unknown')}")
            
            # Disable pyautogui failsafe for smooth playback
            original_failsafe = pyautogui.FAILSAFE
            pyautogui.FAILSAFE = False
            
            try:
                # Play back events
                result = await self._execute_events(
                    macro_data.get("events", []),
                    speed_multiplier,
                    verify_ui_context,
                    stop_on_verification_failure
                )
                
                self.playback_stats["end_time"] = time.time()
                self.playback_stats["duration"] = self.playback_stats["end_time"] - self.playback_stats["start_time"]
                
                result.update({
                    "macro_name": macro_data.get("name", "Unknown"),
                    "playback_stats": self.playback_stats
                })
                
                return result
                
            finally:
                # Restore original failsafe setting
                pyautogui.FAILSAFE = original_failsafe
                self.is_playing = False
                
        except Exception as e:
            self.logger.error(f"Failed to play macro: {str(e)}")
            self.is_playing = False
            return {
                "success": False,
                "error": f"Failed to play macro: {str(e)}"
            }
    
    def _load_macro(self, macro_path: str) -> Optional[Dict[str, Any]]:
        """Load macro data from file."""
        try:
            path = Path(macro_path)
            if not path.exists():
                self.logger.error(f"Macro file not found: {macro_path}")
                return None
            
            if path.suffix.lower() == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                self.logger.error(f"Unsupported macro file format: {path.suffix}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to load macro file: {str(e)}")
            return None
    
    async def _execute_events(
        self,
        events: List[Dict[str, Any]],
        speed_multiplier: float,
        verify_ui_context: bool,
        stop_on_verification_failure: bool
    ) -> Dict[str, Any]:
        """Execute the macro events."""
        if not events:
            return {
                "success": True,
                "message": "No events to execute"
            }
        
        start_time = events[0].get("timestamp", 0)
        last_event_time = start_time
        
        for i, event in enumerate(events):
            if not self.is_playing:
                return {
                    "success": False,
                    "message": "Playback was stopped",
                    "events_executed": i
                }
            
            try:
                # Calculate timing delay
                event_time = event.get("timestamp", last_event_time)
                delay = (event_time - last_event_time) / speed_multiplier
                
                if delay > 0.01:  # Only sleep for significant delays
                    await asyncio.sleep(delay)
                
                # Execute the event
                success = await self._execute_event(event, verify_ui_context)
                
                if success:
                    self.playback_stats["events_executed"] += 1
                else:
                    self.playback_stats["events_skipped"] += 1
                    
                    if stop_on_verification_failure:
                        return {
                            "success": False,
                            "message": f"Stopped playback due to verification failure at event {i + 1}",
                            "failed_event": event
                        }
                
                last_event_time = event_time
                
            except Exception as e:
                self.logger.error(f"Failed to execute event {i + 1}: {str(e)}")
                self.playback_stats["events_skipped"] += 1
                
                if stop_on_verification_failure:
                    return {
                        "success": False,
                        "message": f"Failed to execute event {i + 1}: {str(e)}",
                        "failed_event": event
                    }
        
        return {
            "success": True,
            "message": f"Successfully executed {self.playback_stats['events_executed']} events"
        }
    
    async def _execute_event(self, event: Dict[str, Any], verify_ui_context: bool) -> bool:
        """Execute a single macro event."""
        event_type = event.get("event_type")
        data = event.get("data", {})
        
        try:
            if event_type == MacroEventType.MOUSE_CLICK:
                # Verify UI context if enabled
                if verify_ui_context and self._should_verify_ui_context(event):
                    if not await self._verify_ui_context(event):
                        self.logger.warning(f"UI context verification failed for click event")
                        self.playback_stats["verification_failures"] += 1
                        return False
                
                # Execute click
                x, y = data.get("x", 0), data.get("y", 0)
                pyautogui.click(x, y)
                self.logger.debug(f"Executed click at ({x}, {y})")
                
            elif event_type == MacroEventType.KEYBOARD_TYPE:
                # Execute typing
                text = data.get("text", "")
                pyautogui.write(text)
                self.logger.debug(f"Executed typing: '{text}'")
                
            elif event_type == MacroEventType.KEYBOARD_KEY:
                # Execute key press
                key = data.get("key", "")
                if key:
                    pyautogui.press(key)
                    self.logger.debug(f"Executed key press: {key}")
                
            elif event_type == MacroEventType.KEYBOARD_HOTKEY:
                # Execute hotkey combination
                keys = data.get("keys", [])
                if keys:
                    pyautogui.hotkey(*keys)
                    self.logger.debug(f"Executed hotkey: {'+'.join(keys)}")
                
            elif event_type == MacroEventType.MOUSE_SCROLL:
                # Execute scroll event
                x, y = data.get("x", 0), data.get("y", 0)
                dx, dy = data.get("scroll_dx", 0), data.get("scroll_dy", 0)
                pyautogui.scroll(dy, x=x, y=y)
                self.logger.debug(f"Executed scroll at ({x}, {y}) dx={dx}, dy={dy}")
                
            elif event_type == MacroEventType.MOUSE_MOVE:
                # Handle mouse move or legacy scroll events
                if data.get("action") == "scroll":
                    # Legacy scroll event (for backward compatibility)
                    x, y = data.get("x", 0), data.get("y", 0)
                    dx, dy = data.get("scroll_dx", 0), data.get("scroll_dy", 0)
                    pyautogui.scroll(dy, x=x, y=y)
                    self.logger.debug(f"Executed legacy scroll at ({x}, {y}) dx={dx}, dy={dy}")
                else:
                    # Mouse move event
                    x, y = data.get("x", 0), data.get("y", 0)
                    pyautogui.moveTo(x, y)
                    self.logger.debug(f"Executed mouse move to ({x}, {y})")
                
            elif event_type == MacroEventType.WAIT:
                # Wait event
                duration = data.get("duration", 0)
                if duration > 0:
                    await asyncio.sleep(duration)
                    self.logger.debug(f"Executed wait: {duration}s")
                
            elif event_type == MacroEventType.SCREENSHOT:
                # Screenshot events are informational, skip execution
                self.logger.debug(f"Skipped screenshot event: {data.get('action', 'unknown')}")
                
            else:
                self.logger.warning(f"Unknown event type: {event_type}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to execute {event_type} event: {str(e)}")
            return False
    
    def _should_verify_ui_context(self, event: Dict[str, Any]) -> bool:
        """Determine if UI context should be verified for this event."""
        # Only verify for click events that have UI context
        return (
            event.get("event_type") == MacroEventType.MOUSE_CLICK and
            event.get("ui_context") is not None
        )
    
    async def _verify_ui_context(self, event: Dict[str, Any]) -> bool:
        """Verify that the UI context matches the recorded context."""
        try:
            if not self.ui_tars_service or not self.screenshot_function:
                # Can't verify without these services
                return True
            
            ui_context = event.get("ui_context", {})
            closest_element = ui_context.get("closest_element")
            
            if not closest_element:
                return True
            
            # Take a current screenshot
            _, image_path, _ = await self.screenshot_function(output_prefix="verification")
            
            # Use UI-TARS to find the element
            click_data = event.get("data", {})
            x, y = click_data.get("x", 0), click_data.get("y", 0)
            
            # Create a query based on the recorded element
            element_text = closest_element.get("text", "")
            element_type = closest_element.get("control_type", "")
            
            if element_text:
                query = f"{element_type} with text '{element_text}'"
            else:
                query = f"{element_type} element"
            
            # Analyze current UI
            result = await self.ui_tars_service.analyze_ui(
                image_path=image_path,
                query=query
            )
            
            if not result.get("success"):
                return False
            
            # Check if the found coordinates are close to the recorded ones
            found_coords = result.get("coordinates", {}).get("absolute", {})
            found_x = found_coords.get("x", 0)
            found_y = found_coords.get("y", 0)
            
            # Allow some tolerance (50 pixels)
            tolerance = 50
            distance = ((x - found_x) ** 2 + (y - found_y) ** 2) ** 0.5
            
            return distance <= tolerance
            
        except Exception as e:
            self.logger.warning(f"UI context verification failed: {str(e)}")
            return False
    
    def stop_playback(self) -> Dict[str, Any]:
        """Stop the current macro playback."""
        if not self.is_playing:
            return {
                "success": False,
                "message": "No macro is currently playing"
            }
        
        self.is_playing = False
        return {
            "success": True,
            "message": "Macro playback stopped"
        }
    
    def get_playback_status(self) -> Dict[str, Any]:
        """Get current playback status."""
        return {
            "is_playing": self.is_playing,
            "current_macro": self.current_macro.get("name") if self.current_macro else None,
            "playback_stats": self.playback_stats
        } 