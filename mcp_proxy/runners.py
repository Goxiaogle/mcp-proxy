"""Runners — stdio and SSE proxy execution modes."""

import logging

import mcp.server.stdio

from .proxy_server import create_proxy, make_init_options
from .upstream import connect_upstream

logger = logging.getLogger("mcp-schema-proxy")


async def run_stdio(config: dict):
    """Run proxy in stdio mode (primary)."""
    async with connect_upstream(config) as upstream:
        result = await upstream.list_tools()
        logger.info("Upstream provides %d tools", len(result.tools))

        proxy = create_proxy(upstream)
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("Proxy running in stdio mode")
            await proxy.run(read_stream, write_stream, make_init_options(proxy))


async def run_sse(config: dict, host: str, port: int):
    """Run proxy in SSE server mode (secondary)."""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    import uvicorn

    state: dict = {}
    sse_transport = SseServerTransport("/message")

    async def handle_sse(request):
        proxy = create_proxy(state["upstream"])
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await proxy.run(streams[0], streams[1], make_init_options(proxy))

    async def handle_message(request):
        await sse_transport.handle_post_message(
            request.scope, request.receive, request._send
        )

    async def handle_health(request):
        return JSONResponse({"status": "ok", "upstream": config["type"]})

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/message", endpoint=handle_message, methods=["POST"]),
            Route("/health", endpoint=handle_health),
        ],
    )

    async with connect_upstream(config) as session:
        state["upstream"] = session
        result = await session.list_tools()
        logger.info("Upstream provides %d tools", len(result.tools))
        logger.info("SSE proxy listening at http://%s:%d/sse", host, port)

        server_config = uvicorn.Config(app, host=host, port=port, log_level="info")
        await uvicorn.Server(server_config).serve()
