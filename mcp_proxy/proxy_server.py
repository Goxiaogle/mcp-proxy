"""Proxy server factory — creates an MCP Server that proxies to upstream."""

import logging

import mcp.types as types
from mcp import ClientSession
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from .schema_fixer import fix_tools

logger = logging.getLogger("mcp-schema-proxy")


def create_proxy(upstream: ClientSession) -> Server:
    """Create an MCP Server that proxies all requests to upstream with schema fixes."""
    proxy = Server("mcp-schema-proxy")

    @proxy.list_tools()
    async def _list_tools() -> list[types.Tool]:
        result = await upstream.list_tools()
        return fix_tools(result.tools)

    @proxy.call_tool()
    async def _call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        result = await upstream.call_tool(name, arguments)
        return result.content

    @proxy.list_resources()
    async def _list_resources() -> list[types.Resource]:
        try:
            result = await upstream.list_resources()
            return result.resources
        except Exception:
            return []

    @proxy.read_resource()
    async def _read_resource(uri) -> str:
        result = await upstream.read_resource(str(uri))
        content = result.contents[0]
        return content.text if hasattr(content, "text") else str(content)

    @proxy.list_prompts()
    async def _list_prompts() -> list[types.Prompt]:
        try:
            result = await upstream.list_prompts()
            return result.prompts
        except Exception:
            return []

    @proxy.get_prompt()
    async def _get_prompt(
        name: str, arguments: dict[str, str] | None
    ) -> types.GetPromptResult:
        return await upstream.get_prompt(name, arguments)

    return proxy


def make_init_options(server: Server) -> InitializationOptions:
    """Construct initialization options for the proxy server."""
    return InitializationOptions(
        server_name="mcp-schema-proxy",
        server_version="1.0.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
