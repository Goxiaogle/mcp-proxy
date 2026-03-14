# 🎉 Release v1.0.0: First Official Release

We are excited to announce the first official release of the **MCP Proxy Manager**! 🚀

This release brings a complete, user-friendly graphical interface and a single-file executable designed to seamlessly solve compatibility issues between standard AI clients (especially JetBrains IDEs) and powerful models like Antigravity / Gemini.

## 🌟 Highlights

*   **📦 Ready-to-use Standalone Executable**: No Python environment needed! Just download `mcp-proxy.exe` and double-click to run on Windows.
*   **🧠 JetBrains & Gemini Compatibility Fix**: Completely resolves the `INVALID_ARGUMENT` (`truncateMode` enum error) that occurs when JetBrains products attempt to use MCP tools with the Antigravity-Gemini model. We intercept and properly format the schemas on the fly!
*   **🖥️ Intuitive GUI Manager**: Easily add, edit, and manage multiple MCP agent configurations.
*   **📋 One-Click "Copy Config"**: Click a single button to copy the perfectly formatted JSON configuration block directly into your JetBrains IDE setup—no manual JSON editing required.
*   **🌐 Multi-Language Support**: Documentation and guidance now fully available in English, 简体中文, and 日本語.
*   **🔄 Smart Execution Modes**: 
    *   **Stdio Mode**: Seamlessly delegates the background process lifecycle to your client IDE. 
    *   **SSE Mode**: Start and stop persistent background SSE servers with just a click.

## 🛠️ Fixes & Improvements
*   Resolved an issue where PyInstaller-packaged background processes would silently crash (Exit Code 0) due to `stdin` EOF handling in Windows detached console environments.
*   Improved GUI feedback to explicitly clarify that **Stdio** agents do not need to be manually started in the background manager, preventing user confusion.
*   Refactored the core payload interceptor (`schema_fixer`) to cleanly strip invalid `enum` type restrictions specifically for `STRING` parameters when proxying tool definitions.

## 📥 Installation & Usage

1. Go to the **Assets** section below and download `mcp-proxy.exe` for Windows.
2. Double-click the executable to open the MCP Proxy Manager.
3. Click "新建代理 (New Agent)" to add your target MCP server details.
4. Click the copy icon 📋, paste the configuration into your client Software (like WebStorm or PyCharm), and you're good to go!

---

**[🇨🇳 简体中文版本]**

# 🎉 v1.0.0 正式版发布：彻底解决 JetBrains MCP 兼容报错问题

这是 **MCP Proxy Manager** 的第一个正式发布版本！🚀 

我们带来了一个开箱即用、完全图形化的独立运行程序，专门用于无缝修复主流 AI 客户端（特别是 JetBrains 系列产品）在调用 Antigravity / Gemini 背后 MCP 工具时产生的 Schema 配置不兼容问题。

## 🌟 核心亮点

*   **📦 开箱即用的单文件 EXE**: 告别繁琐的 Python 环境配置！直接在下方下载 `mcp-proxy.exe`，双击即可在 Windows 上直接运行。
*   **🧠 彻底修复 JetBrains & Gemini 兼容性**: 完美解决在 JetBrains 产品中使用 Gemini 模型时出现的 `INVALID_ARGUMENT` (`truncateMode.enum: only allowed for STRING type`) 报错。代理会在底层实时拦截并自动修复数据结构！
*   **🖥️ 直观好用的图形界面**: 轻松添加、编辑和管理多个 MCP 代理配置，告别黑框命令行。
*   **📋 一键「复制配置」**: 只需点击一个按钮，即可将完美格式化后的 JSON 配置文件直接粘贴到 JetBrains IDE 内——省去了所有手动编写 JSON 的烦恼。
*   **🌐 多语言体验支持**: 完整的使用文档现已支持 简体中文、English 以及 日本語。
*   **🔄 智能双模式支持**: 
    *   **Stdio 模式**: 将后台进程的生命周期完美移交给您的 IDE，即连即用。
    *   **SSE 模式**: 在管理器内一键启动/停止常驻后台的 SSE 服务代理。

## 🛠️ 修复与改进
*   解决了在 Windows 环境下被 PyInstaller 打包后的子进程，因无控制台管道 (`stdin` EOF) 导致启动后立刻静默崩溃退出 (Code 0) 的核心缺陷。
*   优化了 GUI 操作逻辑，现在会对尝试手动“启动” Stdio 代理的操作给出清晰的弹窗解释，避免新用户产生不必要的困惑。
*   重构了底层的负载拦截器 (`schema_fixer`)，更干净地移除了工具定义 (Tool Definitions) 中不符合规范的枚举类型限制。

## 📥 安装与使用说明

1. 请在下方的 **Assets** 区域下载为 Windows 准备的 `mcp-proxy.exe`。
2. 双击打开 MCP Proxy Manager，无需安装。
3. 点击“新建代理”按钮，填入你需要代理的目标 MCP 服务信息。
4. 点击红色的配置复制图标 📋，前往你的软件 (WebStorm / PyCharm) 粘贴配置，立刻开始享受无缝的 AI 编程体验！
