"""Datatagger MCP server package."""

from mcp.server.fastmcp import FastMCP


USER_AGENT = "fdmMCP/1.0"
mcp = FastMCP("datatagger")
