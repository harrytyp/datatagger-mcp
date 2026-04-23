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
        import mcp.server.fastmcp
        import uvicorn

        def custom_run_sse(mcp_instance):
            """Custom SSE runner that forces 0.0.0.0 binding."""
            # Use the internal _app or get_starlette_app()
            app = getattr(mcp_instance, "_app", None)
            if app is None:
                try:
                    app = mcp_instance.get_starlette_app()
                except AttributeError:
                    # Fallback to creating the app if possible
                    # This depends on mcp internals
                    raise RuntimeError("Could not find Starlette app in FastMCP instance")
            
            uvicorn.run(app, host=args.host, port=args.port)

        # Monkeypatch the internal FastMCP SSE runner
        mcp.server.fastmcp.run_sse = custom_run_sse
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
