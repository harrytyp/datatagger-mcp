## Auth: Self-contained JWT Tokens

This server uses HMAC-SHA256 self-contained JWTs instead of server-side session storage.
When you register via the web page:

1. Your API token + base URL are embedded into a signed JWT
2. The token is returned as your MCP URL
3. **No credentials are stored on the server**
4. Tokens are valid for **30 days** and survive container restarts
5. Set `MCP_JWT_SECRET` in your `.env` file (a random signing key)

---

# DataTagger MCP Server

A comprehensive Model Context Protocol (MCP) server for interacting with the TUM
DataTagger API. This server enables LLM clients (like Claude for Desktop) to directly
interface with Data Tagger—allowing for powerful autonomous workflows including bulk
uploads, metadata tagging, and permissions management.

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

> [!NOTE]
>
> The native Datatagger REST API currently has an undocumented bug where passing
> a `description` field during the POST creation of Projects and Folders triggers a 500
> Internal Server Error. To protect the LLM and ensure flawless execution, the
> auto-generated MCP tools purposely omit passing descriptions upon creation until the
> API is patched.

### Dataset Versioning & Logic

- `publish_dataset`: Mark a dataset as publicly viewable.
- `restore_dataset_version`: Rollback a dataset to a previous historical version.
- `compare_dataset_versions`: Get a diff summary between two internal versions.

### Files (Upload / Download)

- `download_version_file`: Safely streams a remote file and writes it to your absolute
  local file path.
- `upload_dataset_file`: Reads a file from your local absolute file path, parses its
  MIME type, and securely uploads it via multipart form-data.

### Permissions & Metadata

- `get_folder_permissions` / `set_folder_permissions`: Read and dynamically assign user
  access roles for folders.
- `list_metadata`: Browse available schematic metadata templates.
- `add_metadata_to_dataset`: Apply an array of JSON metadata tags to a given dataset.

### ⚠️ Destructive Operations (Protected)

- `delete_project`
- `delete_folder`
- `delete_dataset`
  > **Security Guard:** To prevent the LLM from accidentally deleting crucial data during
  > general logic processing, all deletion endpoints require an explicit parameter:
  > `confirm_danger=True`. Without this, the MCP Server will immediately reject the
  > command.

---

## Prerequisites

- Python 3.10 or higher
- A personal API token for Data Tagger (`FDM_TOKEN`)
- The base URL of your Data Tagger instance (`FDM_BASE_URL`)

### How to get your `FDM_TOKEN`

You can easily extract your personal Data Tagger JSON Web Token (JWT) directly via your
browser:

1. Log into your Data Tagger instance (e.g., `https://datatagger.ub.tum.de`).
2. Press `F12` to open your browser's Developer Tools.
3. Navigate to the **Application** tab (Chrome/Edge) or **Storage** tab (Firefox).
4. Unfurl the **Cookies** section in the left sidebar and click on your website domain.
5. In the main table, find the row with the Name `token`.
6. Double-click the Value cell, copy the massive text string (e.g., `eyJhb...`), and
   paste it as your `FDM_TOKEN`!

## Installation

You can install and run this standalone or configure it directly in your MCP client. We
recommend using `uv` or standard Python `venv`.

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

To use this with Claude for Desktop, you need to add the server to your
`claude_desktop_config.json` file.

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the following configuration, making sure to replace the paths and variables with
your actual local paths and credentials:

```json
{
  "mcpServers": {
    "datatagger": {
      "command": "/ABSOLUTE/PATH/TO/PARENT/FOLDER/OF/venv/bin/datatagger-mcp",
      "env": {
        "FDM_BASE_URL": "https://datatagger.ub.tum.de",
        "FDM_TOKEN": "YOUR_PERSONAL_TOKEN_HERE"
      }
    }
  }
}
```

> [!WARNING]
>
> You may need to put the full path to the datatagger-mcp executable in the
> command field. You can get this by running `which datatagger-mcp` on macOS/Linux or
> `where datatagger-mcp` on Windows.

> [!NOTE]
>
> Do NOT commit your actual `.env` or personal tokens to version control.

## Usage Modes

The server supports two transport modes:

1.  **STDIO (Local)**: Default mode, used for local integrations like Claude Desktop.
2.  **SSE (Server)**: Used for network-accessible deployments (e.g., in Docker).

### Running Locally (STDIO)

```bash
datatagger-mcp --transport stdio
```

### Running as a Server (SSE)

```bash
datatagger-mcp --transport sse --host 0.0.0.0 --port 8000
```

## Docker Deployment

The repository includes everything needed for Docker deployment.

### 1. Using Docker Compose (Recommended)

Edit the `environment` variables in `docker-compose.yml` and run:

```bash
docker-compose up -d --build
```

### 2. Using Docker Build

1.  **Build the image**:
    ```bash
    docker build -t datatagger-mcp .
    ```

2.  **Run the container**:
    ```bash
    docker run -p 8000:8000 \
      -e FDM_BASE_URL="https://datatagger.ub.tum.de" \
      -e FDM_TOKEN="YOUR_TOKEN" \
      datatagger-mcp
    ```

The server will be reachable at `http://localhost:8000/sse`.

## Multi-User Support

If you are hosting this server for multiple users (e.g., in a shared Docker container via SSE), each user can provide their own API key directly through the chat interface.

### Session-based Authentication

Users can "log in" to their current session by telling the LLM their token. The LLM will then use the `configure_auth` tool:

```python
configure_auth(token="YOUR_PERSONAL_TOKEN", base_url="https://datatagger.ub.tum.de")
```

This configuration is:
- **Private**: Stored only for the current connection (session).
- **Transient**: Lost when the session ends or the server restarts.
- **Priority**: Overrides any global environment variables set on the server.

## Configuration

Settings can be provided via CLI arguments, environment variables, or the `configure_auth` tool:

| Setting | CLI Argument | Env Variable | Session Tool | Default |
| :--- | :--- | :--- | :--- | :--- |
| Transport | `--transport` | `MCP_TRANSPORT` | - | `stdio` |
| Host | `--host` | `MCP_HOST` | - | `0.0.0.0` |
| Port | `--port` | `MCP_PORT` | - | `8000` |
| API URL | - | `FDM_BASE_URL` | `configure_auth` | - |
| API Token | - | `FDM_TOKEN` | `configure_auth` | - |
