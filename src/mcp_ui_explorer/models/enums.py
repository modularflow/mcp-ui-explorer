"""Enums for MCP UI Explorer."""

from enum import Enum


class RegionType(str, Enum):
    """Predefined regions for UI analysis."""
    
    SCREEN = "screen"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"


class ControlType(str, Enum):
    """UI control types for filtering."""
    
    BUTTON = "Button"
    TEXT = "Text"
    EDIT = "Edit"
    CHECKBOX = "CheckBox"
    RADIOBUTTON = "RadioButton"
    COMBOBOX = "ComboBox"
    LIST = "List"
    LISTITEM = "ListItem"
    MENU = "Menu"
    MENUITEM = "MenuItem"
    TREE = "Tree"
    TREEITEM = "TreeItem"
    TOOLBAR = "ToolBar"
    TAB = "Tab"
    TABITEM = "TabItem"
    WINDOW = "Window"
    DIALOG = "Dialog"
    PANE = "Pane"
    GROUP = "Group"
    DOCUMENT = "Document"
    STATUSBAR = "StatusBar"
    IMAGE = "Image"
    HYPERLINK = "Hyperlink"


class MacroState(str, Enum):
    """Macro recording states."""
    
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"


class MacroEventType(str, Enum):
    """Types of events that can be recorded in a macro."""
    
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    MOUSE_SCROLL = "mouse_scroll"
    MOUSE_DRAG = "mouse_drag"
    KEYBOARD_TYPE = "keyboard_type"
    KEYBOARD_KEY = "keyboard_key"
    KEYBOARD_HOTKEY = "keyboard_hotkey"
    UI_CHANGE = "ui_change"
    SCREENSHOT = "screenshot"
    WAIT = "wait" 