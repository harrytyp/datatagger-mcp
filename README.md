# Data Tagger MCP Server

A comprehensive Model Context Protocol (MCP) server for interacting with the Data Tagger API. This server enables LLM clients (like Claude for Desktop) to directly interface with Data Tagger—allowing for powerful autonomous workflows including bulk uploads, metadata tagging, and permissions management.

## Features

This server exposes 20+ specialized tools to your MCP client, logically grouped below:

### Search & Read
- `search_datatagger`: Perform a global search across folders, projects, and uploads.
- `list_projects` / `get_project`: Retrieve available projects.
- `list_folders` / `get_folder`: Retrieve available folders.
- `list_datasets`: Retrieve dataset entries inside folders.

### Creation & Modification
- `create_project` / `update_project`
- `create_folder` / `update_folder`
- `create_dataset` / `update_dataset`

### Dataset Versioning & Logic
- `publish_dataset`: Mark a dataset as publicly viewable.
- `restore_dataset_version`: Rollback a dataset to a previous historical version.
- `compare_dataset_versions`: Get a diff summary between two internal versions.

### Files (Upload / Download)
- `download_version_file`: Safely streams a remote file and writes it to your absolute local file path.
- `upload_dataset_file`: Reads a file from your local absolute file path, parses its MIME type, and securely uploads it via multipart form-data.

### Permissions & Metadata
- `get_folder_permissions` / `set_folder_permissions`: Read and dynamically assign user access roles for folders.
- `list_metadata`: Browse available schematic metadata templates.
- `add_metadata_to_dataset`: Apply an array of JSON metadata tags to a given dataset.

### ⚠️ Destructive Operations (Protected)
- `delete_project`
- `delete_folder`
- `delete_dataset`
> **Security Guard:** To prevent the LLM from accidentally deleting crucial data during general logic processing, all deletion endpoints require an explicit parameter: `confirm_danger=True`. Without this, the MCP Server will immediately reject the command.

---

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

pip install -e .
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
