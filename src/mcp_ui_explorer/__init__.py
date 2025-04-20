"""UI Explorer for MCP."""

__version__ = "0.1.6"

from .mcp_ui_explorer import main, ServerWrapper

# Create a wrapper instance for compatibility
wrapper = ServerWrapper()

# For backward compatibility with existing entry points
mcp = wrapper

__all__ = ['main', 'wrapper', 'mcp'] 