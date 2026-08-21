"""The MCP server: strictly read-only access for AI clients (§9, P4)."""

from ontoforge.mcp.readonly import ReadOnlyGraph
from ontoforge.mcp.server import build_from_settings, create_server, run_stdio

__all__ = ["ReadOnlyGraph", "build_from_settings", "create_server", "run_stdio"]
