"""Schema fixer — repairs JSON Schema issues for strict API validators."""

import logging

import mcp.types as types

logger = logging.getLogger("mcp-schema-proxy")


def fix_schema(schema):
    """Recursively fix JSON Schema nodes for strict API validators.

    Known fixes:
      1. `enum` is only allowed on `type: "string"` — inject type if missing.
    """
    if not isinstance(schema, dict):
        return schema

    fixed = dict(schema)

    # Core fix: enum requires type=string for Gemini
    if "enum" in fixed and fixed.get("type") != "string":
        logger.debug("Fixing enum without string type: %s", fixed.get("enum"))
        fixed["type"] = "string"

    # Recurse into nested structures
    if "properties" in fixed and isinstance(fixed["properties"], dict):
        fixed["properties"] = {
            k: fix_schema(v) for k, v in fixed["properties"].items()
        }

    if "items" in fixed and isinstance(fixed["items"], dict):
        fixed["items"] = fix_schema(fixed["items"])

    for key in ("anyOf", "oneOf", "allOf"):
        if key in fixed and isinstance(fixed[key], list):
            fixed[key] = [fix_schema(s) for s in fixed[key]]

    if "additionalProperties" in fixed and isinstance(
        fixed["additionalProperties"], dict
    ):
        fixed["additionalProperties"] = fix_schema(fixed["additionalProperties"])

    return fixed


def fix_tools(tools: list[types.Tool]) -> list[types.Tool]:
    """Apply schema fixes to a list of MCP Tool objects."""
    fixed = []
    n_fixed = 0
    for tool in tools:
        original = tool.inputSchema
        patched = fix_schema(original) if original else original
        if patched != original:
            n_fixed += 1
        fixed.append(
            types.Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=patched,
            )
        )
    if n_fixed:
        logger.info("Applied schema fixes to %d/%d tools", n_fixed, len(tools))
    return fixed
