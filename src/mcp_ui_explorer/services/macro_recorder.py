"""Macro recording service for capturing user interactions with UI context."""

import json
import time
import threading
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict

from pynput import mouse, keyboard
import pyautogui
from PIL import Image, ImageDraw

from ..models.enums import MacroState, MacroEventType
from ..utils.logging import get_logger
from ..hierarchical_ui_explorer import analyze_ui_hierarchy, visualize_ui_hierarchy


@dataclass
class MacroEvent:
    """Represents a single event in a macro recording."""
    
    event_type: MacroEventType
    timestamp: float
    data: Dict[str, Any]
    ui_context: Optional[Dict[str, Any]] = None
    screenshot_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class MacroRecorder:
    """Service for recording user interactions as macros."""
    
    def __init__(self, screenshot_function: Optional[Callable] = None):
        self.logger = get_logger(__name__)
        self.screenshot_function = screenshot_function
        
        # Recording state
        self.state = MacroState.IDLE
        self.current_macro: Optional[Dict[str, Any]] = None
        self.events: List[MacroEvent] = []
        
        # Event listeners
        self.mouse_listener: Optional[mouse.Listener] = None
        self.keyboard_listener: Optional[keyboard.Listener] = None
        
        # Recording configuration
        self.capture_ui_context = True
        self.capture_screenshots = True
        self.mouse_move_threshold = 50.0
        self.keyboard_commit_events = ["enter", "tab", "escape"]
        
        # State tracking
        self.last_mouse_position = (0, 0)
        self.current_text_buffer = ""
        self.last_ui_context_time = 0
        self.ui_context_cache_duration = 2.0  # seconds
        
        # Package organization
        self.macro_package_dir: Optional[Path] = None
        self.screenshot_counter = 0
        
        # Thread safety
        self.lock = threading.Lock()
    
    def start_recording(
        self,
        macro_name: str,
        description: Optional[str] = None,
        capture_ui_context: bool = True,
        capture_screenshots: bool = True,
        mouse_move_threshold: float = 50.0,
        keyboard_commit_events: List[str] = None
    ) -> Dict[str, Any]:
        """Start recording a new macro."""
        with self.lock:
            if self.state == MacroState.RECORDING:
                return {
                    "success": False,
                    "error": "Already recording a macro. Stop current recording first."
                }
            
            # Initialize recording
            self.current_macro = {
                "name": macro_name,
                "description": description or "",
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            self.events = []
            self.capture_ui_context = capture_ui_context
            self.capture_screenshots = capture_screenshots
            self.mouse_move_threshold = mouse_move_threshold
            self.keyboard_commit_events = keyboard_commit_events or ["enter", "tab", "escape"]
            
            # Reset state tracking
            self.current_text_buffer = ""
            self.last_mouse_position = pyautogui.position()
            self.last_ui_context_time = 0
            self.screenshot_counter = 0
            
            # Initialize package directory for screenshots
            if self.capture_screenshots:
                safe_name = "".join(c for c in macro_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                package_name = f"{safe_name}_{timestamp}"
                
                self.macro_package_dir = Path("macros") / package_name
                self.macro_package_dir.mkdir(parents=True, exist_ok=True)
                (self.macro_package_dir / "screenshots").mkdir(exist_ok=True)
            
            # Start event listeners
            self._start_listeners()
            
            self.state = MacroState.RECORDING
            
            # Record initial state
            self._record_initial_state()
            
            self.logger.info(f"Started recording macro: {macro_name}")
            
            return {
                "success": True,
                "message": f"Started recording macro '{macro_name}'",
                "macro_name": macro_name,
                "state": self.state.value
            }
    
    def stop_recording(self, save_macro: bool = True, output_format: str = "both") -> Dict[str, Any]:
        """Stop recording and optionally save the macro."""
        with self.lock:
            if self.state != MacroState.RECORDING:
                return {
                    "success": False,
                    "error": "No active recording to stop."
                }
            
            # Stop listeners
            self._stop_listeners()
            
            # Commit any pending text
            self._commit_text_buffer()
            
            # Record final state
            self._record_final_state()
            
            self.state = MacroState.STOPPED
            
            result = {
                "success": True,
                "message": f"Stopped recording macro '{self.current_macro['name']}'",
                "macro_name": self.current_macro["name"],
                "events_recorded": len(self.events),
                "state": self.state.value
            }
            
            if save_macro:
                save_result = self._save_macro(output_format)
                result.update(save_result)
            
            self.logger.info(f"Stopped recording macro: {self.current_macro['name']} ({len(self.events)} events)")
            
            return result
    
    def pause_recording(self, pause: bool = True) -> Dict[str, Any]:
        """Pause or resume recording."""
        with self.lock:
            if self.state not in [MacroState.RECORDING, MacroState.PAUSED]:
                return {
                    "success": False,
                    "error": "No active recording to pause/resume."
                }
            
            if pause and self.state == MacroState.RECORDING:
                self._stop_listeners()
                self.state = MacroState.PAUSED
                action = "paused"
            elif not pause and self.state == MacroState.PAUSED:
                self._start_listeners()
                self.state = MacroState.RECORDING
                action = "resumed"
            else:
                return {
                    "success": False,
                    "error": f"Cannot {'pause' if pause else 'resume'} recording in current state: {self.state.value}"
                }
            
            self.logger.info(f"Recording {action}: {self.current_macro['name']}")
            
            return {
                "success": True,
                "message": f"Recording {action}",
                "state": self.state.value
            }
    
    def get_status(self, include_events: bool = False) -> Dict[str, Any]:
        """Get current recording status."""
        with self.lock:
            status = {
                "state": self.state.value,
                "events_recorded": len(self.events),
                "current_macro": self.current_macro
            }
            
            if include_events:
                status["events"] = [event.to_dict() for event in self.events]
            
            return status
    
    def _start_listeners(self):
        """Start mouse and keyboard event listeners."""
        try:
            # Mouse listener
            self.mouse_listener = mouse.Listener(
                on_click=self._on_mouse_click,
                on_move=self._on_mouse_move,
                on_scroll=self._on_mouse_scroll
            )
            self.mouse_listener.start()
            
            # Keyboard listener
            self.keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self.keyboard_listener.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start event listeners: {str(e)}")
            raise
    
    def _stop_listeners(self):
        """Stop event listeners."""
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
    
    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        """Handle mouse click events."""
        if self.state != MacroState.RECORDING:
            return
        
        # Only record click press events (not release)
        if not pressed:
            return
        
        # Commit any pending text before mouse action
        self._commit_text_buffer()
        
        # Get UI element at click location using direct detection
        ui_element = None
        if self.capture_ui_context:
            ui_element = self._get_element_at_point(x, y)
        
        # Take focused screenshot if enabled
        screenshot_path = None
        if self.capture_screenshots:
            action_data = {"x": x, "y": y, "button": button.name}
            screenshot_path = self._take_screenshot("click", action_data)
        
        event = MacroEvent(
            event_type=MacroEventType.MOUSE_CLICK,
            timestamp=time.time(),
            data={
                "x": x,
                "y": y,
                "button": button.name,
                "screen_size": pyautogui.size()
            },
            ui_context=ui_element,  # Store the detected UI element
            screenshot_path=screenshot_path
        )
        
        self.events.append(event)
        
        # Enhanced logging with UI element info
        if ui_element:
            self.logger.debug(f"Recorded mouse click at ({x}, {y}) with {button.name} on {ui_element.get('control_type', 'Unknown')} '{ui_element.get('text', '')}'")
        else:
            self.logger.debug(f"Recorded mouse click at ({x}, {y}) with {button.name}")
    
    def _on_mouse_move(self, x: int, y: int):
        """Handle mouse move events."""
        if self.state != MacroState.RECORDING:
            return
        
        # Update last mouse position for context, but don't record movement events
        # We only want to record the mouse position when an actual action occurs (like a click)
        self.last_mouse_position = (x, y)
        # No longer recording mouse movements as separate events
    
    def _on_mouse_scroll(self, x: int, y: int, dx: int, dy: int):
        """Handle mouse scroll events."""
        if self.state != MacroState.RECORDING:
            return
        
        # Record scroll as an action (not a movement)
        event = MacroEvent(
            event_type=MacroEventType.MOUSE_SCROLL,  # Changed from MOUSE_MOVE
            timestamp=time.time(),
            data={
                "x": x,
                "y": y,
                "scroll_dx": dx,
                "scroll_dy": dy,
                "action": "scroll",
                "screen_size": pyautogui.size()
            }
        )
        
        self.events.append(event)
        self.logger.debug(f"Recorded mouse scroll at ({x}, {y}) dx={dx}, dy={dy}")
    
    def _on_key_press(self, key):
        """Handle key press events."""
        if self.state != MacroState.RECORDING:
            return
        
        try:
            # Handle special keys
            if hasattr(key, 'name'):
                key_name = key.name
                
                # Skip F9 key presses (recording control)
                if key_name.lower() == 'f9':
                    self.logger.debug("Ignoring F9 key press (recording control)")
                    return
                
                # Check if this is a commit event
                if key_name.lower() in self.keyboard_commit_events:
                    self._commit_text_buffer()
                    
                    # Record the key press
                    event = MacroEvent(
                        event_type=MacroEventType.KEYBOARD_KEY,
                        timestamp=time.time(),
                        data={
                            "key": key_name,
                            "special": True
                        }
                    )
                    self.events.append(event)
                    self.logger.debug(f"Recorded special key: {key_name}")
                
                # Handle backspace and delete - modify text buffer instead of recording
                elif key_name.lower() in ['backspace', 'delete']:
                    if key_name.lower() == 'backspace' and self.current_text_buffer:
                        # Remove last character from buffer
                        self.current_text_buffer = self.current_text_buffer[:-1]
                        self.logger.debug(f"Backspace: removed character (buffer: '{self.current_text_buffer}')")
                    elif key_name.lower() == 'delete':
                        # For delete, we can't easily handle cursor position in buffer, so just log it
                        self.logger.debug(f"Delete key pressed (buffer unchanged: '{self.current_text_buffer}')")
                    # Don't record backspace/delete as separate events
                
                # Handle modifier keys and other special keys
                elif key_name in ['ctrl_l', 'ctrl_r', 'alt_l', 'alt_r', 'shift', 'shift_r', 'cmd']:
                    # Don't record modifier keys alone, they'll be captured in hotkey combinations
                    pass
                else:
                    # Other special keys (arrows, function keys, etc.) - only record if they're not editing keys
                    if key_name.lower() not in ['left', 'right', 'up', 'down', 'home', 'end', 'page_up', 'page_down']:
                        event = MacroEvent(
                            event_type=MacroEventType.KEYBOARD_KEY,
                            timestamp=time.time(),
                            data={
                                "key": key_name,
                                "special": True
                            }
                        )
                        self.events.append(event)
                        self.logger.debug(f"Recorded special key: {key_name}")
                    else:
                        self.logger.debug(f"Ignored navigation key: {key_name}")
            
            # Handle regular character keys
            elif hasattr(key, 'char') and key.char:
                # Add to text buffer
                self.current_text_buffer += key.char
                self.logger.debug(f"Added to text buffer: '{key.char}' (buffer: '{self.current_text_buffer}')")
            
        except Exception as e:
            self.logger.error(f"Error handling key press: {str(e)}")
    
    def _on_key_release(self, key):
        """Handle key release events."""
        # Currently not recording key releases, but could be extended
        pass
    
    def _commit_text_buffer(self):
        """Commit the current text buffer as a keyboard event."""
        if not self.current_text_buffer.strip():
            return
        
        # Get current cursor position for context
        cursor_pos = pyautogui.position()
        
        # Get UI element for text input using direct detection
        ui_element = None
        if self.capture_ui_context:
            ui_element = self._get_element_at_point(cursor_pos[0], cursor_pos[1])
        
        # Take focused screenshot for text input
        screenshot_path = None
        if self.capture_screenshots:
            action_data = {"x": cursor_pos[0], "y": cursor_pos[1], "text": self.current_text_buffer}
            screenshot_path = self._take_screenshot("type", action_data)
        
        event = MacroEvent(
            event_type=MacroEventType.KEYBOARD_TYPE,
            timestamp=time.time(),
            data={
                "text": self.current_text_buffer,
                "cursor_position": cursor_pos
            },
            ui_context=ui_element,  # Store the detected UI element
            screenshot_path=screenshot_path
        )
        
        self.events.append(event)
        
        # Enhanced logging with UI element info
        if ui_element:
            self.logger.debug(f"Committed text: '{self.current_text_buffer}' to {ui_element.get('control_type', 'Unknown')} '{ui_element.get('text', '')}'")
        else:
            self.logger.debug(f"Committed text: '{self.current_text_buffer}'")
        
        # Clear the buffer
        self.current_text_buffer = ""
    
    def _get_element_at_point(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        """Get the UI element directly at the specified coordinates using accessibility APIs."""
        try:
            # Use the new accessibility-based element finding
            from ..hierarchical_ui_explorer import analyze_ui_hierarchy
            
            # Analyze a small region around the click point using accessibility APIs
            region_size = 200
            region = (
                max(0, x - region_size // 2),
                max(0, y - region_size // 2), 
                min(pyautogui.size()[0], x + region_size // 2),
                min(pyautogui.size()[1], y + region_size // 2)
            )
            
            self.logger.debug(f"Analyzing UI at point ({x}, {y}) with region {region}")
            
            # Get UI hierarchy using the accessibility-first approach
            ui_hierarchy = analyze_ui_hierarchy(
                region=region,
                max_depth=8,
                focus_only=True,
                min_size=5,
                visible_only=True
            )
            
            if ui_hierarchy:
                # Find the element that contains our click point
                element = self._find_closest_element(ui_hierarchy, x, y)
                if element:
                    # Add detection method metadata
                    element["properties"] = element.get("properties", {})
                    element["properties"]["detection_method"] = "accessibility_hierarchy"
                    element["distance"] = 0  # Point is inside element
                    
                    self.logger.debug(f"Found element via accessibility: {element.get('control_type')} '{element.get('text')}'")
                    return element
            
            # Fallback: try to find any nearby elements if no direct hit
            self.logger.debug(f"No element found at exact point, searching nearby")
            closest_element = self._find_closest_element(ui_hierarchy, x, y)
            if closest_element:
                closest_element["properties"] = closest_element.get("properties", {})
                closest_element["properties"]["detection_method"] = "accessibility_nearby"
                
                self.logger.debug(f"Found nearby element via accessibility: {closest_element.get('control_type')} '{closest_element.get('text')}' distance={closest_element.get('distance', 0)}")
                return closest_element
            
            # Final fallback: basic window detection
            self.logger.debug(f"Accessibility detection failed, falling back to basic window detection")
            return self._get_basic_window_info(x, y)
                
        except Exception as e:
            self.logger.warning(f"Failed to get element at point ({x}, {y}): {str(e)}")
            return self._get_basic_window_info(x, y)
    
    def _find_closest_element(self, ui_hierarchy: List[Dict], x: int, y: int) -> Optional[Dict[str, Any]]:
        """Find the UI element that contains the specified position, or the closest one if none contain it."""
        containing_elements = []
        closest_element = None
        min_distance = float('inf')
        
        def check_element(element):
            nonlocal closest_element, min_distance
            
            if 'position' not in element:
                return
            
            pos = element['position']
            left = pos.get('left', 0)
            top = pos.get('top', 0)
            right = pos.get('right', 0)
            bottom = pos.get('bottom', 0)
            
            # Check if the point is within the element bounds
            if left <= x <= right and top <= y <= bottom:
                containing_elements.append({
                    "control_type": element.get('control_type', 'Unknown'),
                    "text": element.get('text', ''),
                    "position": pos,
                    "distance": 0,  # Point is inside, so distance is 0
                    "properties": element.get('properties', {}),
                    "area": (right - left) * (bottom - top)  # For sorting by size
                })
            else:
                # Calculate distance to the center of the element
                center_x = (left + right) / 2
                center_y = (top + bottom) / 2
                distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                
                # Only consider reasonably close elements (within 100 pixels)
                if distance < min_distance and distance <= 100:
                    min_distance = distance
                    closest_element = {
                        "control_type": element.get('control_type', 'Unknown'),
                        "text": element.get('text', ''),
                        "position": pos,
                        "distance": distance,
                        "properties": element.get('properties', {})
                    }
            
            # Check children
            if 'children' in element:
                for child in element['children']:
                    check_element(child)
        
        for element in ui_hierarchy:
            check_element(element)
        
        # If we found elements that contain the point, return the smallest one
        # (most specific/deepest in the hierarchy)
        if containing_elements:
            # Sort by area (smallest first) to get the most specific element
            containing_elements.sort(key=lambda e: e['area'])
            return containing_elements[0]
        
        # If no element contains the point, return the closest one
        return closest_element
    
    def _get_basic_window_info(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        """Get basic window information as a fallback."""
        try:
            import win32gui
            
            hwnd = win32gui.WindowFromPoint((x, y))
            if hwnd:
                window_title = win32gui.GetWindowText(hwnd)
                window_class = win32gui.GetClassName(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                
                # Simple application detection
                app_name = window_title
                if window_class in ['MSTaskSwWClass', 'Shell_TrayWnd']:
                    app_name = "Taskbar Button"
                elif "firefox" in window_title.lower():
                    app_name = "Firefox"
                elif "chrome" in window_title.lower():
                    app_name = "Chrome"
                elif "edge" in window_title.lower():
                    app_name = "Microsoft Edge"
                elif window_title:
                    app_name = window_title
                else:
                    app_name = f"Window ({window_class})"
                
                return {
                    "control_type": "Window",
                    "text": app_name,
                    "position": {
                        "left": rect[0],
                        "top": rect[1],
                        "right": rect[2],
                        "bottom": rect[3]
                    },
                    "distance": 0,
                    "properties": {
                        "class_name": window_class,
                        "handle": hwnd,
                        "detection_method": "basic_window_fallback"
                    }
                }
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Basic window info failed: {e}")
            return None
    
    def _take_screenshot(self, prefix: str = "macro", action_data: Optional[Dict] = None) -> Optional[str]:
        """Take a full-screen screenshot with action indicators."""
        try:
            if not self.macro_package_dir:
                return None
                
            self.screenshot_counter += 1
            screenshot_filename = f"{self.screenshot_counter:03d}_{prefix}.png"
            screenshot_path = self.macro_package_dir / "screenshots" / screenshot_filename
            
            # Ensure screenshots directory exists
            screenshot_path.parent.mkdir(exist_ok=True)
            
            # Always take full screen screenshot with action indicators
            return self._create_full_screen_screenshot_with_indicators(screenshot_path, prefix, action_data)
                
        except Exception as e:
            self.logger.warning(f"Failed to take screenshot: {str(e)}")
            return None
    
    def _create_full_screen_screenshot_with_indicators(self, output_path: Path, action_type: str, action_data: Optional[Dict] = None) -> str:
        """Create a full-screen screenshot with visual indicators for the action."""
        try:
            # Take full screen screenshot
            screenshot = pyautogui.screenshot()
            
            # Convert to RGBA for overlay effects
            enhanced = screenshot.convert("RGBA")
            overlay = Image.new("RGBA", enhanced.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Add action indicators if we have action data
            if action_data and action_data.get("x") is not None and action_data.get("y") is not None:
                x, y = action_data["x"], action_data["y"]
                
                # Add action indicator based on action type
                if action_type == "click":
                    # Red circle for click with white border
                    draw.ellipse([x - 15, y - 15, x + 15, y + 15], 
                               fill=(255, 0, 0, 220), outline=(255, 255, 255, 255), width=3)
                    # Smaller inner circle for precise location
                    draw.ellipse([x - 5, y - 5, x + 5, y + 5], 
                               fill=(255, 255, 255, 255))
                    
                elif action_type == "type":
                    # Blue crosshair for text input
                    draw.line([x - 20, y, x + 20, y], 
                             fill=(0, 100, 255, 255), width=3)
                    draw.line([x, y - 20, x, y + 20], 
                             fill=(0, 100, 255, 255), width=3)
                    # Small circle at center
                    draw.ellipse([x - 3, y - 3, x + 3, y + 3], 
                               fill=(0, 100, 255, 255))
                    
                elif action_type in ["initial_state", "final_state"]:
                    # Yellow marker for state screenshots
                    draw.ellipse([x - 12, y - 12, x + 12, y + 12], 
                               fill=(255, 255, 0, 180), outline=(255, 255, 255, 255), width=2)
                
                # Add coordinate annotation
                self._add_coordinate_annotation(draw, x, y, enhanced.size, action_type)
            
            # Add screenshot metadata
            self._add_screenshot_metadata(draw, enhanced.size, action_type, action_data)
            
            # Combine original image with overlay
            final_image = Image.alpha_composite(enhanced, overlay)
            final_image.save(str(output_path))
            
            return str(output_path.relative_to(self.macro_package_dir))
            
        except Exception as e:
            self.logger.warning(f"Failed to create full screen screenshot: {str(e)}")
            return None
    
    def _add_coordinate_annotation(self, draw: ImageDraw.Draw, x: int, y: int, image_size: tuple, action_type: str):
        """Add coordinate annotation to the screenshot."""
        try:
            # Try to use a better font if available
            try:
                from PIL import ImageFont
                font_size = 14
                try:
                    # Windows
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    try:
                        # macOS
                        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
                    except:
                        try:
                            # Linux
                            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                        except:
                            font = ImageFont.load_default()
            except ImportError:
                font = None
            
            # Coordinate text
            coord_text = f"({x}, {y})"
            
            # Choose colors based on action type
            if action_type == "click":
                text_color = (255, 255, 255, 255)  # White text
                bg_color = (255, 0, 0, 200)        # Red background
            elif action_type == "type":
                text_color = (255, 255, 255, 255)  # White text
                bg_color = (0, 100, 255, 200)      # Blue background
            else:
                text_color = (255, 255, 255, 255)  # White text
                bg_color = (128, 128, 128, 200)    # Gray background
            
            # Get text dimensions
            if font:
                bbox = draw.textbbox((0, 0), coord_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = len(coord_text) * 8
                text_height = 14
            
            # Position the label near the action point but keep it visible
            padding = 6
            label_width = text_width + (padding * 2)
            label_height = text_height + (padding * 2)
            
            # Try to position above and to the right of the action point
            label_x = x + 25
            label_y = y - label_height - 25
            
            # Adjust if label would go outside the image
            if label_x + label_width > image_size[0]:
                label_x = x - label_width - 25  # Move to left of action point
            if label_y < 0:
                label_y = y + 25  # Move below the action point
            if label_x < 0:
                label_x = 10  # Move to left edge with margin
            if label_y + label_height > image_size[1]:
                label_y = image_size[1] - label_height - 10  # Move up from bottom
            
            # Draw background rectangle
            draw.rectangle([label_x, label_y, label_x + label_width, label_y + label_height], 
                         fill=bg_color, outline=(255, 255, 255, 255), width=1)
            
            # Draw the text
            text_x = label_x + padding
            text_y = label_y + padding
            
            if font:
                draw.text((text_x, text_y), coord_text, fill=text_color, font=font)
            else:
                draw.text((text_x, text_y), coord_text, fill=text_color)
            
            # Draw a line connecting the label to the action point (if not too close)
            distance = ((label_x + label_width//2 - x)**2 + (label_y + label_height//2 - y)**2)**0.5
            if distance > 30:
                # Draw a thin line from label to action point
                line_start_x = label_x + label_width//2
                line_start_y = label_y + label_height//2
                if label_y < y:  # Label is above action point
                    line_start_y = label_y + label_height
                elif label_y > y:  # Label is below action point
                    line_start_y = label_y
                
                draw.line([line_start_x, line_start_y, x, y], 
                         fill=(255, 255, 255, 180), width=1)
                
        except Exception as e:
            self.logger.warning(f"Failed to add coordinate annotation: {str(e)}")
    
    def _add_screenshot_metadata(self, draw: ImageDraw.Draw, image_size: tuple, action_type: str, action_data: Optional[Dict]):
        """Add metadata information to the screenshot."""
        try:
            # Try to get a font
            try:
                from PIL import ImageFont
                try:
                    font = ImageFont.truetype("arial.ttf", 12)
                except:
                    font = ImageFont.load_default()
            except ImportError:
                font = None
            
            # Create metadata text
            metadata_lines = []
            
            # Add timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            metadata_lines.append(f"Captured: {timestamp}")
            
            # Add action information
            if action_type == "click":
                metadata_lines.append(f"Action: Mouse Click")
                if action_data and action_data.get("button"):
                    metadata_lines.append(f"Button: {action_data.get('button', 'Unknown')}")
            elif action_type == "type":
                metadata_lines.append(f"Action: Keyboard Input")
                if action_data and action_data.get("text"):
                    text = action_data.get("text", "")
                    if len(text) > 30:
                        text = text[:27] + "..."
                    metadata_lines.append(f"Text: '{text}'")
            elif action_type == "initial_state":
                metadata_lines.append(f"Action: Recording Started")
            elif action_type == "final_state":
                metadata_lines.append(f"Action: Recording Ended")
            else:
                metadata_lines.append(f"Action: {action_type.title()}")
            
            # Add screen resolution
            metadata_lines.append(f"Resolution: {image_size[0]}x{image_size[1]}")
            
            # Position metadata in bottom-left corner
            padding = 10
            line_height = 16
            
            # Calculate total height needed
            total_height = len(metadata_lines) * line_height + padding * 2
            max_width = 0
            
            # Calculate maximum width needed
            for line in metadata_lines:
                if font:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    width = bbox[2] - bbox[0]
                else:
                    width = len(line) * 7
                max_width = max(max_width, width)
            
            total_width = max_width + padding * 2
            
            # Draw semi-transparent background
            bg_x = padding
            bg_y = image_size[1] - total_height - padding
            draw.rectangle([bg_x, bg_y, bg_x + total_width, bg_y + total_height], 
                         fill=(0, 0, 0, 160), outline=(255, 255, 255, 100))
            
            # Draw each line of metadata
            for i, line in enumerate(metadata_lines):
                text_x = bg_x + padding
                text_y = bg_y + padding + (i * line_height)
                
                if font:
                    draw.text((text_x, text_y), line, fill=(255, 255, 255, 255), font=font)
                else:
                    draw.text((text_x, text_y), line, fill=(255, 255, 255, 255))
                    
        except Exception as e:
            self.logger.warning(f"Failed to add screenshot metadata: {str(e)}")
    
    def _record_initial_state(self):
        """Record the initial state when starting recording."""
        screenshot_path = None
        if self.capture_screenshots:
            screenshot_path = self._take_screenshot("initial_state")
        
        cursor_pos = pyautogui.position()
        ui_context = None
        if self.capture_ui_context:
            ui_context = self._get_element_at_point(cursor_pos[0], cursor_pos[1])
        
        event = MacroEvent(
            event_type=MacroEventType.SCREENSHOT,
            timestamp=time.time(),
            data={
                "action": "initial_state",
                "cursor_position": cursor_pos,
                "screen_size": pyautogui.size()
            },
            ui_context=ui_context,
            screenshot_path=screenshot_path
        )
        
        self.events.append(event)
    
    def _record_final_state(self):
        """Record the final state when stopping recording."""
        screenshot_path = None
        if self.capture_screenshots:
            screenshot_path = self._take_screenshot("final_state")
        
        cursor_pos = pyautogui.position()
        
        event = MacroEvent(
            event_type=MacroEventType.SCREENSHOT,
            timestamp=time.time(),
            data={
                "action": "final_state",
                "cursor_position": cursor_pos,
                "screen_size": pyautogui.size()
            },
            screenshot_path=screenshot_path
        )
        
        self.events.append(event)
    
    def _save_macro(self, output_format: str = "both") -> Dict[str, Any]:
        """Save the recorded macro as an organized package."""
        try:
            # Use existing package directory or create one if not exists
            if not self.macro_package_dir:
                # Fallback: create package directory if not already created
                safe_name = "".join(c for c in self.current_macro["name"] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                package_name = f"{safe_name}_{timestamp}"
                
                self.macro_package_dir = Path("macros") / package_name
                self.macro_package_dir.mkdir(parents=True, exist_ok=True)
                (self.macro_package_dir / "screenshots").mkdir(exist_ok=True)
            
            package_name = self.macro_package_dir.name
            
            # Update screenshot paths to be relative to package (if needed)
            for event in self.events:
                if event.screenshot_path and not event.screenshot_path.startswith("screenshots/"):
                    # Move existing screenshots to package directory if they exist
                    old_path = Path(event.screenshot_path)
                    if old_path.exists():
                        new_path = self.macro_package_dir / "screenshots" / old_path.name
                        shutil.move(str(old_path), str(new_path))
                        event.screenshot_path = f"screenshots/{old_path.name}"
            
            # Create clean macro data for JSON (without screenshots, internal events)
            clean_events = []
            for event in self.events:
                # Skip internal recording events
                if (event.event_type == MacroEventType.SCREENSHOT and 
                    event.data.get("action") in ["initial_state", "final_state"]):
                    continue
                    
                # Skip F9 key presses (recording control)
                if (event.event_type == MacroEventType.KEYBOARD_KEY and 
                    event.data.get("key", "").lower() == "f9"):
                    continue
                
                # Create clean event data
                clean_event_data = event.to_dict()
                
                # Remove screenshot path from JSON version
                if "screenshot_path" in clean_event_data:
                    del clean_event_data["screenshot_path"]
                
                # Enhance the event data with UI element information
                if event.ui_context:
                    ui_element = event.ui_context
                    clean_event_data["ui_element"] = {
                        "control_type": ui_element.get("control_type", "Unknown"),
                        "text": ui_element.get("text", ""),
                        "position": ui_element.get("position", {}),
                        "properties": ui_element.get("properties", {}),
                        "depth": ui_element.get("depth"),
                        "detection_method": ui_element.get("properties", {}).get("detection_method", "unknown")
                    }
                    
                    # Include context hierarchy for debugging if available
                    if ui_element.get("context_hierarchy"):
                        clean_event_data["ui_element"]["context_hierarchy"] = [
                            {
                                "control_type": elem.get("control_type", "Unknown"),
                                "text": elem.get("text", ""),
                                "depth": elem.get("depth", 0)
                            }
                            for elem in ui_element.get("context_hierarchy", [])
                        ]
                
                clean_events.append(clean_event_data)
            
            # Prepare clean macro data
            clean_macro_data = {
                **self.current_macro,
                "events": clean_events,
                "metadata": {
                    "total_events": len(clean_events),
                    "duration": self.events[-1].timestamp - self.events[0].timestamp if self.events else 0,
                    "recording_settings": {
                        "capture_ui_context": self.capture_ui_context,
                        "capture_screenshots": self.capture_screenshots,
                        "mouse_move_threshold": self.mouse_move_threshold,
                        "keyboard_commit_events": self.keyboard_commit_events
                    },
                    "ui_elements_detected": len([e for e in clean_events if e.get("ui_element")]),
                    "element_types": list(set([
                        e.get("ui_element", {}).get("control_type", "Unknown") 
                        for e in clean_events 
                        if e.get("ui_element")
                    ]))
                }
            }
            
            # Prepare full macro data with screenshots for Python generation
            full_macro_data = {
                **self.current_macro,
                "events": [event.to_dict() for event in self.events],
                "metadata": {
                    **clean_macro_data["metadata"],
                    "package_info": {
                        "package_name": package_name,
                        "created_at": datetime.now().isoformat(),
                        "screenshots_count": len([e for e in self.events if e.screenshot_path]),
                        "structure": {
                            "macro.json": "Clean macro data without screenshots",
                            "macro.py": "Executable Python script",
                            "screenshots/": "Action screenshots with UI highlighting",
                            "README.md": "Package documentation"
                        }
                    }
                }
            }
            
            saved_files = []
            
            # Save clean JSON format (without screenshots)
            if output_format in ["json", "both"]:
                json_path = self.macro_package_dir / "macro.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(clean_macro_data, f, indent=2, ensure_ascii=False)
                saved_files.append(str(json_path))
            
            # Save Python format (with screenshot references for debugging)
            if output_format in ["python", "both"]:
                python_path = self.macro_package_dir / "macro.py"
                python_code = self._generate_python_code(full_macro_data)
                with open(python_path, 'w', encoding='utf-8') as f:
                    f.write(python_code)
                saved_files.append(str(python_path))
            
            # Create README
            readme_path = self.macro_package_dir / "README.md"
            readme_content = self._generate_readme(full_macro_data)
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            saved_files.append(str(readme_path))
            
            # Create ZIP package
            zip_path = Path("macros") / f"{package_name}.zip"
            self._create_zip_package(self.macro_package_dir, zip_path)
            saved_files.append(str(zip_path))
            
            return {
                "saved_files": saved_files,
                "package_directory": str(self.macro_package_dir),
                "package_zip": str(zip_path),
                "macro_data": clean_macro_data,  # Return the clean version
                "ui_elements_detected": clean_macro_data["metadata"]["ui_elements_detected"],
                "element_types": clean_macro_data["metadata"]["element_types"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to save macro: {str(e)}")
            return {
                "error": f"Failed to save macro: {str(e)}"
            }
    
    def _create_zip_package(self, package_dir: Path, zip_path: Path):
        """Create a ZIP file of the macro package."""
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in package_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(package_dir)
                        zipf.write(file_path, arcname)
            
            self.logger.info(f"Created macro package: {zip_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to create ZIP package: {str(e)}")
    
    def _generate_readme(self, macro_data: Dict[str, Any]) -> str:
        """Generate a README file for the macro package."""
        events_summary = {}
        for event in macro_data["events"]:
            event_type = event["event_type"]
            events_summary[event_type] = events_summary.get(event_type, 0) + 1
        
        readme_lines = [
            f"# {macro_data['name']}",
            "",
            f"**Description:** {macro_data['description'] or 'No description provided'}",
            f"**Created:** {macro_data['created_at']}",
            f"**Duration:** {macro_data['metadata']['duration']:.2f} seconds",
            f"**Total Events:** {macro_data['metadata']['total_events']}",
            "",
            "## Event Summary",
            "",
        ]
        
        for event_type, count in events_summary.items():
            readme_lines.append(f"- **{event_type}**: {count} events")
        
        readme_lines.extend([
            "",
            "## Package Contents",
            "",
            "- `macro.json` - Complete macro data with UI context and timing",
            "- `macro.py` - Executable Python script",
            "- `screenshots/` - Action screenshots with highlighted UI elements",
            "- `README.md` - This documentation file",
            "",
            "## Usage",
            "",
            "### Play with MCP UI Explorer",
            "```bash",
            f'python play_macro.py --file "macros/{macro_data["metadata"]["package_info"]["package_name"]}/macro.json"',
            "```",
            "",
            "### Play with Python script",
            "```bash",
            f'python "macros/{macro_data["metadata"]["package_info"]["package_name"]}/macro.py"',
            "```",
            "",
            "### Extract from ZIP",
            "```bash",
            f'unzip "macros/{macro_data["metadata"]["package_info"]["package_name"]}.zip" -d extracted/',
            "```",
            "",
            "## Screenshots",
            "",
            "Each action in this macro has an associated screenshot showing:",
            "- **Green highlights** for clickable elements",
            "- **Blue highlights** for input fields",
            "- **Red dots** for exact click positions",
            "- **UI element boundaries** for context",
            "",
            "Screenshots are organized chronologically and named by action sequence.",
        ])
        
        return "\n".join(readme_lines)
    
    def _generate_python_code(self, macro_data: Dict[str, Any]) -> str:
        """Generate Python code to replay the macro."""
        lines = [
            '"""',
            f'Generated macro: {macro_data["name"]}',
            f'Description: {macro_data["description"]}',
            f'Created: {macro_data["created_at"]}',
            f'Total events: {len(macro_data["events"])}',
            '"""',
            '',
            'import time',
            'import pyautogui',
            '',
            'def replay_macro():',
            '    """Replay the recorded macro."""',
            '    print("Starting macro replay...")',
            '    ',
            '    # Disable pyautogui failsafe for smooth playback',
            '    pyautogui.FAILSAFE = False',
            '    ',
        ]
        
        start_time = macro_data["events"][0]["timestamp"] if macro_data["events"] else 0
        
        for i, event in enumerate(macro_data["events"]):
            event_time = event["timestamp"]
            relative_time = event_time - start_time
            
            lines.append(f'    # Event {i + 1}: {event["event_type"]} at {relative_time:.2f}s')
            
            if event["event_type"] == MacroEventType.MOUSE_CLICK:
                data = event["data"]
                lines.append(f'    pyautogui.click({data["x"]}, {data["y"]})')
                
            elif event["event_type"] == MacroEventType.MOUSE_SCROLL:
                data = event["data"]
                x, y = data.get("x", 0), data.get("y", 0)
                dy = data.get("scroll_dy", 0)
                lines.append(f'    pyautogui.scroll({dy}, x={x}, y={y})')
                
            elif event["event_type"] == MacroEventType.MOUSE_MOVE:
                # Handle legacy scroll events or actual mouse moves
                data = event["data"]
                if data.get("action") == "scroll":
                    # Legacy scroll event
                    x, y = data.get("x", 0), data.get("y", 0)
                    dy = data.get("scroll_dy", 0)
                    lines.append(f'    pyautogui.scroll({dy}, x={x}, y={y})')
                else:
                    # Actual mouse move (though these should be rare now)
                    x, y = data.get("x", 0), data.get("y", 0)
                    lines.append(f'    pyautogui.moveTo({x}, {y})')
                
            elif event["event_type"] == MacroEventType.KEYBOARD_TYPE:
                data = event["data"]
                text = data["text"].replace("'", "\\'")
                lines.append(f'    pyautogui.write("{text}")')
                
            elif event["event_type"] == MacroEventType.KEYBOARD_KEY:
                data = event["data"]
                lines.append(f'    pyautogui.press("{data["key"]}")')
                
            elif event["event_type"] == MacroEventType.WAIT:
                data = event["data"]
                lines.append(f'    time.sleep({data["duration"]})')
            
            # Add timing delay between events
            if i < len(macro_data["events"]) - 1:
                next_event_time = macro_data["events"][i + 1]["timestamp"]
                delay = next_event_time - event_time
                if delay > 0.1:  # Only add significant delays
                    lines.append(f'    time.sleep({delay:.2f})')
            
            lines.append('')
        
        lines.extend([
            '    print("Macro replay completed.")',
            '',
            '',
            'if __name__ == "__main__":',
            '    replay_macro()',
        ])
        
        return '\n'.join(lines) 