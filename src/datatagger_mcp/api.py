import mimetypes
import os
import json
import uuid
import time
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from contextvars import ContextVar

import httpx
from fastapi import FastAPI
from starlette.responses import HTMLResponse
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Scope, Receive, Send

from mcp.server.fastmcp import FastMCP, Context

from . import USER_AGENT

# --- FastMCP Instance ---
mcp = FastMCP("datatagger")

# Diagnose FastMCP
print(f"DEBUG: FastMCP instance methods: {[m for m in dir(mcp) if not m.startswith('_')]}")
session_base_url_var: ContextVar[Optional[str]] = ContextVar("session_base_url", default=None)

# In-memory store: {token: {"key": key, "base_url": url, "last_active": timestamp}}
token_store: Dict[str, Dict[str, Any]] = {}

# Legacy store for stdio sessions (optional fallback)
SESSION_AUTH: Dict[str, Dict[str, str]] = {}


def get_session_id(ctx: Optional[Context]) -> Optional[str]:
    """Extract session ID from the MCP context if available."""
    if not ctx:
        return None
    try:
        return str(id(ctx.request_context.session))
    except Exception:
        return None


def cleanup_expired_sessions():
    """Remove sessions that have been inactive for too long."""
    now = time.time()
    expired = [
        t for t, data in token_store.items() if now - data["last_active"] > SESSION_TIMEOUT
    ]
    for t in expired:
        del token_store[t]


class TokenMiddleware:
    """Middleware to extract token from URL and set the session context."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            request = Request(scope)
            token = request.query_params.get("token")

            if token and token in token_store:
                token_store[token]["last_active"] = time.time()
                session_key_var.set(token_store[token]["key"])
                session_base_url_var.set(token_store[token]["base_url"])

        await self.app(scope, receive, send)


# --- Registration & Token UI ---
async def register_page(request: Request):
    """Simple registration page to exchange API key for a session token."""
    if request.method == "POST":
        form = await request.form()
        api_key = str(form.get("api_key", "")).strip()
        base_url = str(form.get("base_url", "https://datatagger.ub.tum.de")).strip()

        if not api_key:
            return HTMLResponse("ERROR: API Key is required", status_code=400)

        new_token = str(uuid.uuid4())
        token_store[new_token] = {
            "key": api_key,
            "base_url": base_url,
            "last_active": time.time(),
        }

        # Detect protocol behind reverse proxy
        forwarded_proto = request.headers.get("x-forwarded-proto", "http")
        host = request.headers.get("host", "localhost:8000")
        personal_url = f"{forwarded_proto}://{host}/sse?token={new_token}"

        return HTMLResponse(
            f"""
            <div style="font-family: sans-serif; padding: 20px; max-width: 600px; margin: 40px auto; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #2c3e50;">Registration Successful</h2>
                <p>Use the following URL in your MCP client (e.g. KISSKI):</p>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 4px; word-break: break-all; font-family: monospace; border: 1px solid #eee; margin: 10px 0;">
                    {personal_url}
                </div>
                <p style="color: #666; font-size: 0.9em; margin-top: 20px;">
                    Note: This session will expire after 30 minutes of inactivity.
                </p>
                <a href="/register" style="display: inline-block; margin-top: 10px; color: #3498db; text-decoration: none;">&larr; Register another key</a>
            </div>
        """
        )

    return HTMLResponse(
        """
        <div style="font-family: sans-serif; padding: 20px; max-width: 600px; margin: 40px auto; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #2c3e50;">Data Tagger MCP Registration</h2>
            <p style="color: #666;">Enter your API token to generate a personal session URL.</p>
            <form method="post">
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: bold;">API Token:</label>
                    <input type="password" name="api_key" placeholder="Paste your token here" style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;" required>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: bold;">Data Tagger Base URL:</label>
                    <input type="text" name="base_url" value="https://datatagger.ub.tum.de" style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                </div>
                <button type="submit" style="background: #3498db; color: white; border: none; padding: 12px 24px; border-radius: 4px; cursor: pointer; font-size: 1em; width: 100%;">Generate MCP URL</button>
            </form>
        </div>
    """
    )


# --- Standalone Starlette App & Explicit Routing ---

async def session_cleanup_loop():
    """Background task to remove expired sessions."""
    while True:
        try:
            cleanup_expired_sessions()
        except Exception:
            pass
        await asyncio.sleep(300)


# --- Final App Construction (FastAPI) ---

app = FastAPI()

# Registration page
@app.api_route("/register", methods=["GET", "POST"])
async def register_page_route(request: Request):
    return await register_page(request)

# Token Middleware for FastAPI
class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = request.query_params.get("token")
        if token and token in token_store:
            token_store[token]["last_active"] = time.time()
            session_key_var.set(token_store[token]["key"])
            session_base_url_var.set(token_store[token]["base_url"])
        return await call_next(request)

app.add_middleware(TokenAuthMiddleware)

# Mounting the MCP server logic
# Use the native streamable_http_app from FastMCP
try:
    if hasattr(mcp, "streamable_http_app"):
        mcp_app = mcp.streamable_http_app()
        app.mount("/mcp", mcp_app)
        print("DEBUG: Mounted MCP via streamable_http_app on /mcp")
    elif hasattr(mcp, "sse_app"):
        mcp_app = mcp.sse_app()
        app.mount("/mcp", mcp_app)
        print("DEBUG: Mounted MCP via sse_app on /mcp")
    else:
        print("ERROR: No native MCP app method found (tried streamable_http_app, sse_app)")
except Exception as e:
    print(f"ERROR during app mounting: {e}")

# Cleanup task logic
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(session_cleanup_loop())


# --- Authentication & Core Helpers ---


def get_auth_config(ctx: Optional[Context] = None) -> Tuple[str, str]:
    """
    Unified authentication resolver.
    1. Check Token-Store (ContextVar) - Hosted Mode (SSE)
    2. Check Session-Store (FastMCP Context) - Manual stdio configuration
    3. Check Environment Variables - Local Mode (os.environ)
    """
    # 1. Hosted Mode (via Middleware/ContextVar)
    token = session_key_var.get()
    base_url = session_base_url_var.get()

    if token and base_url:
        return token, base_url.rstrip("/")

    # 2. Manual Session Store (via legacy configure_auth tool call in stdio)
    session_id = get_session_id(ctx)
    if session_id and session_id in SESSION_AUTH:
        auth = SESSION_AUTH[session_id]
        return auth["token"], auth["base_url"].rstrip("/")

    # 3. Local Mode (Environment Variables)
    env_token = os.environ.get("FDM_TOKEN", "")
    env_base_url = os.environ.get("FDM_BASE_URL", "https://datatagger.ub.tum.de")

    if env_token:
        return env_token, env_base_url.rstrip("/")

    raise ValueError(
        "No authentication configured. \n"
        "- In local mode: set FDM_TOKEN environment variable.\n"
        "- In hosted mode: Visit /register to generate a URL with a token."
    )


async def make_fdm_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[dict] = None,
    json_payload: Optional[dict] = None,
    ctx: Optional[Context] = None,
) -> dict[str, Any] | str | None:
    """Make a generic HTTP request to the FDM API."""
    try:
        token, base_url = get_auth_config(ctx)
    except ValueError as e:
        return str(e)

    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    url = f"{base_url}{endpoint}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    if params:
        params = {k: v for k, v in params.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            req_kwargs = {"headers": headers, "timeout": 30.0}
            if params:
                req_kwargs["params"] = params
            if json_payload is not None:
                req_kwargs["json"] = json_payload

            response = await client.request(method, url, **req_kwargs)
            response.raise_for_status()

            if response.status_code == 204:
                return "Operation successful (204 No Content)"

            content_type = response.headers.get("content-type", "")
            if "json" in content_type.lower():
                return response.json()
            else:
                return response.text
        except httpx.HTTPStatusError as e:
            return f"API Error ({e.response.status_code}): {e.response.text}"
        except Exception as e:
            return f"Error making {method} request to API: {e}"


def format_json_response(data: Any) -> str:
    """Serialize API response data to a formatted JSON string."""
    if isinstance(data, str):
        return data
    import json

    return json.dumps(data, indent=2)


async def download_fdm_file(
    endpoint: str, dest_path: str, overwrite: bool = False, ctx: Optional[Context] = None
) -> str:
    """Stream a file from the FDM API to a local destination path."""
    if os.path.exists(dest_path) and not overwrite:
        return f"Error: File already exists at {dest_path} and overwrite is False."

    try:
        token, base_url = get_auth_config(ctx)
    except ValueError as e:
        return str(e)

    url = f"{base_url}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
    headers = {"User-Agent": USER_AGENT, "Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET", url, headers=headers, timeout=300.0
            ) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
        return f"File successfully downloaded to: {dest_path}"
    except Exception as e:
        return f"Error downloading file: {e}"


async def upload_fdm_file(
    endpoint: str, file_path: str, ctx: Optional[Context] = None
) -> str:
    """Upload a local file to the FDM API endpoint as multipart form data."""
    if not os.path.exists(file_path):
        return f"Error: File not found exactly at {file_path}."

    try:
        token, base_url = get_auth_config(ctx)
    except ValueError as e:
        return str(e)

    url = f"{base_url}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    try:
        filename = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, mime_type)}
                response = await client.post(
                    url, headers=headers, files=files, timeout=600.0
                )
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "json" in content_type.lower():
                    import json

                    return json.dumps(response.json(), indent=2)
                return response.text
    except Exception as e:
        return f"Error uploading file: {e}"


# --- SECTION: SEARCH ---


# --- SECTION: SEARCH ---


@mcp.tool()
async def search_datatagger(term: str, limit: int = 100, ctx: Optional[Context] = None) -> str:
    """Global search across projects, folders, and uploads."""
    payload = {
        "search_text": term,
        "limit": limit,
        "result_types": [
            "project",
            "folder",
            "dataset",
            "dataset_version",
            "file",
            "template",
            "template_version",
        ],
    }
    return format_json_response(
        await make_fdm_request(
            "/api/v1/search/global/", method="POST", json_payload=payload, ctx=ctx
        )
    )


# --- SECTION: PROJECTS ---


@mcp.tool()
async def list_projects(
    limit: int = 100, offset: int = 0, search: str = "", ctx: Optional[Context] = None
) -> str:
    """List Datatagger projects."""
    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search
    return format_json_response(
        await make_fdm_request("/api/v1/project/", params=params, ctx=ctx)
    )


@mcp.tool()
async def get_project(project_id: str, ctx: Optional[Context] = None) -> str:
    """Get details of a Datatagger project."""
    return format_json_response(
        await make_fdm_request(f"/api/v1/project/{project_id}/", ctx=ctx)
    )


@mcp.tool()
async def create_project(name: str, ctx: Optional[Context] = None) -> str:
    """Create a new project."""
    payload = {"name": name}
    return format_json_response(
        await make_fdm_request(
            "/api/v1/project/", method="POST", json_payload=payload, ctx=ctx
        )
    )


@mcp.tool()
async def update_project(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> str:
    """Update a project."""
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if not payload:
        return "No fields provided to update."
    return format_json_response(
        await make_fdm_request(
            f"/api/v1/project/{project_id}/",
            method="PATCH",
            json_payload=payload,
            ctx=ctx,
        )
    )


@mcp.tool()
async def delete_project(
    project_id: str, confirm_danger: bool = False, ctx: Optional[Context] = None
) -> str:
    """Delete a project. REQUIRED: confirm_danger=True."""
    if not confirm_danger:
        return "ERROR: Deletion rejected. You must set confirm_danger=True."
    return format_json_response(
        await make_fdm_request(
            f"/api/v1/project/{project_id}/", method="DELETE", ctx=ctx
        )
    )


# --- SECTION: FOLDERS ---


@mcp.tool()
async def list_folders(
    project: str = "",
    limit: int = 100,
    offset: int = 0,
    search: str = "",
    ctx: Optional[Context] = None,
) -> str:
    """List folders."""
    params = {"limit": limit, "offset": offset}
    if project:
        params["project"] = project
    if search:
        params["search"] = search
    return format_json_response(
        await make_fdm_request("/api/v1/folder/", params=params, ctx=ctx)
    )


@mcp.tool()
async def get_folder(folder_id: str, ctx: Optional[Context] = None) -> str:
    """Get details of a folder."""
    return format_json_response(
        await make_fdm_request(f"/api/v1/folder/{folder_id}/", ctx=ctx)
    )


@mcp.tool()
async def create_folder(
    project_id: str, name: str, ctx: Optional[Context] = None
) -> str:
    """Create a new folder inside a project."""
    payload = {"project": project_id, "name": name}
    return format_json_response(
        await make_fdm_request(
            "/api/v1/folder/", method="POST", json_payload=payload, ctx=ctx
        )
    )


@mcp.tool()
async def update_folder(
    folder_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> str:
    """Update a folder."""
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if not payload:
        return "No fields provided to update."
    return format_json_response(
        await make_fdm_request(
            f"/api/v1/folder/{folder_id}/",
            method="PATCH",
            json_payload=payload,
            ctx=ctx,
        )
    )


@mcp.tool()
async def delete_folder(
    folder_id: str, confirm_danger: bool = False, ctx: Optional[Context] = None
) -> str:
    """Delete a folder. REQUIRED: confirm_danger=True."""
    if not confirm_danger:
        return "ERROR: Deletion rejected. You must set confirm_danger=True."
    return format_json_response(
        await make_fdm_request(f"/api/v1/folder/{folder_id}/", method="DELETE", ctx=ctx)
    )


# --- SECTION: DATASETS & VERSIONS ---


@mcp.tool()
async def list_datasets(
    folder_id: str = "",
    limit: int = 100,
    offset: int = 0,
    search: str = "",
    ctx: Optional[Context] = None,
) -> str:
    """List dataset entries. Filter by folder_id optional."""
    params = {"limit": limit, "offset": offset}
    if folder_id:
        params["folder"] = folder_id
    if search:
        params["search"] = search
    return format_json_response(
        await make_fdm_request("/api/v1/uploads-dataset/", params=params, ctx=ctx)
    )


@mcp.tool()
async def create_dataset(
    folder_id: str, name: str, ctx: Optional[Context] = None
) -> str:
    """Create a new dataset entry inside a folder."""
    payload = {"folder": folder_id, "name": name}
    return format_json_response(
        await make_fdm_request(
            "/api/v1/uploads-dataset/", method="POST", json_payload=payload, ctx=ctx
        )
    )


@mcp.tool()
async def delete_dataset(
    dataset_id: str, confirm_danger: bool = False, ctx: Optional[Context] = None
) -> str:
    """Delete a dataset. REQUIRED: confirm_danger=True."""
    if not confirm_danger:
        return "ERROR: Deletion rejected. set confirm_danger=True."
    return format_json_response(
        await make_fdm_request(
            f"/api/v1/uploads-dataset/{dataset_id}/", method="DELETE", ctx=ctx
        )
    )


@mcp.tool()
async def publish_dataset(dataset_id: str, ctx: Optional[Context] = None) -> str:
    """Finalize/Commit a dataset (often referred to as 'publishing' internally)."""
    return format_json_response(
        await make_fdm_request(
            f"/api/v1/uploads-dataset/{dataset_id}/publish/",
            method="POST",
            json_payload={},
            ctx=ctx,
        )
    )


@mcp.tool()
async def restore_dataset_version(
    dataset_id: str, uploads_version_id: str, ctx: Optional[Context] = None
) -> str:
    """Restore a dataset to a previous historical version."""
    payload = {"uploads_version": uploads_version_id}
    return format_json_response(
        await make_fdm_request(
            f"/api/v1/uploads-dataset/{dataset_id}/restore/",
            method="POST",
            json_payload=payload,
            ctx=ctx,
        )
    )


@mcp.tool()
async def compare_dataset_versions(
    version_id: str, compare_to_id: str, ctx: Optional[Context] = None
) -> str:
    """Get the diff/comparison between two dataset versions."""
    payload = {"compare": compare_to_id}
    return format_json_response(
        await make_fdm_request(
            f"/api/v1/uploads-version/{version_id}/diff/",
            method="POST",
            json_payload=payload,
            ctx=ctx,
        )
    )


# --- SECTION: UPLOAD & DOWNLOAD FILE DATA ---


@mcp.tool()
async def download_version_file(
    version_id: str, dest_path: str, overwrite: bool = False, ctx: Optional[Context] = None
) -> str:
    """Download a version file dynamically to your local computer's absolute path."""
    return await download_fdm_file(
        f"/api/v1/uploads-version/{version_id}/download/", dest_path, overwrite, ctx=ctx
    )


@mcp.tool()
async def upload_dataset_file(
    dataset_id: str, source_path: str, ctx: Optional[Context] = None
) -> str:
    """Upload a raw file from your local computer into a dataset."""
    return await upload_fdm_file(
        f"/api/v1/uploads-dataset/{dataset_id}/file/", source_path, ctx=ctx
    )


# --- SECTION: PERMISSIONS ---


@mcp.tool()
async def set_folder_permissions(
    folder_id: str,
    folder_users: List[Dict[str, Any]],
    ctx: Optional[Context] = None,
) -> str:
    """Set the user permissions array for a folder."""
    payload = {"folder_users": folder_users}
    return format_json_response(
        await make_fdm_request(
            f"/api/v1/folder/{folder_id}/permissions/",
            method="PUT",
            json_payload=payload,
            ctx=ctx,
        )
    )


@mcp.tool()
async def get_folder_permissions(
    folder_id: str, ctx: Optional[Context] = None
) -> str:
    """List all the active user permissions for a folder."""
    return format_json_response(
        await make_fdm_request(
            "/api/v1/folder-permission/", params={"folder": folder_id}, ctx=ctx
        )
    )


# --- SECTION: METADATA ---


@mcp.tool()
async def list_metadata(
    search: str = "", limit: int = 100, ctx: Optional[Context] = None
) -> str:
    """List available metadata template mappings across Data Tagger."""
    params = {"limit": limit, "search": search}
    return format_json_response(
        await make_fdm_request("/api/v1/metadata/", params=params, ctx=ctx)
    )


@mcp.tool()
async def add_metadata_to_dataset(
    dataset_id: str,
    metadata_items: List[Dict[str, Any]],
    ctx: Optional[Context] = None,
) -> str:
    """Add a batch of metadata item tags (via json) to an existing dataset."""
    # Simulates fdm_uploads_dataset_version_create_with_metadata logic
    payload = {"metadata": metadata_items}
    return format_json_response(
        await make_fdm_request(
            f"/api/v1/uploads-dataset/{dataset_id}/version/",
            method="POST",
            json_payload=payload,
            ctx=ctx,
        )
    )
