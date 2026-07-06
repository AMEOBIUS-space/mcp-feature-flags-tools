"""mcp-feature-flags-tools package — MCP server for feature flags."""
from .flag_engine import FeatureFlagEngine
from .server import MCPFeatureFlagsToolsServer, TOOL_DEFS
__all__ = ["FeatureFlagEngine", "MCPFeatureFlagsToolsServer", "TOOL_DEFS"]
__version__ = "1.0.0"
