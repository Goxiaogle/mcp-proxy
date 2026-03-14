#!/usr/bin/env python3
"""
MCP Schema Proxy Manager — GUI for managing MCP proxy agents.

Usage:
  python mcp_proxy.py
"""

import sys
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if len(sys.argv) > 1 and sys.argv[1] == "--cli-runner":
        sys.argv.pop(1)
        from mcp_proxy.cli_runner import main
        sys.exit(main())
    else:
        from mcp_proxy.gui import run_gui
        run_gui()
