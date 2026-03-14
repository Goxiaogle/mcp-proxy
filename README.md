# ⚡ MCP Schema Proxy

**[English](./README_EN.md) | 简体中文 | [日本語](./README_JA.md)**

**修复 JetBrains MCP Server 与 Google Gemini（Antigravity）之间的 JSON Schema 兼容性问题。**

提供 **GUI 可视化管理界面**，支持多代理配置、持久化、上游状态检测、一键复制 MCP 配置。

---

## 💥 解决什么问题？

在使用 **Antigravity（Gemini 模型）** 连接 **JetBrains 系列 IDE**（GoLand、IntelliJ IDEA、PyCharm、WebStorm 等）的 MCP 工具时，会遇到以下 **HTTP 400** 报错：

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

### 根因

JetBrains MCP Server 返回的工具定义中，部分 JSON Schema 字段使用了 `enum` 但**没有声明 `type: "string"`**。Gemini 的严格校验器要求 `enum` 必须搭配 `type: "string"` 使用，因此直接拒绝了请求。

### 解决方案

MCP Schema Proxy 作为**透明代理**，拦截上游 `tools/list` 响应，自动修复 Schema 中的兼容性问题：

```
AI Client ←(stdio/sse)→ MCP Schema Proxy ←(stdio/sse)→ JetBrains MCP Server
                              │
                         fix_schema()
                         ├─ enum 补充 type: "string"
                         └─ 递归修复所有嵌套 schema
```

所有其他请求（`tools/call`、`resources/*`、`prompts/*`）完全透明转发，不做任何修改。

---

## 📦 安装

```bash
git clone https://github.com/yourname/mcp-proxy.git
cd mcp-proxy
pip install -r requirements.txt
```

> 依赖：`mcp>=1.0.0`、`starlette>=0.27.0`、`uvicorn>=0.27.0`

---

## 🚀 使用方法

### 启动 GUI

```bash
python mcp_proxy.py
```

### GUI 功能一览

| 功能 | 说明 |
|------|------|
| **添加代理** | 支持直接粘贴 JetBrains MCP 的原始 JSON 配置，自动解析 |
| **多代理管理** | 同时管理多个 IDE / 项目的 MCP 代理 |
| **上游状态检测** | 自动探测上游 MCP 是否在线、提供多少工具 |
| **启动 / 停止** | 单个或一键全部启动 / 停止代理进程 |
| **复制 MCP 配置** | 一键生成 AI 客户端可用的 JSON 配置并复制到剪贴板 |
| **复制总配置** | 一键复制全部代理的合并配置，直接粘贴到 AI 客户端 |
| **持久化** | 配置自动保存到 `~/.mcp-proxy/agents.json` |

---

## 📖 使用教程

### Step 1: 获取 JetBrains MCP 配置

在 JetBrains IDE 中：**Settings → Tools → AI Assistant → MCP**，复制 MCP Server 的配置 JSON。

**SSE 方式示例：**
```json
{
  "type": "sse",
  "url": "http://localhost:64342/sse",
  "headers": {
    "IJ_MCP_SERVER_PROJECT_PATH": "D:\\Projects\\YourProject"
  }
}
```

**Stdio 方式示例：**
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

### Step 2: 在 GUI 中添加代理

1. 启动 GUI：`python mcp_proxy.py`
2. 点击 **「+ 添加代理」**
3. 在 **「📋 粘贴配置」** 标签页中直接粘贴上面的 JSON
4. 点击 **「✅ 解析并填入表单」**，自动识别类型并填充所有字段
5. 调整代理名称（可选），点击 **「保存」**

### Step 3: 检查上游状态

GUI 会自动检测上游 MCP 是否在线以及提供的工具数。确保对应的 JetBrains IDE 已启动且 MCP Server 已开启。

- 🟢 **在线** — 上游 MCP 可达，显示工具数
- 🔴 **离线** — 上游 MCP 不可达，请检查 IDE 是否启动

### Step 4: 复制配置到 AI 客户端

1. 选中代理，点击 **「📋 复制配置」** 复制单个代理配置
2. 或点击 **「📋 复制总配置」** 复制全部代理的合并配置
3. 将复制的 JSON 粘贴到 Antigravity / 其他 AI 客户端的 MCP 配置中

**单个代理配置示例（复制后）：**
```json
{
  "type": "stdio",
  "command": "python",
  "args": ["D:\\Projects\\mcp-proxy\\mcp_proxy\\cli_runner.py", "{...}"]
}
```

**总配置示例（复制后，可直接粘贴到 mcpServers 中）：**
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

### Step 5（可选）: 启动代理

如果使用 SSE 代理模式，需要先在 GUI 中点击 **「▶ 启动」** 或 **「▶▶ 全部启动」**。

使用 Stdio 代理模式（默认）时**无需手动启动**，AI 客户端会自动拉起代理进程。

---

## 🏗️ 项目结构

```
mcp-proxy/
├── mcp_proxy.py              ← 入口：启动 GUI
├── mcp_proxy/
│   ├── __init__.py
│   ├── schema_fixer.py       ← JSON Schema 修复逻辑
│   ├── proxy_server.py       ← MCP 代理 Server 工厂
│   ├── upstream.py           ← 上游 MCP 连接（stdio/SSE）
│   ├── config.py             ← 配置加载
│   ├── runners.py            ← stdio/SSE 运行器
│   ├── agents.py             ← Agent 数据模型 + JSON 持久化
│   ├── gui.py                ← tkinter GUI 界面
│   └── cli_runner.py         ← 内部 CLI（子进程入口）
├── config.example.json       ← 配置示例
└── requirements.txt
```

---

## ❓ FAQ

### 支持哪些 JetBrains IDE？

所有安装了 MCP Server 插件的 JetBrains IDE：GoLand、IntelliJ IDEA、PyCharm、WebStorm、CLion、Rider 等。

### 支持哪些 AI 客户端？

任何支持 MCP 协议的 AI 客户端，包括 Antigravity（Google Gemini）、Claude Desktop、Cursor 等。本项目主要解决 **Gemini 模型**的 Schema 严格校验问题。

### 代理会修改我的请求吗？

不会。代理**仅修改** `tools/list` 返回的工具定义中的 JSON Schema，修复 `enum` 缺少 `type: "string"` 的兼容性问题。所有 `tools/call`、`resources/*`、`prompts/*` 请求完全透明转发。

### 持久化数据存在哪里？

代理配置自动保存到 `~/.mcp-proxy/agents.json`。

---

## 📄 License

MIT
