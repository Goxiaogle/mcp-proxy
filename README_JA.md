# ⚡ MCP Schema Proxy

**[English](./README_EN.md) | [简体中文](./README.md) | 日本語**

**JetBrains MCP Server と Google Gemini（Antigravity）間の JSON Schema 互換性問題を修正します。**

**GUI ビジュアル管理インターフェース**を提供し、マルチエージェント設定、永続化、上流ステータス検出、ワンクリック MCP 設定コピーに対応しています。

---

## 💥 どんな問題を解決するのか？

**Antigravity（Gemini モデル）** で **JetBrains 系 IDE**（GoLand、IntelliJ IDEA、PyCharm、WebStorm など）の MCP ツールに接続する際、以下の **HTTP 400** エラーが発生します：

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

### 根本原因

JetBrains MCP Server が返すツール定義の JSON Schema で、`enum` が使用されているにもかかわらず **`type: "string"` が宣言されていません**。Gemini の厳格なバリデーターは `enum` に `type: "string"` を必須としているため、リクエストが拒否されます。

### 解決策

MCP Schema Proxy は**透過プロキシ**として動作し、上流の `tools/list` レスポンスをインターセプトして Schema の互換性問題を自動修正します：

```
AI Client ←(stdio/sse)→ MCP Schema Proxy ←(stdio/sse)→ JetBrains MCP Server
                              │
                         fix_schema()
                         ├─ enum に type: "string" を補完
                         └─ すべてのネストされた schema を再帰的に修正
```

その他のリクエスト（`tools/call`、`resources/*`、`prompts/*`）はすべて透過的に転送され、一切変更されません。

---

## 📦 インストール

```bash
git clone https://github.com/yourname/mcp-proxy.git
cd mcp-proxy
pip install -r requirements.txt
```

> 依存関係：`mcp>=1.0.0`、`starlette>=0.27.0`、`uvicorn>=0.27.0`

---

## 🚀 使い方

### GUI の起動

```bash
python mcp_proxy.py
```

### GUI 機能一覧

| 機能 | 説明 |
|------|------|
| **エージェント追加** | JetBrains MCP の生の JSON 設定を直接貼り付け、自動解析 |
| **マルチエージェント** | 複数の IDE / プロジェクトの MCP プロキシを同時管理 |
| **上流ステータス検出** | 上流 MCP がオンラインか、ツール数を自動検出 |
| **起動 / 停止** | 個別またはワンクリックで全エージェントを起動 / 停止 |
| **MCP 設定コピー** | ワンクリックで AI クライアント用の JSON 設定を生成しクリップボードにコピー |
| **統合設定コピー** | 全エージェントの統合設定をワンクリックでコピー |
| **永続化** | 設定は `~/.mcp-proxy/agents.json` に自動保存 |

---

## 📖 チュートリアル

### Step 1: JetBrains MCP 設定を取得

JetBrains IDE で：**Settings → Tools → AI Assistant → MCP** から MCP Server 設定の JSON をコピーします。

**SSE の例：**
```json
{
  "type": "sse",
  "url": "http://localhost:64342/sse",
  "headers": {
    "IJ_MCP_SERVER_PROJECT_PATH": "D:\\Projects\\YourProject"
  }
}
```

**Stdio の例：**
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

### Step 2: GUI でエージェントを追加

1. GUI を起動：`python mcp_proxy.py`
2. **「+ エージェント追加」** をクリック
3. **「📋 設定貼り付け」** タブに JSON を直接貼り付け
4. **「✅ 解析してフォームに入力」** をクリック — タイプが自動検出され、すべてのフィールドが入力されます
5. エージェント名を調整（任意）、**「保存」** をクリック

### Step 3: 上流ステータスを確認

GUI は上流 MCP がオンラインか、ツール数を自動検出します。対応する JetBrains IDE が起動し、MCP Server が有効になっていることを確認してください。

- 🟢 **オンライン** — 上流 MCP に到達可能、ツール数を表示
- 🔴 **オフライン** — 上流 MCP に到達不可、IDE が起動しているか確認してください

### Step 4: AI クライアントに設定をコピー

1. エージェントを選択し、**「📋 設定コピー」** で単一エージェントの設定をコピー
2. または **「📋 統合設定コピー」** で全エージェントの統合設定をコピー
3. コピーした JSON を Antigravity / AI クライアントの MCP 設定に貼り付け

### Step 5（オプション）: プロキシを起動

SSE プロキシモードを使用する場合、GUI で **「▶ 起動」** または **「▶▶ 全て起動」** をクリックしてください。

Stdio プロキシモード（デフォルト）では**手動起動は不要**です。AI クライアントが自動的にプロキシプロセスを起動します。

---

## 🏗️ プロジェクト構造

```
mcp-proxy/
├── mcp_proxy.py              ← エントリポイント：GUI 起動
├── mcp_proxy/
│   ├── __init__.py
│   ├── schema_fixer.py       ← JSON Schema 修正ロジック
│   ├── proxy_server.py       ← MCP プロキシ Server ファクトリ
│   ├── upstream.py           ← 上流 MCP 接続（stdio/SSE）
│   ├── config.py             ← 設定読み込み
│   ├── runners.py            ← stdio/SSE ランナー
│   ├── agents.py             ← Agent データモデル + JSON 永続化
│   ├── gui.py                ← tkinter GUI インターフェース
│   └── cli_runner.py         ← 内部 CLI（サブプロセスエントリポイント）
├── config.example.json       ← 設定例
└── requirements.txt
```

---

## ❓ FAQ

### どの JetBrains IDE に対応していますか？

MCP Server プラグインがインストールされたすべての JetBrains IDE：GoLand、IntelliJ IDEA、PyCharm、WebStorm、CLion、Rider など。

### どの AI クライアントに対応していますか？

MCP プロトコル対応のすべての AI クライアント：Antigravity（Google Gemini）、Claude Desktop、Cursor など。本プロジェクトは主に **Gemini モデル**の厳格な Schema 検証問題を解決します。

### プロキシはリクエストを変更しますか？

いいえ。プロキシは `tools/list` が返すツール定義の JSON Schema **のみを変更**し、`enum` に `type: "string"` がない互換性問題を修正します。`tools/call`、`resources/*`、`prompts/*` のすべてのリクエストは透過的に転送されます。

### 永続化データはどこに保存されますか？

エージェント設定は `~/.mcp-proxy/agents.json` に自動保存されます。

---

## 📄 License

MIT
