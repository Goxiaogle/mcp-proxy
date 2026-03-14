#!/usr/bin/env python3
"""Internal CLI runner — launched by GUI as subprocess. Not for direct use."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `mcp_proxy` package can be imported
# when this script is invoked directly as a subprocess.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_proxy.config import load_config
from mcp_proxy.runners import run_stdio, run_sse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Upstream config (inline JSON or file path)")
    parser.add_argument("--sse", action="store_true")
    parser.add_argument("--port", type=int, default=3100)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    config = load_config(args.config)
    if args.sse:
        asyncio.run(run_sse(config, args.host, args.port))
    else:
        asyncio.run(run_stdio(config))


if __name__ == "__main__":
    main()
