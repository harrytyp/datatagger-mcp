import argparse
import os
import sys

from .api import mcp as mcp_server, app as web_app


def main():
    """
    Run the MCP server in Dual Mode.
    MCP_MODE=local  -> Start as stdio server (local use, e.g. Claude Code)
    MCP_MODE=hosted -> Start as web server via Uvicorn (remote use)
    """
    mode = os.environ.get("MCP_MODE", "local").lower()
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    if mode == "hosted":
        import uvicorn
        # We start the native app which handles all MCP endpoints under /sse or /mcp
        print(f"Starting Datatagger MCP in HOSTED mode on {host}:{port}")
        print(f"Registration page: http://{host}:{port}/register")
        uvicorn.run(web_app, host=host, port=port)
    else:
        # Local mode (stdio) for Claude Code, etc.
        # Ensure it runs as stdio
        print("Starting Datatagger MCP in LOCAL mode (stdio)", file=sys.stderr)
        mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
