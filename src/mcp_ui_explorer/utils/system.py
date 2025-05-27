"""System utilities for MCP UI Explorer."""

import os
import sys


def setup_unicode_encoding() -> None:
    """
    Set up Unicode encoding for Windows systems.
    
    Reconfigures stdin, stdout, and stderr to use UTF-8 encoding
    to avoid UnicodeEncodeError issues on Windows systems.
    """
    if sys.platform == "win32" and os.environ.get('PYTHONIOENCODING') is None:
        try:
            sys.stdin.reconfigure(encoding="utf-8")
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except AttributeError:
            # Python < 3.7 doesn't have reconfigure method
            pass 