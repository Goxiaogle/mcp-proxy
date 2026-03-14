"""Upstream connection — connects to MCP servers via stdio or SSE."""

import logging
import os
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger("mcp-schema-proxy")


@asynccontextmanager
async def connect_upstream(config: dict):
    """Connect to upstream MCP server based on config type (stdio or sse)."""
    transport_type = config["type"]

    if transport_type == "stdio":
        # Build env: merge custom env vars into current environment
        custom_env = {
            k: str(v)
            for k, v in (config.get("env") or {}).items()
            if v is not None
        }
        env = {**os.environ, **custom_env} if custom_env else None

        params = StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env=env,
        )
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                logger.info("Connected to upstream via stdio (command: %s)", config["command"])
                yield session

    elif transport_type == "sse":
        from mcp.client.sse import sse_client

        headers = {
            k: v
            for k, v in (config.get("headers") or {}).items()
            if v is not None
        }
        async with sse_client(config["url"], headers=headers) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                logger.info("Connected to upstream via SSE (%s)", config["url"])
                yield session

    else:
        raise ValueError(f"Unsupported transport type: {transport_type}")
