"""UI Explorer for MCP - Production Ready Modular Package."""

__version__ = "0.1.17"

# Import from the new modular structure
from .core.ui_explorer import UIExplorer
from .server.mcp_server import create_server, run_server, ServerWrapper

# Create a wrapper instance for compatibility
wrapper = ServerWrapper()

# For backward compatibility with existing entry points
mcp = wrapper

# Main entry point function
async def main():
    """Main entry point for the MCP UI Explorer server."""
    await run_server()

__all__ = ['UIExplorer', 'main', 'wrapper', 'mcp', 'create_server', 'run_server', 'ServerWrapper'] 