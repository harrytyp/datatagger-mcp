# Data Tagger MCP Server

A Model Context Protocol (MCP) server for interacting with the Data Tagger API. This server enables LLM clients (like Claude for Desktop) to directly list and search projects and folders within Data Tagger.

## Features

This server exposes the following tools to your MCP client:
- `list_projects`: List all accessible Data Tagger projects.
- `get_project`: Retrieve details of a specific project by UUID.
- `list_folders`: List all Data Tagger folders (can be filtered by project ID).
- `get_folder`: Retrieve details of a specific folder by UUID.
- `search_datatagger`: Perform a global search across folders, projects, and uploads.

## Prerequisites

- Python 3.10 or higher
- A personal API token for Data Tagger (`FDM_TOKEN`)
- The base URL of your Data Tagger instance (`FDM_BASE_URL`)

## Installation

You can install and run this standalone or configure it directly in your MCP client. We recommend using `uv` or standard Python `venv`.

1. Clone the repository:
```bash
git clone https://github.com/harrytyp/datatagger-mcp.git
cd datatagger-mcp
```

2. Create a virtual environment and install requirements:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuration for Claude Desktop

To use this with Claude for Desktop, you need to add the server to your `claude_desktop_config.json` file. 

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the following configuration, making sure to replace the paths and variables with your actual local paths and credentials:

```json
{
  "mcpServers": {
    "datatagger": {
      "command": "C:\\path\\to\\datatagger-mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\path\\to\\datatagger-mcp\\server.py"
      ],
      "env": {
        "FDM_BASE_URL": "https://datatagger.ub.tum.de",
        "FDM_TOKEN": "YOUR_PERSONAL_TOKEN_HERE"
      }
    }
  }
}
```

> **Note:** Do NOT commit your actual `.env` or personal tokens to version control. 

## Development

To test the server locally over `stdio`, you can run:

```bash
python server.py
```
*(It will hang waiting for JSON-RPC messages - this is normal behavior for MCP stdio servers).*
