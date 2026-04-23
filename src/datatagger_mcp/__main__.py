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
        import uvicorn
        
        # Get the starlette app directly from the instance.
        # We try different ways to find it depending on the version.
        app = getattr(mcp_server, "_app", None)
        if app is None:
            try:
                app = mcp_server.get_starlette_app()
            except AttributeError:
                # Last resort: try to trigger the internal creation
                # by calling a dummy sse related method if it exists
                # or just use the internal server to build it.
                from mcp.server.fastmcp import FastMCP
                # This is a bit of a hack to get the app
                mcp_server.run(transport="stdio") # This won't work in a script
                raise RuntimeError("Could not find Starlette app in FastMCP instance. Please check your mcp library version.")

        print(f"Starting SSE server on {args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
