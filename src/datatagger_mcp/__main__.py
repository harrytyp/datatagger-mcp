import argparse
import os
import sys
import traceback

from .api import mcp as mcp_server, app as web_app


def main():
    """
    Run the MCP server in Dual Mode.
    MCP_MODE=local  -> Start as stdio server (local use)
    MCP_MODE=hosted -> Start as web server via Uvicorn (remote use)
    """
    mode = os.environ.get("MCP_MODE", "local").lower()
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    if mode == "hosted":
        import uvicorn
        print(f"DEBUG: Starting Datatagger MCP in HOSTED mode on {host}:{port}")
        print(f"DEBUG: Registration page: http://{host}:{port}/register")
        
        try:
            if web_app is None:
                print("ERROR: web_app is None! Check api.py for issues.")
                sys.exit(1)
            
            # Run uvicorn and catch any early exits
            uvicorn.run(web_app, host=host, port=port, log_level="debug")
        except Exception as e:
            print(f"CRITICAL ERROR during uvicorn.run: {e}")
            traceback.print_exc()
            sys.exit(1)
    else:
        # Local mode (stdio)
        print("Starting Datatagger MCP in LOCAL mode (stdio)", file=sys.stderr)
        try:
            mcp_server.run(transport="stdio")
        except Exception as e:
            print(f"CRITICAL ERROR during stdio run: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
