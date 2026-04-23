import argparse
import os

from .api import mcp as mcp_server


def main():
    """Run the MCP server with selectable transport (stdio or sse)."""
    parser = argparse.ArgumentParser(description="Datatagger MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport mode: 'stdio' for local use, 'sse' for network/Docker",
    )
    # Note: Host/Port are handled by the mcp CLI or environment variables
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    
    args = parser.parse_args()

    if args.transport == "sse":
        # In newer mcp versions, run() supports host/port. 
        # If not, we rely on environment variables.
        try:
            mcp_server.run(transport="sse", host=args.host, port=args.port)
        except TypeError:
            mcp_server.run(transport="sse")
    else:
        mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
