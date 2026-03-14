"""GUI — tkinter-based visual manager for MCP proxy agents."""

import asyncio
import json
import logging
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import asdict
from pathlib import Path

from .agents import Agent, AgentStore

logger = logging.getLogger("mcp-schema-proxy")

# ── Resolve script path for client configs ────────────────────────────────────
def _get_runner_cmd() -> list[str]:
    """Get the base command to launch the CLI runner based on execution mode."""
    if getattr(sys, 'frozen', False):
        return [sys.executable, "--cli-runner"]
    else:
        main_script = str(Path(__file__).resolve().parent.parent / "mcp_proxy.py")
        return [sys.executable, main_script, "--cli-runner"]

# ── Color Palette ─────────────────────────────────────────────────────────────
C_BG = "#1e1e2e"
C_BG2 = "#282840"
C_FG = "#cdd6f4"
C_ACCENT = "#89b4fa"
C_ACCENT2 = "#74c7ec"
C_GREEN = "#a6e3a1"
C_RED = "#f38ba8"
C_YELLOW = "#f9e2af"
C_SURFACE = "#313244"
C_OVERLAY = "#45475a"
C_BTN_FG = "#1e1e2e"


# ── Styled Helpers ────────────────────────────────────────────────────────────

def _rounded_frame(parent, **kw):
    f = tk.Frame(parent, bg=C_SURFACE, highlightbackground=C_OVERLAY,
                 highlightthickness=1, **kw)
    return f


def _label(parent, text, *, size=10, bold=False, color=C_FG, **kw):
    weight = "bold" if bold else "normal"
    lbl = tk.Label(parent, text=text, fg=color, bg=parent["bg"],
                   font=("Segoe UI", size, weight), **kw)
    return lbl


def _entry(parent, *, width=40, **kw):
    e = tk.Entry(parent, width=width, fg=C_FG, bg=C_BG, insertbackground=C_FG,
                 highlightbackground=C_OVERLAY, highlightthickness=1,
                 font=("Consolas", 10), relief="flat", **kw)
    return e


def _button(parent, text, command, *, bg=C_ACCENT, fg=C_BTN_FG, width=None):
    btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                    activebackground=C_ACCENT2, activeforeground=fg,
                    font=("Segoe UI", 10, "bold"), relief="flat",
                    cursor="hand2", padx=14, pady=5, bd=0)
    if width:
        btn.config(width=width)
    return btn


def _combo(parent, values, *, width=15, **kw):
    style = ttk.Style()
    style.configure("Dark.TCombobox",
                     fieldbackground=C_BG, background=C_SURFACE,
                     foreground=C_FG, selectbackground=C_ACCENT,
                     selectforeground=C_BTN_FG)
    cb = ttk.Combobox(parent, values=values, width=width,
                      style="Dark.TCombobox", state="readonly", **kw)
    return cb


# ── Upstream Probe ────────────────────────────────────────────────────────────

def _probe_upstream(config: dict) -> tuple[bool, int]:
    """Try connecting to upstream MCP and count tools. Returns (ok, tool_count)."""
    async def _do():
        from .upstream import connect_upstream
        async with connect_upstream(config) as session:
            result = await session.list_tools()
            return len(result.tools)

    try:
        count = asyncio.run(_do())
        return True, count
    except Exception:
        return False, 0


# ── Agent Dialog ──────────────────────────────────────────────────────────────

class AgentDialog(tk.Toplevel):
    """Dialog for adding or editing an agent.

    Supports two input modes:
      - 「粘贴配置」: paste raw upstream JSON, auto-fills form fields.
      - 「表单模式」: fill fields manually.
    """

    def __init__(self, parent, agent: Agent | None = None):
        super().__init__(parent)
        self.result: Agent | None = None
        self._agent = agent or Agent()
        self._is_edit = agent is not None

        self.title("编辑代理" if self._is_edit else "添加代理")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        w, h = 580, 640
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build_ui()
        if self._is_edit:
            self._populate()
            self._show_tab("form")
        else:
            self._show_tab("paste")

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 16, "pady": (8, 2)}

        # ── Name ──
        _label(self, "代理名称", bold=True).pack(anchor="w", **pad)
        self._name_var = tk.StringVar()
        _entry(self, textvariable=self._name_var, width=55).pack(
            anchor="w", padx=16, pady=(0, 8))

        # ── Tab switcher ──
        tab_bar = tk.Frame(self, bg=C_BG)
        tab_bar.pack(fill="x", padx=16, pady=(4, 0))
        self._tab_paste_btn = _button(tab_bar, "📋 粘贴配置", lambda: self._show_tab("paste"),
                                       bg=C_ACCENT)
        self._tab_paste_btn.pack(side="left", padx=(0, 4))
        self._tab_form_btn = _button(tab_bar, "📝 表单模式", lambda: self._show_tab("form"),
                                      bg=C_OVERLAY, fg=C_FG)
        self._tab_form_btn.pack(side="left")

        # ── PASTE TAB ─────────────────────────────────────────────────────
        self._paste_frame = tk.Frame(self, bg=C_BG)
        _label(self._paste_frame, "粘贴上游 MCP 配置 JSON：", size=9, color=C_OVERLAY).pack(
            anchor="w", padx=0, pady=(8, 4))
        self._paste_text = tk.Text(self._paste_frame, height=14, width=62,
                                   bg=C_SURFACE, fg=C_FG, insertbackground=C_FG,
                                   font=("Consolas", 10), relief="flat",
                                   highlightbackground=C_OVERLAY,
                                   highlightthickness=1, wrap="none")
        self._paste_text.pack(fill="both", expand=True, pady=(0, 8))

        paste_hint = _label(self._paste_frame,
                            '支持 {"type":"sse",...} 或 {"type":"stdio",...} 格式',
                            size=9, color=C_OVERLAY)
        paste_hint.pack(anchor="w")

        parse_btn_frame = tk.Frame(self._paste_frame, bg=C_BG)
        parse_btn_frame.pack(fill="x", pady=(8, 0))
        _button(parse_btn_frame, "✅ 解析并填入表单", self._on_parse_json,
                bg=C_GREEN).pack(side="left")

        # ── FORM TAB ──────────────────────────────────────────────────────
        self._form_frame = tk.Frame(self, bg=C_BG)

        # Upstream Type
        _label(self._form_frame, "上游类型", bold=True).pack(anchor="w", pady=(8, 2))
        self._up_type_var = tk.StringVar(value="sse")
        frame_ut = tk.Frame(self._form_frame, bg=C_BG)
        frame_ut.pack(anchor="w", pady=(0, 8))
        for val, label in [("sse", "SSE"), ("stdio", "Stdio")]:
            tk.Radiobutton(frame_ut, text=label, variable=self._up_type_var,
                           value=val, bg=C_BG, fg=C_FG,
                           activebackground=C_BG, activeforeground=C_ACCENT,
                           selectcolor=C_SURFACE, font=("Segoe UI", 10),
                           command=self._toggle_upstream).pack(side="left", padx=(0, 16))

        # SSE Fields
        self._sse_frame = tk.Frame(self._form_frame, bg=C_BG)
        _label(self._sse_frame, "URL").pack(anchor="w")
        self._url_var = tk.StringVar()
        _entry(self._sse_frame, textvariable=self._url_var, width=55).pack(
            anchor="w", pady=(0, 4))
        _label(self._sse_frame, "Headers (JSON)").pack(anchor="w")
        self._headers_text = tk.Text(self._sse_frame, height=3, width=55,
                                     bg=C_BG, fg=C_FG, insertbackground=C_FG,
                                     font=("Consolas", 10), relief="flat",
                                     highlightbackground=C_OVERLAY,
                                     highlightthickness=1)
        self._headers_text.pack(anchor="w", pady=(0, 4))

        # Stdio Fields
        self._stdio_frame = tk.Frame(self._form_frame, bg=C_BG)
        _label(self._stdio_frame, "Command").pack(anchor="w")
        self._cmd_var = tk.StringVar()
        _entry(self._stdio_frame, textvariable=self._cmd_var, width=55).pack(
            anchor="w", pady=(0, 4))
        _label(self._stdio_frame, "Args (JSON 数组)").pack(anchor="w")
        self._args_text = tk.Text(self._stdio_frame, height=3, width=55,
                                  bg=C_BG, fg=C_FG, insertbackground=C_FG,
                                  font=("Consolas", 10), relief="flat",
                                  highlightbackground=C_OVERLAY,
                                  highlightthickness=1)
        self._args_text.pack(anchor="w", pady=(0, 4))
        _label(self._stdio_frame, "Env (JSON 对象)").pack(anchor="w")
        self._env_text = tk.Text(self._stdio_frame, height=3, width=55,
                                 bg=C_BG, fg=C_FG, insertbackground=C_FG,
                                 font=("Consolas", 10), relief="flat",
                                 highlightbackground=C_OVERLAY,
                                 highlightthickness=1)
        self._env_text.pack(anchor="w", pady=(0, 4))

        # Proxy Mode
        sep = tk.Frame(self._form_frame, bg=C_OVERLAY, height=1)
        sep.pack(fill="x", pady=8)

        proxy_frame = tk.Frame(self._form_frame, bg=C_BG)
        proxy_frame.pack(anchor="w", pady=(0, 4))
        _label(proxy_frame, "代理输出模式", bold=True).pack(side="left")
        self._proxy_mode_var = tk.StringVar(value="stdio")
        for val, label in [("stdio", "Stdio"), ("sse", "SSE")]:
            tk.Radiobutton(proxy_frame, text=label, variable=self._proxy_mode_var,
                           value=val, bg=C_BG, fg=C_FG,
                           activebackground=C_BG, activeforeground=C_ACCENT,
                           selectcolor=C_SURFACE, font=("Segoe UI", 10),
                           command=self._toggle_proxy).pack(side="left", padx=(12, 0))

        self._port_frame = tk.Frame(self._form_frame, bg=C_BG)
        _label(self._port_frame, "SSE 端口").pack(side="left")
        self._port_var = tk.StringVar(value="3100")
        _entry(self._port_frame, textvariable=self._port_var, width=8).pack(
            side="left", padx=(8, 0))
        _label(self._port_frame, "Host").pack(side="left", padx=(16, 0))
        self._host_var = tk.StringVar(value="127.0.0.1")
        _entry(self._port_frame, textvariable=self._host_var, width=15).pack(
            side="left", padx=(8, 0))

        # ── Bottom Buttons ──
        btn_frame = tk.Frame(self, bg=C_BG)
        btn_frame.pack(side="bottom", fill="x", padx=16, pady=16)
        _button(btn_frame, "取消", self.destroy, bg=C_OVERLAY, fg=C_FG).pack(
            side="right", padx=(8, 0))
        _button(btn_frame, "保存", self._on_save).pack(side="right")

        self._toggle_upstream()
        self._toggle_proxy()

    # ── Tab Switching ─────────────────────────────────────────────────────

    def _show_tab(self, tab: str):
        if tab == "paste":
            self._form_frame.pack_forget()
            self._paste_frame.pack(fill="both", expand=True, padx=16, pady=(4, 0))
            self._tab_paste_btn.config(bg=C_ACCENT, fg=C_BTN_FG)
            self._tab_form_btn.config(bg=C_OVERLAY, fg=C_FG)
        else:
            self._paste_frame.pack_forget()
            self._form_frame.pack(fill="both", expand=True, padx=16, pady=(4, 0))
            self._tab_form_btn.config(bg=C_ACCENT, fg=C_BTN_FG)
            self._tab_paste_btn.config(bg=C_OVERLAY, fg=C_FG)
            self._toggle_upstream()
            self._toggle_proxy()

    # ── Parse Pasted JSON ─────────────────────────────────────────────────

    def _on_parse_json(self):
        """Parse pasted upstream config JSON and populate form fields."""
        raw = self._paste_text.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning("提示", "请先粘贴 JSON 配置", parent=self)
            return

        try:
            cfg = json.loads(raw)
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON 错误", f"无法解析 JSON:\n{e}", parent=self)
            return

        if not isinstance(cfg, dict) or "type" not in cfg:
            messagebox.showerror("格式错误", '缺少 "type" 字段（应为 "sse" 或 "stdio"）', parent=self)
            return

        t = cfg["type"]
        if t not in ("sse", "stdio"):
            messagebox.showerror("格式错误", f'不支持的 type: "{t}"（应为 "sse" 或 "stdio"）',
                                 parent=self)
            return

        # Clear existing form data
        self._url_var.set("")
        self._headers_text.delete("1.0", "end")
        self._cmd_var.set("")
        self._args_text.delete("1.0", "end")
        self._env_text.delete("1.0", "end")

        self._up_type_var.set(t)

        if t == "sse":
            self._url_var.set(cfg.get("url", ""))
            headers = cfg.get("headers")
            if headers:
                self._headers_text.insert("1.0", json.dumps(headers, indent=2, ensure_ascii=False))
        else:
            self._cmd_var.set(cfg.get("command", ""))
            args = cfg.get("args")
            if args:
                self._args_text.insert("1.0", json.dumps(args, indent=2, ensure_ascii=False))
            env = cfg.get("env")
            if env:
                self._env_text.insert("1.0", json.dumps(env, indent=2, ensure_ascii=False))

        # Auto-fill name if empty
        if not self._name_var.get().strip():
            if t == "sse":
                self._name_var.set(cfg.get("url", "SSE Proxy"))
            else:
                cmd = cfg.get("command", "")
                # Use last part of command path as name
                name = cmd.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] if cmd else "Stdio Proxy"
                self._name_var.set(name)

        self._show_tab("form")

    # ── Toggle Helpers ────────────────────────────────────────────────────

    def _toggle_upstream(self):
        if self._up_type_var.get() == "sse":
            self._stdio_frame.pack_forget()
            self._sse_frame.pack(anchor="w", pady=(0, 4))
        else:
            self._sse_frame.pack_forget()
            self._stdio_frame.pack(anchor="w", pady=(0, 4))

    def _toggle_proxy(self):
        if self._proxy_mode_var.get() == "sse":
            self._port_frame.pack(anchor="w", pady=(0, 4))
        else:
            self._port_frame.pack_forget()

    # ── Populate (for edit mode) ──────────────────────────────────────────

    def _populate(self):
        a = self._agent
        self._name_var.set(a.name)
        self._up_type_var.set(a.upstream_type)
        self._url_var.set(a.upstream_url)
        if a.upstream_headers:
            self._headers_text.insert("1.0", json.dumps(a.upstream_headers, indent=2, ensure_ascii=False))
        self._cmd_var.set(a.upstream_command)
        if a.upstream_args:
            self._args_text.insert("1.0", json.dumps(a.upstream_args, indent=2, ensure_ascii=False))
        if a.upstream_env:
            self._env_text.insert("1.0", json.dumps(a.upstream_env, indent=2, ensure_ascii=False))
        self._proxy_mode_var.set(a.proxy_mode)
        self._port_var.set(str(a.proxy_port))
        self._host_var.set(a.proxy_host)
        # Also populate paste text with current upstream config for reference
        self._paste_text.insert("1.0", json.dumps(a.upstream_config(), indent=2, ensure_ascii=False))

    # ── Save ──────────────────────────────────────────────────────────────

    def _parse_json_field(self, widget: tk.Text, label: str, default):
        raw = widget.get("1.0", "end").strip()
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            messagebox.showerror("JSON 错误", f"{label} 不是合法 JSON", parent=self)
            return None

    def _on_save(self):
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请填写代理名称", parent=self)
            return

        a = self._agent
        a.name = name
        a.upstream_type = self._up_type_var.get()

        if a.upstream_type == "sse":
            url = self._url_var.get().strip()
            if not url:
                messagebox.showwarning("提示", "请填写上游 URL", parent=self)
                return
            a.upstream_url = url
            headers = self._parse_json_field(self._headers_text, "Headers", {})
            if headers is None:
                return
            a.upstream_headers = headers
        else:
            cmd = self._cmd_var.get().strip()
            if not cmd:
                messagebox.showwarning("提示", "请填写 Command", parent=self)
                return
            a.upstream_command = cmd
            args = self._parse_json_field(self._args_text, "Args", [])
            if args is None:
                return
            a.upstream_args = args
            env = self._parse_json_field(self._env_text, "Env", {})
            if env is None:
                return
            a.upstream_env = env

        a.proxy_mode = self._proxy_mode_var.get()
        try:
            a.proxy_port = int(self._port_var.get())
        except ValueError:
            a.proxy_port = 3100
        a.proxy_host = self._host_var.get().strip() or "127.0.0.1"

        self.result = a
        self.destroy()


# ── Toast Notification ────────────────────────────────────────────────────────

class Toast(tk.Toplevel):
    """Brief pop-up notification."""

    def __init__(self, parent, message, *, duration=2000):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg=C_GREEN)
        lbl = tk.Label(self, text=message, bg=C_GREEN, fg=C_BTN_FG,
                       font=("Segoe UI", 11, "bold"), padx=20, pady=10)
        lbl.pack()
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + parent.winfo_height() - self.winfo_height() - 30
        self.geometry(f"+{x}+{y}")
        self.attributes("-alpha", 0.92)
        self.after(duration, self.destroy)


# ── Main Application ─────────────────────────────────────────────────────────

class McpProxyGUI(tk.Tk):
    """Main GUI window for managing MCP proxy agents."""

    def __init__(self):
        super().__init__()
        self.title("MCP Schema Proxy Manager")
        self.configure(bg=C_BG)
        self.minsize(900, 540)
        self.geometry("980x600")

        self._store = AgentStore()
        self._processes: dict[str, subprocess.Popen] = {}
        # Upstream probe results: agent_id -> (ok, tool_count) or None
        self._probe_results: dict[str, tuple[bool, int] | None] = {}

        self._build_ui()
        self._refresh_list()
        # Start background upstream detection for all agents
        self._probe_all_upstreams()

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self):
        # Title bar
        header = tk.Frame(self, bg=C_BG2, padx=16, pady=12)
        header.pack(fill="x")
        _label(header, "⚡ MCP Schema Proxy", size=16, bold=True,
               color=C_ACCENT).pack(side="left")
        _button(header, "+ 添加代理", self._on_add).pack(side="right")

        # Batch action bar (below header)
        batch_bar = tk.Frame(self, bg=C_BG, pady=8)
        batch_bar.pack(fill="x", padx=16)

        _button(batch_bar, "▶▶ 全部启动", self._on_start_all,
                bg=C_GREEN).pack(side="left", padx=(0, 8))
        _button(batch_bar, "⏹⏹ 全部停止", self._on_stop_all,
                bg=C_YELLOW).pack(side="left", padx=(0, 8))
        _button(batch_bar, "📋 复制总配置", self._on_copy_all,
                bg=C_ACCENT).pack(side="left", padx=(0, 8))
        _button(batch_bar, "🔄 刷新上游状态", self._probe_all_upstreams,
                bg=C_OVERLAY, fg=C_FG).pack(side="left")

        # Agent list
        list_frame = tk.Frame(self, bg=C_BG)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(4, 0))

        columns = ("name", "upstream", "mode", "port", "upstream_status", "tools", "proxy_status")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Treeview",
                         background=C_SURFACE, foreground=C_FG,
                         fieldbackground=C_SURFACE, rowheight=36,
                         font=("Segoe UI", 10))
        style.configure("Dark.Treeview.Heading",
                         background=C_BG2, foreground=C_ACCENT,
                         font=("Segoe UI", 10, "bold"),
                         relief="flat")
        style.map("Dark.Treeview",
                   background=[("selected", C_OVERLAY)],
                   foreground=[("selected", C_ACCENT)])

        self._tree = ttk.Treeview(list_frame, columns=columns,
                                   show="headings", style="Dark.Treeview",
                                   selectmode="browse")
        self._tree.heading("name", text="名称")
        self._tree.heading("upstream", text="上游类型")
        self._tree.heading("mode", text="代理模式")
        self._tree.heading("port", text="端口")
        self._tree.heading("upstream_status", text="上游状态")
        self._tree.heading("tools", text="工具数")
        self._tree.heading("proxy_status", text="代理状态")

        self._tree.column("name", width=180, anchor="w")
        self._tree.column("upstream", width=80, anchor="center")
        self._tree.column("mode", width=80, anchor="center")
        self._tree.column("port", width=60, anchor="center")
        self._tree.column("upstream_status", width=100, anchor="center")
        self._tree.column("tools", width=60, anchor="center")
        self._tree.column("proxy_status", width=100, anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                   command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.bind("<Double-1>", lambda e: self._on_edit())

        # Per-agent action bar
        action_bar = tk.Frame(self, bg=C_BG, pady=10)
        action_bar.pack(fill="x", padx=16)

        _button(action_bar, "📋 复制配置", self._on_copy,
                bg=C_ACCENT).pack(side="left", padx=(0, 8))
        _button(action_bar, "▶ 启动", self._on_start,
                bg=C_GREEN).pack(side="left", padx=(0, 8))
        _button(action_bar, "⏹ 停止", self._on_stop,
                bg=C_YELLOW).pack(side="left", padx=(0, 8))
        _button(action_bar, "✏ 编辑", self._on_edit,
                bg=C_OVERLAY, fg=C_FG).pack(side="left", padx=(0, 8))
        _button(action_bar, "🗑 删除", self._on_delete,
                bg=C_RED).pack(side="left")

        # Status bar
        status_bar = tk.Frame(self, bg=C_BG2, padx=16, pady=6)
        status_bar.pack(fill="x", side="bottom")
        self._status_label = _label(status_bar, "就绪", size=9, color=C_OVERLAY)
        self._status_label.pack(side="left")

    # ── List Refresh ──────────────────────────────────────────────────────

    def _refresh_list(self):
        self._tree.delete(*self._tree.get_children())
        for agent in self._store.list():
            proxy_status = "🟢 运行中" if agent.id in self._processes else "⚪ 已停止"
            port_display = str(agent.proxy_port) if agent.proxy_mode == "sse" else "—"

            # Upstream probe result
            probe = self._probe_results.get(agent.id)
            if probe is None:
                up_status = "🔍 检测中…"
                tools = "…"
            elif probe[0]:
                up_status = "🟢 在线"
                tools = str(probe[1])
            else:
                up_status = "🔴 离线"
                tools = "—"

            self._tree.insert("", "end", iid=agent.id, values=(
                agent.name,
                agent.upstream_type.upper(),
                agent.proxy_mode.upper(),
                port_display,
                up_status,
                tools,
                proxy_status,
            ))

    def _selected_agent(self) -> Agent | None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选中一个代理")
            return None
        return self._store.get(sel[0])

    def _set_status(self, msg: str):
        self._status_label.config(text=msg)

    # ── Upstream Probe ────────────────────────────────────────────────────

    def _probe_all_upstreams(self):
        """Probe all agents' upstreams in background threads."""
        agents = self._store.list()
        if not agents:
            return
        for agent in agents:
            self._probe_results[agent.id] = None   # mark as "detecting"
        self._refresh_list()
        self._set_status("正在检测上游 MCP 状态…")

        for agent in agents:
            threading.Thread(target=self._probe_one,
                             args=(agent,), daemon=True).start()

    def _probe_one(self, agent: Agent):
        """Probe a single agent's upstream (runs in background thread)."""
        result = _probe_upstream(agent.upstream_config())
        self._probe_results[agent.id] = result
        self.after(0, self._refresh_list)
        ok, count = result
        if ok:
            self.after(0, lambda: self._set_status(
                f"✅ {agent.name}: 上游在线，{count} 个工具"))
        else:
            self.after(0, lambda: self._set_status(
                f"❌ {agent.name}: 上游离线"))

    # ── Actions ───────────────────────────────────────────────────────────

    def _on_add(self):
        dlg = AgentDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self._store.add(dlg.result)
            self._refresh_list()
            self._set_status(f"已添加代理: {dlg.result.name}")
            # Probe new agent immediately
            threading.Thread(target=self._probe_one,
                             args=(dlg.result,), daemon=True).start()

    def _on_edit(self):
        agent = self._selected_agent()
        if not agent:
            return
        dlg = AgentDialog(self, agent)
        self.wait_window(dlg)
        if dlg.result:
            self._store.update(dlg.result)
            self._refresh_list()
            self._set_status(f"已更新代理: {dlg.result.name}")

    def _on_delete(self):
        agent = self._selected_agent()
        if not agent:
            return
        if not messagebox.askyesno("确认删除", f"确定删除代理「{agent.name}」？"):
            return
        # Stop if running
        if agent.id in self._processes:
            self._stop_agent(agent.id)
        self._probe_results.pop(agent.id, None)
        self._store.delete(agent.id)
        self._refresh_list()
        self._set_status(f"已删除代理: {agent.name}")

    def _on_copy(self):
        """Copy a single agent's MCP config to clipboard."""
        agent = self._selected_agent()
        if not agent:
            return
        config = agent.client_mcp_config(_get_runner_cmd())
        text = json.dumps(config, indent=2, ensure_ascii=False)
        self.clipboard_clear()
        self.clipboard_append(text)
        Toast(self, "✅ MCP 配置已复制到剪贴板")
        self._set_status(f"已复制 {agent.name} 的 MCP 配置")

    def _on_copy_all(self):
        """Copy combined config for all agents: name: config, name: config, ..."""
        agents = self._store.list()
        if not agents:
            messagebox.showinfo("提示", "没有代理可复制")
            return
        lines = []
        for agent in agents:
            cfg_json = json.dumps(agent.client_mcp_config(_get_runner_cmd()), indent=2, ensure_ascii=False)
            # Indent the config body by 2 spaces so it reads nicely
            indented = cfg_json.replace("\n", "\n  ")
            lines.append(f'"{agent.name}": {indented}')
        text = ",\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        Toast(self, f"✅ 已复制 {len(agents)} 个代理的总配置")
        self._set_status(f"已复制 {len(agents)} 个代理的总配置到剪贴板")

    def _on_start(self):
        agent = self._selected_agent()
        if not agent:
            return
        if agent.id in self._processes:
            messagebox.showinfo("提示", f"代理「{agent.name}」已在运行中")
            return
        self._start_agent(agent)

    def _on_stop(self):
        agent = self._selected_agent()
        if not agent:
            return
        if agent.id not in self._processes:
            messagebox.showinfo("提示", f"代理「{agent.name}」未在运行")
            return
        self._stop_agent(agent.id)
        self._refresh_list()
        self._set_status(f"已停止代理: {agent.name}")

    def _on_start_all(self):
        """Start all agents that are not already running."""
        agents = self._store.list()
        if not agents:
            messagebox.showinfo("提示", "没有代理可启动")
            return
        started = 0
        for agent in agents:
            if agent.id not in self._processes:
                self._start_agent(agent)
                started += 1
        if started:
            self._set_status(f"已启动 {started} 个代理")
        else:
            self._set_status("所有代理已在运行中")

    def _on_stop_all(self):
        """Stop all running agents."""
        if not self._processes:
            messagebox.showinfo("提示", "没有正在运行的代理")
            return
        count = len(self._processes)
        for aid in list(self._processes):
            self._stop_agent(aid)
        self._refresh_list()
        self._set_status(f"已停止 {count} 个代理")

    # ── Process Management ────────────────────────────────────────────────

    def _start_agent(self, agent: Agent):
        """Start a proxy agent as a subprocess."""
        upstream_json = json.dumps(agent.upstream_config(), ensure_ascii=False)
        cmd = _get_runner_cmd() + [upstream_json]

        if agent.proxy_mode == "sse":
            cmd += ["--sse", "--port", str(agent.proxy_port),
                    "--host", agent.proxy_host]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            self._processes[agent.id] = proc
            self._refresh_list()
            self._set_status(f"已启动代理: {agent.name} (PID {proc.pid})")

            # Monitor in background thread
            threading.Thread(target=self._monitor_process,
                             args=(agent.id, agent.name, proc),
                             daemon=True).start()
        except Exception as e:
            messagebox.showerror("启动失败", str(e))

    def _stop_agent(self, agent_id: str):
        proc = self._processes.pop(agent_id, None)
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _monitor_process(self, agent_id: str, name: str, proc: subprocess.Popen):
        proc.wait()
        self._processes.pop(agent_id, None)
        self.after(0, self._refresh_list)
        self.after(0, lambda: self._set_status(f"代理 {name} 已退出 (code {proc.returncode})"))

    def destroy(self):
        # Clean up all running processes
        for aid in list(self._processes):
            self._stop_agent(aid)
        super().destroy()


def run_gui():
    """Entry point for GUI mode."""
    app = McpProxyGUI()
    app.mainloop()
