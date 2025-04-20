### Available Tools
- explore_ui: Explore UI elements hierarchically and return the hierarchy data.
    Input Schema:
		{
      "type": "object",
      "properties": {
        "region": {
          "anyOf": [
            {
              "$ref": "#/$defs/RegionType"
            },
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Region to analyze: predefined regions or custom 'left,top,right,bottom' coordinates",
          "title": "Region"
        },
        "depth": {
          "default": 5,
          "description": "Maximum depth to analyze",
          "title": "Depth",
          "type": "integer"
        },
        "min_size": {
          "default": 5,
          "description": "Minimum element size to include",
          "title": "Min Size",
          "type": "integer"
        },
        "focus_window": {
          "default": false,
          "description": "Only analyze the foreground window",
          "title": "Focus Window",
          "type": "boolean"
        },
        "visible_only": {
          "default": true,
          "description": "Only include elements visible on screen",
          "title": "Visible Only",
          "type": "boolean"
        },
        "control_type": {
          "allOf": [
            {
              "$ref": "#/$defs/ControlType"
            }
          ],
          "default": "Button",
          "description": "Only include elements of this control type (default: Button)",
          "title": "Control Type"
        },
        "text": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Only include elements containing this text (case-insensitive, partial match)",
          "title": "Text"
        }
      },
      "$defs": {
        "RegionType": {
          "enum": [
            "screen",
            "top",
            "bottom",
            "left",
            "right",
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right"
          ],
          "title": "RegionType",
          "type": "string"
        },
        "ControlType": {
          "enum": [
            "Button",
            "Text",
            "Edit",
            "CheckBox",
            "RadioButton",
            "ComboBox",
            "List",
            "ListItem",
            "Menu",
            "MenuItem",
            "Tree",
            "TreeItem",
            "ToolBar",
            "Tab",
            "TabItem",
            "Window",
            "Dialog",
            "Pane",
            "Group",
            "Document",
            "StatusBar",
            "Image",
            "Hyperlink"
          ],
          "title": "ControlType",
          "type": "string"
        }
      },
      "title": "ExploreUIInput"
    }

- screenshot_ui: Take a screenshot with UI elements highlighted and return it as an image.
    Input Schema:
		{
      "type": "object",
      "properties": {
        "region": {
          "anyOf": [
            {
              "$ref": "#/$defs/RegionType"
            },
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Region to analyze: predefined regions or custom 'left,top,right,bottom' coordinates",
          "title": "Region"
        },
        "highlight_levels": {
          "default": true,
          "description": "Use different colors for hierarchy levels",
          "title": "Highlight Levels",
          "type": "boolean"
        },
        "output_prefix": {
          "default": "ui_hierarchy",
          "description": "Prefix for output files",
          "title": "Output Prefix",
          "type": "string"
        },
        "control_type": {
          "allOf": [
            {
              "$ref": "#/$defs/ControlType"
            }
          ],
          "default": "Button",
          "description": "Only include elements of this control type (default: Button)",
          "title": "Control Type"
        },
        "text": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Only include elements containing this text (case-insensitive, partial match)",
          "title": "Text"
        }
      },
      "$defs": {
        "RegionType": {
          "enum": [
            "screen",
            "top",
            "bottom",
            "left",
            "right",
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right"
          ],
          "title": "RegionType",
          "type": "string"
        },
        "ControlType": {
          "enum": [
            "Button",
            "Text",
            "Edit",
            "CheckBox",
            "RadioButton",
            "ComboBox",
            "List",
            "ListItem",
            "Menu",
            "MenuItem",
            "Tree",
            "TreeItem",
            "ToolBar",
            "Tab",
            "TabItem",
            "Window",
            "Dialog",
            "Pane",
            "Group",
            "Document",
            "StatusBar",
            "Image",
            "Hyperlink"
          ],
          "title": "ControlType",
          "type": "string"
        }
      },
      "title": "ScreenshotUIInput"
    }

- click_ui_element: Click on a UI element based on search criteria.
    Input Schema:
		{
      "type": "object",
      "properties": {
        "control_type": {
          "anyOf": [
            {
              "$ref": "#/$defs/ControlType"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Control type to search for (e.g., 'Button')"
        },
        "text": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Text content to search for",
          "title": "Text"
        },
        "element_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Path to element (e.g., '0.children.3.children.2')",
          "title": "Element Path"
        },
        "wait_time": {
          "default": 2,
          "description": "Seconds to wait before clicking",
          "title": "Wait Time",
          "type": "number"
        },
        "hierarchy_data": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "Hierarchy data from explore_ui (if not provided, will run explore_ui)",
          "title": "Hierarchy Data"
        }
      },
      "required": ["control_type"],
      "$defs": {
        "ControlType": {
          "enum": [
            "Button",
            "Text",
            "Edit",
            "CheckBox",
            "RadioButton",
            "ComboBox",
            "List",
            "ListItem",
            "Menu",
            "MenuItem",
            "Tree",
            "TreeItem",
            "ToolBar",
            "Tab",
            "TabItem",
            "Window",
            "Dialog",
            "Pane",
            "Group",
            "Document",
            "StatusBar",
            "Image",
            "Hyperlink"
          ],
          "title": "ControlType",
          "type": "string"
        }
      },
      "title": "ClickUIElementInput"
    }

- keyboard_input: Send keyboard input (type text).
    Input Schema:
		{
      "type": "object",
      "properties": {
        "text": {
          "description": "Text to type",
          "title": "Text",
          "type": "string"
        },
        "delay": {
          "default": 0.1,
          "description": "Delay before starting to type in seconds",
          "title": "Delay",
          "type": "number"
        },
        "interval": {
          "default": 0,
          "description": "Interval between characters in seconds",
          "title": "Interval",
          "type": "number"
        },
        "press_enter": {
          "default": false,
          "description": "Whether to press Enter after typing",
          "title": "Press Enter",
          "type": "boolean"
        }
      },
      "required": [
        "text"
      ],
      "title": "KeyboardInputInput"
    }

- press_key: Press a specific keyboard key (like Enter, Tab, Escape, etc.)
    Input Schema:
		{
      "type": "object",
      "properties": {
        "key": {
          "description": "Key to press (e.g., 'enter', 'tab', 'esc', 'space', 'backspace', 'delete', etc.)",
          "title": "Key",
          "type": "string"
        },
        "delay": {
          "default": 0.1,
          "description": "Delay before pressing key in seconds",
          "title": "Delay",
          "type": "number"
        },
        "presses": {
          "default": 1,
          "description": "Number of times to press the key",
          "title": "Presses",
          "type": "integer"
        },
        "interval": {
          "default": 0,
          "description": "Interval between keypresses in seconds",
          "title": "Interval",
          "type": "number"
        }
      },
      "required": [
        "key"
      ],
      "title": "PressKeyInput"
    }

- hot_key: Press a keyboard shortcut combination (like Ctrl+C, Alt+Tab, etc.)
    Input Schema:
		{
      "type": "object",
      "properties": {
        "keys": {
          "description": "List of keys to press together (e.g., ['ctrl', 'c'] for Ctrl+C)",
          "items": {
            "type": "string"
          },
          "title": "Keys",
          "type": "array"
        },
        "delay": {
          "default": 0.1,
          "description": "Delay before pressing keys in seconds",
          "title": "Delay",
          "type": "number"
        }
      },
      "required": [
        "keys"
      ],
      "title": "HotKeyInput"
    } 