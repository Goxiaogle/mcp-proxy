@echo off
REM ── Build MCP Schema Proxy Windows EXE ──
REM Produces: dist\mcp-proxy.exe (one-file build)

cd /d "%~dp0"

echo === Building MCP Schema Proxy ===

.venv\Scripts\pyinstaller.exe ^
    --name "mcp-proxy" ^
    --windowed ^
    --onefile ^
    --noconfirm ^
    --clean ^
    --hidden-import mcp ^
    --hidden-import mcp.types ^
    --hidden-import mcp.server ^
    --hidden-import mcp.server.stdio ^
    --hidden-import mcp.server.sse ^
    --hidden-import mcp.server.models ^
    --hidden-import mcp.client ^
    --hidden-import mcp.client.sse ^
    --hidden-import mcp.client.stdio ^
    --hidden-import starlette ^
    --hidden-import starlette.applications ^
    --hidden-import starlette.responses ^
    --hidden-import starlette.routing ^
    --hidden-import uvicorn ^
    --hidden-import anyio ^
    --hidden-import anyio._backends ^
    --hidden-import anyio._backends._asyncio ^
    --hidden-import httpx ^
    --hidden-import httpx_sse ^
    --hidden-import sse_starlette ^
    --hidden-import pydantic ^
    --exclude-module mcp.cli ^
    --exclude-module typer ^
    mcp_proxy.py

if %ERRORLEVEL% neq 0 (
    echo === Build FAILED ===
    exit /b 1
)

echo === Build complete ===
echo Output: dist\mcp-proxy.exe
