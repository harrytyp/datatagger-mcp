"""Entry point for the Datatagger MCP server."""

from .api import mcp


def main():
    """Run the MCP server using stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
