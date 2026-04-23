import argparse
import os
import sys

from .api import mcp as mcp_server


def main():
    """
    Run the MCP server in Dual Mode.
    MCP_MODE=local  -> Start as stdio server (local use)
    MCP_MODE=hosted -> Start as SSE/Web server via Uvicorn (remote use)
    """
    mode = os.environ.get("MCP_MODE", "local").lower()
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    if mode == "hosted":
        import uvicorn
        # The starlette app is available at mcp_server.external_app
        # We start it directly to handle our custom middleware and routes
        print(f"Starting Datatagger MCP in HOSTED mode on {host}:{port}")
        print(f"Registration page available at http://{host}:{port}/register")
        uvicorn.run(mcp_server.external_app, host=host, port=port)
    else:
        # Local mode uses standard stdio transport
        print("Starting Datatagger MCP in LOCAL mode (stdio)", file=sys.stderr)
        mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
