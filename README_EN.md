# ⚡ MCP Schema Proxy

**English | [简体中文](./README.md) | [日本語](./README_JA.md)**

**Fixes JSON Schema compatibility issues between JetBrains MCP Server and Google Gemini (Antigravity).**

Provides a **GUI-based visual management interface** with multi-agent support, persistence, upstream status detection, and one-click MCP config copy.

---

## 💥 What Problem Does It Solve?

When using **Antigravity (Gemini model)** to connect to **JetBrains IDEs** (GoLand, IntelliJ IDEA, PyCharm, WebStorm, etc.) via MCP tools, you encounter the following **HTTP 400** error:

```
Error: HTTP 400 Bad Request

{
  "error": {
    "code": 400,
    "message": "* GenerateContentRequest.tools[11].function_declarations[0]
                .parameters.properties[truncateMode].enum:
                only allowed for STRING type\n",
    "status": "INVALID_ARGUMENT"
  }
}
```

### Root Cause

The tool definitions returned by JetBrains MCP Server contain JSON Schema fields that use `enum` **without declaring `type: "string"`**. Gemini's strict validator requires `enum` to be paired with `type: "string"`, so it rejects the request outright.

### Solution

MCP Schema Proxy acts as a **transparent proxy**, intercepting upstream `tools/list` responses and automatically fixing Schema compatibility issues:

```
AI Client ←(stdio/sse)→ MCP Schema Proxy ←(stdio/sse)→ JetBrains MCP Server
                              │
                         fix_schema()
                         ├─ Injects type: "string" for enum fields
                         └─ Recursively fixes all nested schemas
```

All other requests (`tools/call`, `resources/*`, `prompts/*`) are forwarded transparently without any modification.

---

## 📦 Installation

```bash
git clone https://github.com/yourname/mcp-proxy.git
cd mcp-proxy
pip install -r requirements.txt
```

> Dependencies: `mcp>=1.0.0`, `starlette>=0.27.0`, `uvicorn>=0.27.0`

---

## 🚀 Usage

### Launch the GUI

```bash
python mcp_proxy.py
```

### GUI Features

| Feature | Description |
|---------|-------------|
| **Add Agent** | Paste raw JetBrains MCP JSON config directly, auto-parsed |
| **Multi-Agent** | Manage multiple IDE / project MCP proxies simultaneously |
| **Upstream Detection** | Auto-detect whether upstream MCP is online and how many tools it provides |
| **Start / Stop** | Start or stop individual agents, or batch start/stop all |
| **Copy MCP Config** | One-click generate and copy the JSON config for your AI client |
| **Copy Combined Config** | One-click copy all agents' merged config for pasting into AI client |
| **Persistence** | Configs auto-saved to `~/.mcp-proxy/agents.json` |

---

## 📖 Tutorial

### Step 1: Get JetBrains MCP Config

In your JetBrains IDE: **Settings → Tools → AI Assistant → MCP**, copy the MCP Server configuration JSON.

**SSE example:**
```json
{
  "type": "sse",
  "url": "http://localhost:64342/sse",
  "headers": {
    "IJ_MCP_SERVER_PROJECT_PATH": "D:\\Projects\\YourProject"
  }
}
```

**Stdio example:**
```json
{
  "type": "stdio",
  "env": {
    "IJ_MCP_SERVER_PORT": "64342"
  },
  "command": "D:\\Jetbrains\\GoLand\\jbr\\bin\\java",
  "args": [
    "-classpath",
    "D:\\Jetbrains\\GoLand\\plugins\\mcpserver\\lib\\mcpserver-frontend.jar;...",
    "com.intellij.mcpserver.stdio.McpStdioRunnerKt"
  ]
}
```

### Step 2: Add an Agent in the GUI

1. Launch the GUI: `python mcp_proxy.py`
2. Click **"+ Add Agent"**
3. In the **"📋 Paste Config"** tab, paste the JSON directly
4. Click **"✅ Parse & Fill Form"** — type is auto-detected and all fields are populated
5. Adjust the agent name (optional), click **"Save"**

### Step 3: Check Upstream Status

The GUI automatically detects whether the upstream MCP is online and how many tools it exposes. Make sure the corresponding JetBrains IDE is running with MCP Server enabled.

- 🟢 **Online** — upstream MCP is reachable, tool count is displayed
- 🔴 **Offline** — upstream MCP is unreachable, check if the IDE is running

### Step 4: Copy Config to AI Client

1. Select an agent, click **"📋 Copy Config"** for a single agent's config
2. Or click **"📋 Copy Combined Config"** for all agents' merged config
3. Paste the JSON into Antigravity / your AI client's MCP settings

**Single agent config example (after copy):**
```json
{
  "type": "stdio",
  "command": "python",
  "args": ["D:\\Projects\\mcp-proxy\\mcp_proxy\\cli_runner.py", "{...}"]
}
```

**Combined config example (paste directly into mcpServers):**
```
"GoLand": {
  "type": "stdio",
  "command": "python",
  "args": [...]
},
"PyCharm": {
  "type": "stdio",
  "command": "python",
  "args": [...]
}
```

### Step 5 (Optional): Start the Proxy

If using SSE proxy mode, click **"▶ Start"** or **"▶▶ Start All"** in the GUI first.

When using Stdio proxy mode (default), **no manual start is needed** — the AI client will automatically spawn the proxy process.

---

## 🏗️ Project Structure

```
mcp-proxy/
├── mcp_proxy.py              ← Entry point: launches GUI
├── mcp_proxy/
│   ├── __init__.py
│   ├── schema_fixer.py       ← JSON Schema fix logic
│   ├── proxy_server.py       ← MCP proxy Server factory
│   ├── upstream.py           ← Upstream MCP connection (stdio/SSE)
│   ├── config.py             ← Config loading
│   ├── runners.py            ← stdio/SSE runners
│   ├── agents.py             ← Agent data model + JSON persistence
│   ├── gui.py                ← tkinter GUI interface
│   └── cli_runner.py         ← Internal CLI (subprocess entry point)
├── config.example.json       ← Example config
└── requirements.txt
```

---

## ❓ FAQ

### Which JetBrains IDEs are supported?

All JetBrains IDEs with the MCP Server plugin: GoLand, IntelliJ IDEA, PyCharm, WebStorm, CLion, Rider, etc.

### Which AI clients are supported?

Any MCP-compatible AI client, including Antigravity (Google Gemini), Claude Desktop, Cursor, etc. This project primarily addresses the **Gemini model's** strict Schema validation issue.

### Does the proxy modify my requests?

No. The proxy **only modifies** the JSON Schema in tool definitions returned by `tools/list`, fixing the `enum` missing `type: "string"` compatibility issue. All `tools/call`, `resources/*`, `prompts/*` requests are forwarded transparently.

### Where is persistent data stored?

Agent configs are automatically saved to `~/.mcp-proxy/agents.json`.

---

## 📄 License

MIT
