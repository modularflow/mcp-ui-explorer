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
        """Get the UI element directly at the specified coordinates using point-based queries."""
        try:
            # Try multiple approaches to find the element at the specific point
            
            # Method 1: Use Windows UI Automation to find element from point
            try:
                # Get the window at the point first
                import win32gui
                hwnd = win32gui.WindowFromPoint((x, y))
                
                if hwnd:
                    # Get window title and class
                    window_title = win32gui.GetWindowText(hwnd)
                    window_class = win32gui.GetClassName(hwnd)
                    
                    # Get window rectangle
                    rect = win32gui.GetWindowRect(hwnd)
                    
                    self.logger.debug(f"Found window at ({x}, {y}): '{window_title}' class='{window_class}' rect={rect}")
                    
                    # Special handling for taskbar elements
                    if window_class in ['MSTaskSwWClass', 'Shell_TrayWnd', 'MSTaskListWClass']:
                        self.logger.debug(f"Detected taskbar element, trying enhanced detection...")
                        
                        # Try to get more specific taskbar button information
                        taskbar_element = self._detect_taskbar_button(hwnd, window_class, window_title, x, y, rect)
                        if taskbar_element:
                            return taskbar_element
                    
                    # For some specific classes, we can provide better information
                    if window_class in ['MSTaskSwWClass', 'Shell_TrayWnd', 'Button', 'ReBarWindow32']:
                        # These are often taskbar or button elements
                        element_type = "Button" if "button" in window_class.lower() or window_class == 'MSTaskSwWClass' else "Control"
                        
                        # Try to get more descriptive text
                        display_text = window_title
                        if not display_text and window_class == 'MSTaskSwWClass':
                            # This is likely a taskbar button, try to get app name
                            try:
                                # For taskbar buttons, the window might contain app information
                                if "firefox" in window_title.lower():
                                    display_text = "Firefox"
                                elif len(window_title.strip()) == 0:
                                    display_text = f"Taskbar Button ({window_class})"
                                else:
                                    display_text = window_title
                            except:
                                display_text = f"Taskbar Button ({window_class})"
                        
                        return {
                            "control_type": element_type,
                            "text": display_text,
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
                                "detection_method": "direct_window_api"
                            }
                        }
                    
                    # Try to get more specific element info using UI Automation
                    try:
                        from pyautogui import Desktop
                        desktop = Desktop(backend="uia")
                        
                        # Find window by handle
                        for window in desktop.windows():
                            if window.handle == hwnd and window.is_visible():
                                # Try to find child element at the specific point
                                try:
                                    # Convert to window-relative coordinates
                                    rel_x = x - rect[0]
                                    rel_y = y - rect[1]
                                    
                                    # Search for child elements that contain this point
                                    element_info = self._find_element_at_point_in_window(window, rel_x, rel_y, x, y)
                                    if element_info and element_info.get('control_type') not in ['Window', 'Document']:
                                        return element_info
                                        
                                except Exception as e:
                                    self.logger.debug(f"Error searching in window children: {e}")
                                
                                # Fallback: return window info with enhanced details
                                return {
                                    "control_type": "Window",
                                    "text": window_title,
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
                                        "detection_method": "ui_automation"
                                    }
                                }
                                
                    except Exception as e:
                        self.logger.debug(f"UI Automation failed: {e}")
                        
                        # Fallback: return basic window info
                        return {
                            "control_type": "Window", 
                            "text": window_title,
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
                                "detection_method": "basic_window_api"
                            }
                        }
                        
            except Exception as e:
                self.logger.debug(f"Point query method 1 failed: {e}")
                
            # Method 2: Fallback using smaller region analysis
            try:
                # Analyze a small region around the click point
                region_size = 100
                region = (
                    max(0, x - region_size // 2),
                    max(0, y - region_size // 2), 
                    min(pyautogui.size()[0], x + region_size // 2),
                    min(pyautogui.size()[1], y + region_size // 2)
                )
                
                ui_hierarchy = analyze_ui_hierarchy(
                    region=region,
                    max_depth=6,
                    focus_only=True,
                    min_size=5,
                    visible_only=True
                )
                
                if ui_hierarchy:
                    element = self._find_closest_element(ui_hierarchy, x, y)
                    if element:
                        element["properties"] = element.get("properties", {})
                        element["properties"]["detection_method"] = "hierarchy_analysis"
                        self.logger.debug(f"Found element via small region analysis: {element.get('control_type')} '{element.get('text')}'")
                        return element
                        
            except Exception as e:
                self.logger.debug(f"Point query method 2 failed: {e}")
                
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to get element at point ({x}, {y}): {str(e)}")
            return None
    
    def _detect_taskbar_button(self, hwnd: int, window_class: str, window_title: str, x: int, y: int, rect: tuple) -> Optional[Dict[str, Any]]:
        """Enhanced detection for taskbar buttons using multiple methods."""
        try:
            import win32gui
            import win32con
            
            self.logger.debug(f"Enhanced taskbar detection for class '{window_class}' title '{window_title}'")
            
            # Method 1: Try to enumerate child windows to find specific buttons (including nested children)
            try:
                taskbar_buttons = []
                
                def enum_child_proc(child_hwnd, lparam):
                    try:
                        child_class = win32gui.GetClassName(child_hwnd)
                        child_title = win32gui.GetWindowText(child_hwnd)
                        child_rect = win32gui.GetWindowRect(child_hwnd)
                        
                        self.logger.debug(f"Found child: class='{child_class}' title='{child_title}' rect={child_rect}")
                        
                        # Check if this child window contains our click point
                        if (child_rect[0] <= x <= child_rect[2] and 
                            child_rect[1] <= y <= child_rect[3]):
                            
                            self.logger.debug(f"Found child at click point: class='{child_class}' title='{child_title}' rect={child_rect}")
                            
                            # Look for Firefox indicators in title or class
                            element_text = child_title
                            if "firefox" in child_title.lower():
                                element_text = "Firefox"
                            elif "mozilla" in child_title.lower():
                                element_text = "Mozilla Firefox"
                            elif child_class == "MSTaskSwWClass":
                                # Try to get tooltip or accessibility name
                                element_text = self._get_taskbar_button_name(child_hwnd) or child_title or "Taskbar Button"
                            
                            taskbar_buttons.append({
                                "hwnd": child_hwnd,
                                "class": child_class,
                                "title": child_title,
                                "text": element_text,
                                "rect": child_rect,
                                "distance_to_click": abs((child_rect[0] + child_rect[2]) // 2 - x) + abs((child_rect[1] + child_rect[3]) // 2 - y)
                            })
                            
                            # If this is MSTaskListWClass, dive deeper to find individual buttons
                            if child_class == "MSTaskListWClass":
                                self.logger.debug(f"Found MSTaskListWClass container, searching for individual app buttons...")
                                
                                def enum_grandchild_proc(grandchild_hwnd, lparam):
                                    try:
                                        gc_class = win32gui.GetClassName(grandchild_hwnd)
                                        gc_title = win32gui.GetWindowText(grandchild_hwnd)
                                        gc_rect = win32gui.GetWindowRect(grandchild_hwnd)
                                        
                                        self.logger.debug(f"  Found grandchild: class='{gc_class}' title='{gc_title}' rect={gc_rect}")
                                        
                                        # Check if this grandchild contains our click point
                                        if (gc_rect[0] <= x <= gc_rect[2] and 
                                            gc_rect[1] <= y <= gc_rect[3]):
                                            
                                            self.logger.debug(f"  Grandchild contains click point: class='{gc_class}' title='{gc_title}'")
                                            
                                            # Try to get process information for this button
                                            gc_element_text = gc_title
                                            try:
                                                import win32process
                                                import psutil
                                                
                                                _, gc_process_id = win32process.GetWindowThreadProcessId(grandchild_hwnd)
                                                if gc_process_id:
                                                    try:
                                                        gc_process = psutil.Process(gc_process_id)
                                                        gc_process_name = gc_process.name()
                                                        
                                                        self.logger.debug(f"  Grandchild process: {gc_process_name} (PID: {gc_process_id})")
                                                        
                                                        if "firefox" in gc_process_name.lower():
                                                            gc_element_text = "Firefox"
                                                        elif gc_title and "firefox" in gc_title.lower():
                                                            gc_element_text = "Firefox"
                                                        elif gc_title:
                                                            gc_element_text = gc_title
                                                        else:
                                                            gc_element_text = f"App Button ({gc_process_name})"
                                                            
                                                    except Exception as e:
                                                        self.logger.debug(f"  Process lookup failed for grandchild: {e}")
                                                        
                                            except ImportError:
                                                pass
                                            
                                            # Look for Firefox indicators
                                            if "firefox" in gc_title.lower():
                                                gc_element_text = "Firefox"
                                            elif "mozilla" in gc_title.lower():
                                                gc_element_text = "Mozilla Firefox"
                                            
                                            taskbar_buttons.append({
                                                "hwnd": grandchild_hwnd,
                                                "class": gc_class,
                                                "title": gc_title,
                                                "text": gc_element_text,
                                                "rect": gc_rect,
                                                "distance_to_click": abs((gc_rect[0] + gc_rect[2]) // 2 - x) + abs((gc_rect[1] + gc_rect[3]) // 2 - y),
                                                "is_grandchild": True
                                            })
                                            
                                            # Continue searching even deeper if needed
                                            def enum_great_grandchild_proc(ggc_hwnd, lparam):
                                                try:
                                                    ggc_class = win32gui.GetClassName(ggc_hwnd)
                                                    ggc_title = win32gui.GetWindowText(ggc_hwnd)
                                                    ggc_rect = win32gui.GetWindowRect(ggc_hwnd)
                                                    
                                                    # Check if this great-grandchild contains our click point
                                                    if (ggc_rect[0] <= x <= ggc_rect[2] and 
                                                        ggc_rect[1] <= y <= ggc_rect[3]):
                                                        
                                                        self.logger.debug(f"    Found great-grandchild at click: class='{ggc_class}' title='{ggc_title}' rect={ggc_rect}")
                                                        
                                                        # Try to get even more specific information
                                                        ggc_element_text = ggc_title
                                                        if "firefox" in ggc_title.lower():
                                                            ggc_element_text = "Firefox"
                                                        elif "mozilla" in ggc_title.lower():
                                                            ggc_element_text = "Mozilla Firefox"
                                                        
                                                        taskbar_buttons.append({
                                                            "hwnd": ggc_hwnd,
                                                            "class": ggc_class,
                                                            "title": ggc_title,
                                                            "text": ggc_element_text,
                                                            "rect": ggc_rect,
                                                            "distance_to_click": abs((ggc_rect[0] + ggc_rect[2]) // 2 - x) + abs((ggc_rect[1] + ggc_rect[3]) // 2 - y),
                                                            "is_great_grandchild": True
                                                        })
                                                        
                                                except Exception as e:
                                                    self.logger.debug(f"    Error processing great-grandchild: {e}")
                                                
                                                return True
                                            
                                            # Search great-grandchildren
                                            win32gui.EnumChildWindows(grandchild_hwnd, enum_great_grandchild_proc, 0)
                                            
                                    except Exception as e:
                                        self.logger.debug(f"  Error processing grandchild window: {e}")
                                    
                                    return True  # Continue enumeration
                                
                                # Enumerate grandchildren of the MSTaskListWClass
                                win32gui.EnumChildWindows(child_hwnd, enum_grandchild_proc, 0)
                            
                    except Exception as e:
                        self.logger.debug(f"Error processing child window: {e}")
                    
                    return True  # Continue enumeration
                
                # Enumerate child windows
                win32gui.EnumChildWindows(hwnd, enum_child_proc, 0)
                
                if taskbar_buttons:
                    # Sort by specificity and firefox preference
                    taskbar_buttons.sort(key=lambda b: (
                        0 if "firefox" in b["text"].lower() else 1,  # Firefox buttons first
                        0 if b.get("is_great_grandchild") else (1 if b.get("is_grandchild") else 2),  # Deeper elements first
                        b["distance_to_click"]  # Then by distance
                    ))
                    
                    best_button = taskbar_buttons[0]
                    self.logger.debug(f"Selected best taskbar button: '{best_button['text']}' class='{best_button['class']}' depth={best_button.get('is_great_grandchild', False) and 'great-grandchild' or (best_button.get('is_grandchild', False) and 'grandchild' or 'child')}")
                    
                    # Apply coordinate-based heuristics for better descriptions
                    enhanced_text = self._enhance_taskbar_button_description(best_button, x, y, rect)
                    
                    return {
                        "control_type": "Button",
                        "text": enhanced_text,
                        "position": {
                            "left": best_button["rect"][0],
                            "top": best_button["rect"][1],
                            "right": best_button["rect"][2],
                            "bottom": best_button["rect"][3]
                        },
                        "distance": 0,
                        "properties": {
                            "class_name": best_button["class"],
                            "handle": best_button["hwnd"],
                            "parent_handle": hwnd,
                            "detection_method": "enhanced_taskbar_enum_deep",
                            "depth_level": best_button.get("is_great_grandchild", False) and "great-grandchild" or (best_button.get("is_grandchild", False) and "grandchild" or "child"),
                            "original_text": best_button["text"]
                        }
                    }
                    
            except Exception as e:
                self.logger.debug(f"Child enumeration failed: {e}")
            
            # Method 2: Try to get window process information
            try:
                import win32process
                import psutil
                
                # Get process ID and name
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                if process_id:
                    try:
                        process = psutil.Process(process_id)
                        process_name = process.name()
                        
                        self.logger.debug(f"Window process: {process_name} (PID: {process_id})")
                        
                        # Check if this is Firefox process
                        if "firefox" in process_name.lower():
                            return {
                                "control_type": "Button",
                                "text": "Firefox",
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
                                    "process_name": process_name,
                                    "process_id": process_id,
                                    "detection_method": "process_identification"
                                }
                            }
                    except Exception as e:
                        self.logger.debug(f"Process lookup failed: {e}")
                        
            except Exception as e:
                self.logger.debug(f"Process method failed: {e}")
            
            # Method 3: Coordinate-based heuristic analysis
            try:
                heuristic_text = self._get_taskbar_heuristic_description(x, y, rect, window_class, window_title)
                
                return {
                    "control_type": "Button",
                    "text": heuristic_text,
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
                        "detection_method": "coordinate_heuristic"
                    }
                }
                
            except Exception as e:
                self.logger.debug(f"Heuristic method failed: {e}")
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Enhanced taskbar detection failed: {e}")
            return None
    
    def _enhance_taskbar_button_description(self, button_info: Dict, x: int, y: int, taskbar_rect: tuple) -> str:
        """Enhance taskbar button description using coordinate-based heuristics."""
        try:
            original_text = button_info.get("text", "")
            button_class = button_info.get("class", "")
            
            # If we already have a good description, keep it
            if original_text and original_text not in ["Running applications", "DesktopWindowXamlSource", ""]:
                return original_text
            
            # Use coordinate-based heuristics for Windows 11 taskbar
            return self._get_taskbar_heuristic_description(x, y, taskbar_rect, button_class, original_text)
            
        except Exception as e:
            self.logger.debug(f"Failed to enhance button description: {e}")
            return button_info.get("text", "Taskbar Button")
    
    def _get_taskbar_heuristic_description(self, x: int, y: int, rect: tuple, window_class: str, window_title: str) -> str:
        """Generate a taskbar button description using coordinate-based heuristics."""
        try:
            # Get running processes to correlate with click position
            import psutil
            
            # Taskbar layout analysis for Windows 11
            taskbar_left = rect[0]
            taskbar_right = rect[2]
            taskbar_width = taskbar_right - taskbar_left
            
            # Common Windows 11 taskbar areas (approximate)
            start_button_end = taskbar_left + 60  # Start button area
            search_area_end = start_button_end + 300  # Search area
            task_view_area_end = search_area_end + 60  # Task view button
            app_area_start = task_view_area_end  # Where apps typically start
            
            # Determine the area clicked
            if x <= start_button_end:
                return "Start Button"
            elif x <= search_area_end:
                return "Search Area"
            elif x <= task_view_area_end:
                return "Task View Button"
            elif x >= taskbar_right - 200:  # System tray area
                return "System Tray"
            else:
                # This is likely an application button area
                # Try to correlate with running processes
                app_processes = []
                try:
                    for proc in psutil.process_iter(['pid', 'name', 'exe']):
                        try:
                            proc_info = proc.info
                            proc_name = proc_info['name'].lower()
                            
                            # Common applications that appear on taskbar
                            if any(app in proc_name for app in ['firefox', 'chrome', 'edge', 'notepad', 'explorer', 'code', 'outlook', 'teams', 'word', 'excel', 'powerpoint']):
                                app_processes.append(proc_name)
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            continue
                            
                except Exception as e:
                    self.logger.debug(f"Process enumeration failed: {e}")
                
                # Estimate position within app area
                app_area_width = taskbar_right - 200 - app_area_start  # Subtract system tray
                relative_position = (x - app_area_start) / app_area_width if app_area_width > 0 else 0
                
                # Try to guess which app based on position and running processes
                if app_processes:
                    app_processes.sort()  # Consistent ordering
                    
                    # Simple heuristic: estimate app button based on position
                    estimated_index = min(int(relative_position * len(app_processes)), len(app_processes) - 1)
                    if 0 <= estimated_index < len(app_processes):
                        guessed_app = app_processes[estimated_index]
                        
                        # Clean up the process name for display
                        if 'firefox' in guessed_app:
                            return "Firefox"
                        elif 'chrome' in guessed_app:
                            return "Chrome"
                        elif 'edge' in guessed_app:
                            return "Microsoft Edge"
                        elif 'code' in guessed_app:
                            return "Visual Studio Code"
                        elif 'notepad' in guessed_app:
                            return "Notepad"
                        elif 'explorer' in guessed_app:
                            return "File Explorer"
                        else:
                            # Capitalize first letter and remove .exe
                            clean_name = guessed_app.replace('.exe', '').replace('_', ' ').title()
                            return f"App Button ({clean_name})"
                
                # Fallback descriptions based on position
                if relative_position < 0.3:
                    return "Left App Button"
                elif relative_position < 0.7:
                    return "Center App Button"
                else:
                    return "Right App Button"
            
        except Exception as e:
            self.logger.debug(f"Heuristic description failed: {e}")
            return "Taskbar Button"
    
    def _find_element_at_point_in_window(self, window, rel_x: int, rel_y: int, abs_x: int, abs_y: int) -> Optional[Dict[str, Any]]:
        """Find a specific UI element within a window that contains the given point."""
        try:
            # Track the most specific element and build a context hierarchy
            elements_at_point = []  # List of elements from most general to most specific
            search_count = 0
            
            self.logger.debug(f"Starting deep search in window at relative pos ({rel_x}, {rel_y}), absolute pos ({abs_x}, {abs_y})")
            
            def search_children(element, depth=0, parent_path=""):
                nonlocal search_count
                search_count += 1
                
                if depth > 15:  # Increased even further
                    return None
                
                # Log search progress every 50 elements to avoid spam
                if search_count % 50 == 0:
                    self.logger.debug(f"Searched {search_count} elements so far...")
                    
                try:
                    # Get element rectangle
                    rect = element.rectangle()
                    
                    # Enhanced debugging for elements near our target
                    distance_to_target = abs(rect.left + (rect.right - rect.left)//2 - abs_x) + abs(rect.top + (rect.bottom - rect.top)//2 - abs_y)
                    is_near_target = distance_to_target < 100
                    
                    # Check if point is within this element
                    if (rect.left <= abs_x <= rect.right and 
                        rect.top <= abs_y <= rect.bottom):
                        
                        # This element contains the point
                        control_type = element.element_info.control_type if hasattr(element, 'element_info') else "Unknown"
                        text = ""
                        
                        # Try multiple ways to get text
                        try:
                            if hasattr(element, 'window_text') and callable(element.window_text):
                                text = element.window_text()
                        except:
                            pass
                            
                        if not text:
                            try:
                                if hasattr(element, 'text') and callable(element.text):
                                    text = element.text()
                            except:
                                pass
                                
                        if not text:
                            try:
                                if hasattr(element.element_info, 'name'):
                                    text = element.element_info.name or ""
                            except:
                                pass
                        
                        # Get additional properties
                        properties = {}
                        try:
                            if hasattr(element.element_info, 'class_name'):
                                properties['class_name'] = element.element_info.class_name
                            if hasattr(element.element_info, 'automation_id'):
                                properties['automation_id'] = element.element_info.automation_id
                            if hasattr(element.element_info, 'control_id'):
                                properties['control_id'] = element.element_info.control_id
                        except:
                            pass
                        
                        element_info = {
                            "control_type": control_type,
                            "text": text,
                            "position": {
                                "left": rect.left,
                                "top": rect.top,
                                "right": rect.right,
                                "bottom": rect.bottom
                            },
                            "distance": 0,
                            "depth": depth,
                            "path": parent_path,
                            "properties": properties
                        }
                        
                        # Enhanced debugging for containing elements
                        self.logger.debug(f"Found containing element at depth {depth}: {control_type} '{text}' "
                                        f"rect=({rect.left},{rect.top},{rect.right},{rect.bottom}) "
                                        f"props={properties}")
                        
                        # Add this element to our hierarchy
                        elements_at_point.append(element_info)
                        
                        # Continue searching children for more specific elements
                        try:
                            children = element.children()
                            self.logger.debug(f"Element at depth {depth} has {len(children)} children")
                            
                            for i, child in enumerate(children):
                                child_path = f"{parent_path}.{i}" if parent_path else str(i)
                                search_children(child, depth + 1, child_path)
                        except Exception as e:
                            self.logger.debug(f"Error accessing children at depth {depth}: {e}")
                    
                    elif is_near_target:
                        # Log elements that are near the target but don't contain it
                        control_type = element.element_info.control_type if hasattr(element, 'element_info') else "Unknown"
                        try:
                            text = element.window_text() if hasattr(element, 'window_text') and callable(element.window_text) else ""
                            if not text and hasattr(element.element_info, 'name'):
                                text = element.element_info.name or ""
                        except:
                            text = ""
                        
                        self.logger.debug(f"Near target at depth {depth} (distance={distance_to_target}): {control_type} '{text}' "
                                        f"rect=({rect.left},{rect.top},{rect.right},{rect.bottom})")
                         
                except Exception as e:
                    # Element might not be accessible
                    if depth <= 3:  # Only log errors for shallow depths to avoid spam
                        self.logger.debug(f"Error accessing element at depth {depth}: {e}")
                    
                return None
            
            # Start search from window
            search_children(window)
            
            self.logger.debug(f"Search completed. Searched {search_count} total elements, found {len(elements_at_point)} containing elements")
            
            if not elements_at_point:
                return None
            
            # Log all containing elements for debugging
            for i, elem in enumerate(elements_at_point):
                self.logger.debug(f"Containing element {i}: depth={elem['depth']}, type={elem['control_type']}, text='{elem['text']}', props={elem.get('properties', {})}")
            
            # Find the most specific element (deepest in hierarchy)
            most_specific = max(elements_at_point, key=lambda e: e['depth'])
            
            # Add context hierarchy for screenshot purposes
            most_specific['context_hierarchy'] = elements_at_point
            
            # For Firefox button detection, look for specific patterns
            if len(elements_at_point) > 1:
                # Look for Firefox-related elements
                for element in reversed(elements_at_point):  # Start from most specific
                    element_text = element.get('text', '').lower()
                    element_type = element.get('control_type', '')
                    properties = element.get('properties', {})
                    
                    # Check for Firefox indicators
                    is_firefox_related = (
                        'firefox' in element_text or
                        'mozilla' in element_text or
                        any('firefox' in str(v).lower() for v in properties.values() if v)
                    )
                    
                    # Prefer specific interactive elements
                    is_interactive = element_type in ['Button', 'MenuItem', 'ListItem', 'Hyperlink']
                    
                    if is_firefox_related and (is_interactive or element.get('depth', 0) > most_specific.get('depth', 0) - 2):
                        self.logger.debug(f"Found Firefox-specific element: {element_type} '{element.get('text', '')}' at depth {element.get('depth')}")
                        element['context_hierarchy'] = elements_at_point
                        return element
            
            # Prefer interactive elements over containers
            interactive_elements = [e for e in elements_at_point 
                                  if e.get('control_type') in ['Button', 'MenuItem', 'ListItem', 'Hyperlink', 'Edit', 'CheckBox']]
            
            if interactive_elements:
                # Return the most specific interactive element
                best_interactive = max(interactive_elements, key=lambda e: e['depth'])
                best_interactive['context_hierarchy'] = elements_at_point
                self.logger.debug(f"Found interactive element: {best_interactive.get('control_type')} '{best_interactive.get('text', '')}' at depth {best_interactive.get('depth')}")
                return best_interactive
            
            # Fallback to most specific element
            self.logger.debug(f"Using most specific element: {most_specific.get('control_type')} '{most_specific.get('text', '')}' at depth {most_specific.get('depth')}")
            return most_specific
            
        except Exception as e:
            self.logger.debug(f"Error searching window children: {e}")
            return None
    
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
                
                if distance < min_distance:
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
    
    def _take_screenshot(self, prefix: str = "macro", action_data: Optional[Dict] = None) -> Optional[str]:
        """Take a focused screenshot highlighting the relevant UI element."""
        try:
            if not self.macro_package_dir:
                return None
                
            self.screenshot_counter += 1
            screenshot_filename = f"{self.screenshot_counter:03d}_{prefix}.png"
            screenshot_path = self.macro_package_dir / "screenshots" / screenshot_filename
            
            # Ensure screenshots directory exists
            screenshot_path.parent.mkdir(exist_ok=True)
            
            if action_data and action_data.get("x") is not None and action_data.get("y") is not None:
                # Create focused screenshot for click actions
                return self._create_focused_screenshot(
                    action_data["x"], 
                    action_data["y"], 
                    screenshot_path,
                    action_type=prefix
                )
            else:
                # Create full screenshot with UI hierarchy for other actions
                return self._create_full_ui_screenshot(screenshot_path, prefix)
                
        except Exception as e:
            self.logger.warning(f"Failed to take screenshot: {str(e)}")
            return None
    
    def _create_focused_screenshot(self, x: int, y: int, output_path: Path, action_type: str = "click") -> str:
        """Create a focused screenshot highlighting only the relevant UI element."""
        try:
            # Use direct point-based element detection first
            target_element = self._get_element_at_point(x, y)
            
            if target_element:
                self.logger.debug(f"Direct detection found element: {target_element.get('control_type', 'Unknown')} '{target_element.get('text', '')}' "
                                f"at depth {target_element.get('depth', 'unknown')}")
                
                # Check if we have context hierarchy for better screenshots
                context_hierarchy = target_element.get('context_hierarchy', [])
                if context_hierarchy and len(context_hierarchy) > 1:
                    self.logger.debug(f"Found {len(context_hierarchy)} elements in hierarchy")
                    for i, elem in enumerate(context_hierarchy):
                        self.logger.debug(f"  Depth {elem.get('depth', i)}: {elem.get('control_type')} '{elem.get('text', '')}'")
            else:
                self.logger.debug(f"Direct detection found no element for {action_type} at ({x}, {y})")
            
            if target_element and target_element.get('distance', float('inf')) == 0:
                # Element contains the click point - create focused screenshot with context
                bounds = target_element.get('position', {})
                context_hierarchy = target_element.get('context_hierarchy', [])
                
                if bounds:
                    # Determine screenshot bounds - use parent context if available for better context
                    screenshot_bounds = bounds
                    
                    # If we have a context hierarchy, use a parent container for better context
                    if context_hierarchy and len(context_hierarchy) > 1:
                        # Find a good parent container (not too big, not too small)
                        for parent in context_hierarchy[:-1]:  # Skip the most specific element
                            parent_pos = parent.get('position', {})
                            if parent_pos:
                                parent_width = parent_pos.get('right', 0) - parent_pos.get('left', 0)
                                parent_height = parent_pos.get('bottom', 0) - parent_pos.get('top', 0)
                                
                                # Use parent if it's not too large (reasonable context size)
                                if parent_width <= 800 and parent_height <= 600:
                                    screenshot_bounds = parent_pos
                                    self.logger.debug(f"Using parent container for context: {parent.get('control_type')} '{parent.get('text', '')}'")
                                    break
                    
                    # Expand bounds slightly for better visibility
                    padding = 20
                    left = max(0, screenshot_bounds.get('left', x - 100) - padding)
                    top = max(0, screenshot_bounds.get('top', y - 100) - padding)
                    right = min(pyautogui.size()[0], screenshot_bounds.get('right', x + 100) + padding)
                    bottom = min(pyautogui.size()[1], screenshot_bounds.get('bottom', y + 100) + padding)
                    
                    self.logger.debug(f"Creating focused screenshot for bounds: ({left}, {top}, {right}, {bottom})")
                    
                    # Take screenshot of the focused region
                    region_screenshot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
                    
                    # Create enhanced image with highlighting
                    enhanced_image = self._enhance_focused_screenshot_with_context(
                        region_screenshot, 
                        target_element,
                        context_hierarchy,
                        x - left,  # relative x in cropped image
                        y - top,   # relative y in cropped image
                        x,         # absolute x coordinate
                        y,         # absolute y coordinate
                        left,      # screenshot left offset
                        top,       # screenshot top offset
                        action_type
                    )
                    
                    enhanced_image.save(str(output_path))
                    return str(output_path.relative_to(self.macro_package_dir))
            
            # Fallback: create a region around the click point with basic highlighting
            # This handles cases where direct element detection fails or the click is not within any detected element
            self.logger.debug(f"No containing element found for {action_type} at ({x}, {y}), using region screenshot")
            return self._create_region_screenshot(x, y, output_path, action_type)
            
        except Exception as e:
            self.logger.warning(f"Failed to create focused screenshot: {str(e)}")
            return self._create_region_screenshot(x, y, output_path, action_type)
    
    def _enhance_focused_screenshot_with_context(self, image: Image.Image, target_element: Dict, context_hierarchy: List[Dict], 
                                               rel_x: int, rel_y: int, abs_x: int, abs_y: int, 
                                               screenshot_left: int, screenshot_top: int, action_type: str) -> Image.Image:
        """Enhance the screenshot with highlighting for both the target element and its context."""
        # Convert to RGBA for transparency effects
        enhanced = image.convert("RGBA")
        
        # Create overlay for highlighting
        overlay = Image.new("RGBA", enhanced.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Highlight context hierarchy (from general to specific)
        if context_hierarchy:
            for i, element in enumerate(context_hierarchy):
                bounds = element.get('position', {})
                if not bounds:
                    continue
                    
                # Convert to screenshot-relative coordinates
                elem_left = bounds.get('left', 0) - screenshot_left
                elem_top = bounds.get('top', 0) - screenshot_top
                elem_right = bounds.get('right', enhanced.width + screenshot_left) - screenshot_left
                elem_bottom = bounds.get('bottom', enhanced.height + screenshot_top) - screenshot_top
                
                # Ensure bounds are within image
                elem_left = max(0, min(enhanced.width, elem_left))
                elem_top = max(0, min(enhanced.height, elem_top))
                elem_right = max(0, min(enhanced.width, elem_right))
                elem_bottom = max(0, min(enhanced.height, elem_bottom))
                
                # Skip if bounds are invalid
                if elem_right <= elem_left or elem_bottom <= elem_top:
                    continue
                
                # Color coding based on element type and hierarchy level
                control_type = element.get('control_type', '')
                is_target = element == target_element
                
                if is_target:
                    # Target element gets the strongest highlighting
                    if action_type == "click":
                        color = (0, 255, 0, 200)  # Bright green
                        width = 4
                    elif action_type == "type":
                        color = (0, 100, 255, 200)  # Blue
                        width = 4
                    else:
                        color = (255, 255, 0, 200)  # Yellow
                        width = 3
                else:
                    # Context elements get lighter highlighting
                    if control_type in ['Window', 'Pane']:
                        color = (128, 128, 128, 100)  # Light gray for containers
                        width = 2
                    else:
                        color = (255, 165, 0, 150)  # Orange for other context elements
                        width = 2
                
                # Draw the element boundary
                draw.rectangle([elem_left, elem_top, elem_right, elem_bottom], 
                             outline=color, width=width)
                
                # Add label for context elements (but not too cluttered)
                if not is_target and element.get('text') and len(element.get('text', '').strip()) > 0:
                    try:
                        from PIL import ImageFont
                        try:
                            font = ImageFont.truetype("arial.ttf", 10)
                        except:
                            font = ImageFont.load_default()
                    except ImportError:
                        font = None
                    
                    label_text = f"{control_type}: {element.get('text', '')}"
                    if len(label_text) > 30:
                        label_text = label_text[:27] + "..."
                    
                    # Position label at top-left of element
                    label_x = elem_left + 2
                    label_y = elem_top + 2
                    
                    # Draw semi-transparent background for label
                    if font:
                        bbox = draw.textbbox((0, 0), label_text, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                    else:
                        text_width = len(label_text) * 6
                        text_height = 11
                    
                    # Ensure label fits in image
                    if label_x + text_width < enhanced.width and label_y + text_height < enhanced.height:
                        draw.rectangle([label_x - 1, label_y - 1, label_x + text_width + 1, label_y + text_height + 1], 
                                     fill=(0, 0, 0, 120))
                        
                        if font:
                            draw.text((label_x, label_y), label_text, fill=(255, 255, 255, 200), font=font)
                        else:
                            draw.text((label_x, label_y), label_text, fill=(255, 255, 255, 200))
        
        # Add action indicator at the exact click point
        if action_type == "click":
            # Red circle for click with white border
            draw.ellipse([rel_x - 8, rel_y - 8, rel_x + 8, rel_y + 8], 
                       fill=(255, 0, 0, 220), outline=(255, 255, 255, 255), width=2)
            # Smaller inner circle for precise location
            draw.ellipse([rel_x - 3, rel_y - 3, rel_x + 3, rel_y + 3], 
                       fill=(255, 255, 255, 255))
        elif action_type == "type":
            # Blue crosshair for text input
            draw.line([rel_x - 12, rel_y, rel_x + 12, rel_y], 
                     fill=(0, 100, 255, 255), width=2)
            draw.line([rel_x, rel_y - 12, rel_x, rel_y + 12], 
                     fill=(0, 100, 255, 255), width=2)
            # Small circle at center
            draw.ellipse([rel_x - 2, rel_y - 2, rel_x + 2, rel_y + 2], 
                       fill=(0, 100, 255, 255))
        
        # Add coordinate annotation with absolute coordinates
        self._add_absolute_coordinate_annotation(draw, rel_x, rel_y, abs_x, abs_y, enhanced.size, action_type)
        
        # Add element information annotation
        if target_element:
            element_info = f"{target_element.get('control_type', 'Unknown')}"
            if target_element.get('text'):
                element_info += f": {target_element.get('text', '')}"
            
            # Position at bottom of image
            try:
                from PIL import ImageFont
                try:
                    font = ImageFont.truetype("arial.ttf", 11)
                except:
                    font = ImageFont.load_default()
            except ImportError:
                font = None
            
            if len(element_info) > 40:
                element_info = element_info[:37] + "..."
            
            if font:
                bbox = draw.textbbox((0, 0), element_info, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = len(element_info) * 6
                text_height = 11
            
            info_x = 5
            info_y = enhanced.height - text_height - 10
            
            # Draw background
            draw.rectangle([info_x - 2, info_y - 2, info_x + text_width + 2, info_y + text_height + 2], 
                         fill=(0, 0, 0, 160), outline=(255, 255, 255, 100))
            
            # Draw text
            if font:
                draw.text((info_x, info_y), element_info, fill=(255, 255, 255, 255), font=font)
            else:
                draw.text((info_x, info_y), element_info, fill=(255, 255, 255, 255))
        
        # Combine original image with overlay
        return Image.alpha_composite(enhanced, overlay)
    
    def _add_absolute_coordinate_annotation(self, draw: ImageDraw.Draw, rel_x: int, rel_y: int, abs_x: int, abs_y: int, image_size: tuple, action_type: str):
        """Add coordinate annotation with absolute screen coordinates."""
        try:
            # Try to use a better font if available, fallback to default
            try:
                from PIL import ImageFont
                font_size = 12
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
            
            # Use absolute coordinates for the annotation
            coord_text = f"({abs_x}, {abs_y})"
            
            # Choose text color based on action type
            if action_type == "click":
                text_color = (255, 255, 255, 255)  # White text
                bg_color = (255, 0, 0, 180)        # Red background
            elif action_type == "type":
                text_color = (255, 255, 255, 255)  # White text
                bg_color = (0, 100, 255, 180)      # Blue background
            else:
                text_color = (255, 255, 255, 255)  # White text
                bg_color = (128, 128, 128, 180)    # Gray background
            
            # Get text dimensions
            if font:
                bbox = draw.textbbox((0, 0), coord_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                # Estimate text size for default font
                text_width = len(coord_text) * 6
                text_height = 11
            
            # Position the text annotation
            padding = 4
            label_width = text_width + (padding * 2)
            label_height = text_height + (padding * 2)
            
            # Try to position the label near the click point but keep it visible
            label_x = rel_x + 10  # Offset from click point
            label_y = rel_y - label_height - 10  # Above the click point
            
            # Adjust if the label would go outside the image
            if label_x + label_width > image_size[0]:
                label_x = rel_x - label_width - 10  # Move to left of click point
            if label_y < 0:
                label_y = rel_y + 10  # Move below the click point
            if label_x < 0:
                label_x = 5  # Move to left edge with small margin
            if label_y + label_height > image_size[1]:
                label_y = image_size[1] - label_height - 5  # Move to bottom with margin
            
            # Draw background rectangle for text
            draw.rectangle([label_x, label_y, label_x + label_width, label_y + label_height], 
                         fill=bg_color, outline=(255, 255, 255, 200), width=1)
            
            # Draw the coordinate text
            text_x = label_x + padding
            text_y = label_y + padding
            
            if font:
                draw.text((text_x, text_y), coord_text, fill=text_color, font=font)
            else:
                draw.text((text_x, text_y), coord_text, fill=text_color)
            
            # Draw a line connecting the label to the click point (if not too close)
            distance = ((label_x + label_width//2 - rel_x)**2 + (label_y + label_height//2 - rel_y)**2)**0.5
            if distance > 20:  # Only draw line if label is far from click point
                # Draw a thin line from label to click point
                line_start_x = label_x + label_width//2
                line_start_y = label_y + label_height//2
                if label_y < rel_y:  # Label is above click point
                    line_start_y = label_y + label_height
                elif label_y > rel_y:  # Label is below click point
                    line_start_y = label_y
                
                draw.line([line_start_x, line_start_y, rel_x, rel_y], 
                         fill=(255, 255, 255, 150), width=1)
                
        except Exception as e:
            # If annotation fails, just log and continue
            self.logger.warning(f"Failed to add absolute coordinate annotation: {str(e)}")
    
    def _create_region_screenshot(self, x: int, y: int, output_path: Path, action_type: str) -> str:
        """Create a screenshot of a region around the specified point."""
        try:
            # Define region around the point - make it larger for better context
            region_size = 400  # Increased from 200 for better context
            screen_width, screen_height = pyautogui.size()
            
            left = max(0, x - region_size // 2)
            top = max(0, y - region_size // 2)
            right = min(screen_width, x + region_size // 2)
            bottom = min(screen_height, y + region_size // 2)
            
            # Take screenshot of region
            region_screenshot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
            
            # Add visual highlighting
            enhanced = region_screenshot.convert("RGBA")
            overlay = Image.new("RGBA", enhanced.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Calculate relative position within the region
            rel_x = x - left
            rel_y = y - top
            
            # Add action indicator based on action type
            if action_type == "click":
                # Red circle for click with white border
                draw.ellipse([rel_x - 12, rel_y - 12, rel_x + 12, rel_y + 12], 
                           fill=(255, 0, 0, 200), outline=(255, 255, 255, 255), width=3)
                # Smaller inner circle for precise location
                draw.ellipse([rel_x - 4, rel_y - 4, rel_x + 4, rel_y + 4], 
                           fill=(255, 255, 255, 255))
            elif action_type == "type":
                # Blue crosshair for text input
                draw.line([rel_x - 15, rel_y, rel_x + 15, rel_y], 
                         fill=(0, 100, 255, 255), width=3)
                draw.line([rel_x, rel_y - 15, rel_x, rel_y + 15], 
                         fill=(0, 100, 255, 255), width=3)
                # Small circle at center
                draw.ellipse([rel_x - 3, rel_y - 3, rel_x + 3, rel_y + 3], 
                           fill=(0, 100, 255, 255))
            else:
                # Generic yellow indicator for other actions
                draw.ellipse([rel_x - 10, rel_y - 10, rel_x + 10, rel_y + 10], 
                           fill=(255, 255, 0, 180), outline=(255, 255, 255, 255), width=2)
            
            # Add coordinate annotation with absolute coordinates
            self._add_absolute_coordinate_annotation(draw, rel_x, rel_y, x, y, enhanced.size, action_type)
            
            # Add a note that this is a fallback screenshot
            try:
                from PIL import ImageFont
                try:
                    font = ImageFont.truetype("arial.ttf", 10)
                except:
                    font = ImageFont.load_default()
            except ImportError:
                font = None
            
            # Add a small note in the corner
            note_text = f"No UI element detected - showing {action_type} location"
            if font:
                note_bbox = draw.textbbox((0, 0), note_text, font=font)
                note_width = note_bbox[2] - note_bbox[0]
                note_height = note_bbox[3] - note_bbox[1]
            else:
                note_width = len(note_text) * 6
                note_height = 11
            
            # Position in bottom-left corner
            note_x = 5
            note_y = enhanced.height - note_height - 5
            
            # Draw semi-transparent background for note
            draw.rectangle([note_x - 2, note_y - 2, note_x + note_width + 2, note_y + note_height + 2], 
                         fill=(0, 0, 0, 120), outline=(255, 255, 255, 100))
            
            # Draw the note text
            if font:
                draw.text((note_x, note_y), note_text, fill=(255, 255, 255, 200), font=font)
            else:
                draw.text((note_x, note_y), note_text, fill=(255, 255, 255, 200))
            
            final_image = Image.alpha_composite(enhanced, overlay)
            final_image.save(str(output_path))
            
            return str(output_path.relative_to(self.macro_package_dir))
            
        except Exception as e:
            self.logger.warning(f"Failed to create region screenshot: {str(e)}")
            return None
    
    def _create_full_ui_screenshot(self, output_path: Path, prefix: str) -> str:
        """Create a full screenshot with UI hierarchy visualization."""
        try:
            if self.screenshot_function:
                # Use the provided screenshot function for full UI analysis
                _, temp_image_path, _ = self.screenshot_function(
                    output_prefix=f"temp_{prefix}",
                    highlight_levels=True,
                    min_size=20,
                    max_depth=3
                )
                
                # Move the image to our package directory
                if temp_image_path and Path(temp_image_path).exists():
                    shutil.move(temp_image_path, str(output_path))
                    return str(output_path.relative_to(self.macro_package_dir))
            
            # Fallback to basic screenshot
            screenshot = pyautogui.screenshot()
            screenshot.save(str(output_path))
            return str(output_path.relative_to(self.macro_package_dir))
            
        except Exception as e:
            self.logger.warning(f"Failed to create full UI screenshot: {str(e)}")
            return None
    
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

    def _get_taskbar_button_name(self, hwnd: int) -> Optional[str]:
        """Try to get the real name of a taskbar button."""
        try:
            import win32gui
            
            # Try to get window text first
            text = win32gui.GetWindowText(hwnd)
            if text and "firefox" in text.lower():
                return "Firefox"
            
            # Try to get class name for clues
            class_name = win32gui.GetClassName(hwnd)
            if "firefox" in class_name.lower():
                return "Firefox"
            
            return text if text else None
            
        except Exception as e:
            self.logger.debug(f"Failed to get taskbar button name: {e}")
            return None