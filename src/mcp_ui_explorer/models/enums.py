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