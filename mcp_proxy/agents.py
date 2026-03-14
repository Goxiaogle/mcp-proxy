"""Agent data model and persistent storage."""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger("mcp-schema-proxy")

STORE_DIR = Path.home() / ".mcp-proxy"
STORE_FILE = STORE_DIR / "agents.json"


@dataclass
class Agent:
    """Represents a single MCP proxy agent configuration."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    upstream_type: str = "sse"          # "sse" or "stdio"
    # SSE upstream fields
    upstream_url: str = ""
    upstream_headers: dict = field(default_factory=dict)
    # Stdio upstream fields
    upstream_command: str = ""
    upstream_args: list = field(default_factory=list)
    upstream_env: dict = field(default_factory=dict)
    # Proxy output mode
    proxy_mode: str = "stdio"           # "stdio" or "sse"
    proxy_port: int = 3100
    proxy_host: str = "127.0.0.1"
    enabled: bool = True

    def upstream_config(self) -> dict:
        """Build the upstream config dict used by connect_upstream()."""
        if self.upstream_type == "sse":
            cfg = {"type": "sse", "url": self.upstream_url}
            if self.upstream_headers:
                cfg["headers"] = self.upstream_headers
            return cfg
        else:
            cfg = {
                "type": "stdio",
                "command": self.upstream_command,
                "args": self.upstream_args,
            }
            if self.upstream_env:
                cfg["env"] = self.upstream_env
            return cfg

    def client_mcp_config(self, base_cmd: list[str]) -> dict:
        """Generate the MCP config JSON that AI clients should use."""
        if self.proxy_mode == "sse":
            return {
                "type": "sse",
                "url": f"http://{self.proxy_host}:{self.proxy_port}/sse",
            }
        else:
            # Stdio mode: client launches proxy via the correct dev/frozen cmd
            upstream_json = json.dumps(self.upstream_config(), ensure_ascii=False)
            return {
                "type": "stdio",
                "command": base_cmd[0],
                "args": base_cmd[1:] + [upstream_json],
            }


class AgentStore:
    """CRUD storage for Agent objects, persisted to JSON."""

    def __init__(self, path: Optional[Path] = None):
        self._path = path or STORE_FILE
        self._agents: dict[str, Agent] = {}
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for item in data:
                    agent = Agent(**item)
                    self._agents[agent.id] = agent
                logger.info("Loaded %d agents from %s", len(self._agents), self._path)
            except Exception as e:
                logger.warning("Failed to load agents: %s", e)

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(a) for a in self._agents.values()]
        self._path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def list(self) -> list[Agent]:
        return list(self._agents.values())

    def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def add(self, agent: Agent) -> Agent:
        self._agents[agent.id] = agent
        self._save()
        return agent

    def update(self, agent: Agent) -> Agent:
        self._agents[agent.id] = agent
        self._save()
        return agent

    def delete(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._save()
            return True
        return False
