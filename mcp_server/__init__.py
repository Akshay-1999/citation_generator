"""
MCP Connector package for RecAI / ProfileIQ.
Exposes resume search, bulk screening, and screening reports to Anthropic Claude.
"""
from mcp_server.oauth import oauth_router
from mcp_server.server import mcp_router

__all__ = ["oauth_router", "mcp_router"]
