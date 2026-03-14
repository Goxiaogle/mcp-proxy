"""Config loading — reads upstream config from file or inline JSON."""

import json
import logging
from pathlib import Path

logger = logging.getLogger("mcp-schema-proxy")


def load_config(arg: str) -> dict:
    """Load config from a file path or an inline JSON string."""
    # Try inline JSON first
    try:
        return json.loads(arg)
    except json.JSONDecodeError:
        pass

    # Try as file path
    p = Path(arg)
    if p.exists():
        logger.info("Loading config from %s", p)
        return json.loads(p.read_text(encoding="utf-8"))

    raise FileNotFoundError(f"Config not found: {arg}")
