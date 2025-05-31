"""Input models for MCP UI Explorer tools."""

from typing import Optional, List, Union, Literal
from pydantic import BaseModel, Field

from .enums import RegionType, ControlType, MacroState


class ExploreUIInput(BaseModel):
    """Input model for explore_ui tool."""
    
    region: Optional[Union[RegionType, str]] = Field(
        default=None, 
        description="Region to analyze: predefined regions or custom 'left,top,right,bottom' coordinates"
    )
    depth: int = Field(default=8, description="Maximum depth to analyze")
    min_size: int = Field(default=5, description="Minimum element size to include")
    focus_window: bool = Field(default=False, description="Only analyze the foreground window")
    visible_only: bool = Field(default=True, description="Only include elements visible on screen")
    control_type: ControlType = Field(default=ControlType.BUTTON, description="Only include elements of this control type (default: ALL)")
    text: Optional[str] = Field(default=None, description="Only include elements containing this text (case-insensitive, partial match)")


class FindNearCursorInput(BaseModel):
    """Input model for find_elements_near_cursor tool."""
    
    max_distance: int = Field(default=100, description="Maximum distance from cursor to include elements")
    control_type: Optional[ControlType] = Field(default=None, description="Only include elements of this control type")
    limit: int = Field(default=5, description="Maximum number of elements to return")


class ScreenshotUIInput(BaseModel):
    """Input model for screenshot_ui tool."""
    
    focus_only: bool = Field(default=True, description="Only analyze the foreground window")
    highlight_levels: bool = Field(default=True, description="Use different colors for hierarchy levels")
    max_depth: int = Field(default=4, description="Maximum depth to analyze (default: 4)")
    min_size: int = Field(default=20, description="Minimum element size to include (default: 20)")
    output_prefix: str = Field(default="ui_hierarchy", description="Prefix for output files")
    region: Optional[str] = Field(default=None, description="Region to analyze: predefined regions or custom 'left,top,right,bottom' coordinates")


class ClickUIElementInput(BaseModel):
    """Input model for click_ui_element tool."""
    
    x: float = Field(description="X coordinate to click (absolute pixels or normalized 0-1)")
    y: float = Field(description="Y coordinate to click (absolute pixels or normalized 0-1)")
    normalized: bool = Field(default=False, description="Whether coordinates are normalized (0-1) or absolute pixels")
    wait_time: float = Field(default=2.0, description="Seconds to wait before clicking")
    auto_verify: bool = Field(default=True, description="Automatically verify the click action using UI-TARS")
    verification_query: Optional[str] = Field(default=None, description="What to look for to verify the click worked (auto-generated if not provided)")
    verification_timeout: float = Field(default=3.0, description="How long to wait for verification (seconds)")


class KeyboardInputInput(BaseModel):
    """Input model for keyboard_input tool."""
    
    text: str = Field(description="Text to type")
    delay: float = Field(default=0.1, description="Delay before starting to type in seconds")
    interval: float = Field(default=0.0, description="Interval between characters in seconds")
    press_enter: bool = Field(default=False, description="Whether to press Enter after typing")
    auto_verify: bool = Field(default=True, description="Automatically verify the typing action using UI-TARS")
    verification_query: Optional[str] = Field(default=None, description="What to look for to verify the typing worked (auto-generated if not provided)")
    verification_timeout: float = Field(default=3.0, description="How long to wait for verification (seconds)")


class PressKeyInput(BaseModel):
    """Input model for press_key tool."""
    
    key: str = Field(description="Key to press (e.g., 'enter', 'tab', 'esc', 'space', 'backspace', 'delete', etc.)")
    delay: float = Field(default=0.1, description="Delay before pressing key in seconds")
    presses: int = Field(default=1, description="Number of times to press the key")
    interval: float = Field(default=0.0, description="Interval between keypresses in seconds")
    auto_verify: bool = Field(default=True, description="Automatically verify the key press action using UI-TARS")
    verification_query: Optional[str] = Field(default=None, description="What to look for to verify the key press worked (auto-generated if not provided)")
    verification_timeout: float = Field(default=3.0, description="How long to wait for verification (seconds)")


class HotKeyInput(BaseModel):
    """Input model for hot_key tool."""
    
    keys: List[str] = Field(description="List of keys to press together (e.g., ['ctrl', 'c'] for Ctrl+C)")
    delay: float = Field(default=0.1, description="Delay before pressing keys in seconds")
    auto_verify: bool = Field(default=True, description="Automatically verify the hotkey action using UI-TARS")
    verification_query: Optional[str] = Field(default=None, description="What to look for to verify the hotkey worked (auto-generated if not provided)")
    verification_timeout: float = Field(default=3.0, description="How long to wait for verification (seconds)")


class UITarsInput(BaseModel):
    """Input model for ui_tars_analyze tool with multi-provider support."""
    
    image_path: str = Field(description="Path to the screenshot image to analyze")
    query: str = Field(description="Description of what to find on the screen (e.g., 'the login button', 'the search box')")
    
    # Provider configuration (optional overrides)
    provider: Optional[Literal["openai", "anthropic", "azure", "local", "custom"]] = Field(
        default=None, 
        description="AI provider to use (overrides config default)"
    )
    api_url: Optional[str] = Field(
        default=None, 
        description="Base URL for the AI API (overrides config default)"
    )
    api_key: Optional[str] = Field(
        default=None, 
        description="API key for authentication (overrides config default)"
    )
    model_name: Optional[str] = Field(
        default=None, 
        description="Name of the model to use (overrides config default)"
    )
    
    # Legacy fields for backward compatibility
    # These will be deprecated in favor of the provider-specific configuration
    # but kept for now to maintain compatibility with existing code
    # api_url: str = Field(default="http://127.0.0.1:1234/v1", description="Base URL for the UI-TARS API")
    # model_name: str = Field(default="ui-tars-7b-dpo", description="Name of the UI-TARS model to use")


class UIVerificationInput(BaseModel):
    """Input model for verify_ui_action tool."""
    
    action_description: str = Field(description="Description of the action that was performed")
    expected_result: str = Field(description="What should have happened (e.g., 'window should open', 'text should appear')")
    verification_query: str = Field(description="What to look for in the screenshot to verify success")
    timeout: float = Field(default=3.0, description="How long to wait for the change to occur (seconds)")
    comparison_image: Optional[str] = Field(default=None, description="Optional: path to before image for comparison")


class CreateMemorySummaryInput(BaseModel):
    """Input model for create_memory_summary tool."""
    
    force_summary: bool = Field(default=False, description="Force creation of summary even if context threshold not reached")


class DocumentStepInput(BaseModel):
    """Input model for document_step tool."""
    
    step_description: str = Field(description="Description of the current step being attempted")
    mark_previous_complete: bool = Field(default=False, description="Mark the previous step as completed")
    completion_notes: str = Field(default="", description="Notes about the previous step completion")


class GetStepStatusInput(BaseModel):
    """Input model for get_step_status tool."""
    
    show_all_steps: bool = Field(default=False, description="Show all planned steps, not just current")


class StartMacroRecordingInput(BaseModel):
    """Input model for start_macro_recording tool."""
    
    macro_name: str = Field(description="Name for the macro being recorded")
    description: Optional[str] = Field(default=None, description="Optional description of what the macro does")
    capture_ui_context: bool = Field(default=True, description="Whether to capture UI element information during recording")
    capture_screenshots: bool = Field(default=True, description="Whether to take screenshots at key moments")
    mouse_move_threshold: float = Field(default=50.0, description="Minimum distance in pixels to record mouse movements")
    keyboard_commit_events: List[str] = Field(
        default=["enter", "tab", "escape"], 
        description="Keys that trigger text commit events (e.g., when user finishes typing in a field)"
    )


class StopMacroRecordingInput(BaseModel):
    """Input model for stop_macro_recording tool."""
    
    save_macro: bool = Field(default=True, description="Whether to save the recorded macro")
    output_format: Literal["json", "python", "both"] = Field(default="both", description="Format to save the macro in")


class PauseMacroRecordingInput(BaseModel):
    """Input model for pause_macro_recording tool."""
    
    pause: bool = Field(default=True, description="True to pause, False to resume recording")


class GetMacroStatusInput(BaseModel):
    """Input model for get_macro_status tool."""
    
    include_events: bool = Field(default=False, description="Whether to include the recorded events in the response")


class PlayMacroInput(BaseModel):
    """Input model for play_macro tool."""
    
    macro_path: str = Field(description="Path to the macro file to play")
    speed_multiplier: float = Field(default=1.0, description="Speed multiplier for playback (1.0 = normal speed)")
    verify_ui_context: bool = Field(default=True, description="Whether to verify UI context matches before executing actions")
    stop_on_verification_failure: bool = Field(default=True, description="Whether to stop playback if UI verification fails") 