import argparse
import os

from .api import mcp


def main():
    """Run the MCP server with selectable transport (stdio or sse)."""
    parser = argparse.ArgumentParser(description="Datatagger MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport mode: 'stdio' for local use, 'sse' for network/Docker (default: stdio or MCP_TRANSPORT env)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Host to bind to in SSE mode (default: 0.0.0.0 or MCP_HOST env)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8000")),
        help="Port to listen on in SSE mode (default: 8000 or MCP_PORT env)",
    )
    args = parser.parse_args()

    if args.transport == "sse":
        # Force uvicorn to bind to the correct host and port via env vars
        os.environ["UVICORN_HOST"] = args.host
        os.environ["UVICORN_PORT"] = str(args.port)
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
