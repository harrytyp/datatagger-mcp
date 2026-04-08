import os
import mimetypes
from typing import Any, Optional, Dict, List
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("datatagger")
USER_AGENT = "fdmMCP/1.0"

# --- Authentication & Core Helpers ---

def get_base_url() -> str:
    url = os.environ.get("FDM_BASE_URL", "")
    if not url:
        raise ValueError("FDM_BASE_URL environment variable is not set")
    return url.rstrip('/')

def get_token() -> str:
    token = os.environ.get("FDM_TOKEN", "")
    if not token:
        raise ValueError("FDM_TOKEN environment variable is not set")
    return token

async def make_fdm_request(endpoint: str, method: str = "GET", params: Optional[dict] = None, json_payload: Optional[dict] = None) -> dict[str, Any] | str | None:
    """Make a generic HTTP request to the FDM API."""
    base_url = get_base_url()
    token = get_token()
    
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
        
    url = f"{base_url}{endpoint}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
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
    if isinstance(data, str):
        return data
    import json
    return json.dumps(data, indent=2)

async def download_fdm_file(endpoint: str, dest_path: str, overwrite: bool = False) -> str:
    if os.path.exists(dest_path) and not overwrite:
        return f"Error: File already exists at {dest_path} and overwrite is False."
    
    url = f"{get_base_url()}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
    headers = {"User-Agent": USER_AGENT, "Authorization": f"Bearer {get_token()}"}
    
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url, headers=headers, timeout=300.0) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
        return f"File successfully downloaded to: {dest_path}"
    except Exception as e:
        return f"Error downloading file: {e}"

async def upload_fdm_file(endpoint: str, file_path: str) -> str:
    if not os.path.exists(file_path):
        return f"Error: File not found exactly at {file_path}."
        
    url = f"{get_base_url()}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Authorization": f"Bearer {get_token()}"
    }

    try:
        filename = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"
            
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, mime_type)}
                response = await client.post(url, headers=headers, files=files, timeout=600.0)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "json" in content_type.lower():
                    import json
                    return json.dumps(response.json(), indent=2)
                return response.text
    except Exception as e:
        return f"Error uploading file: {e}"

# --- SECTION: SEARCH ---

@mcp.tool()
async def search_datatagger(term: str, limit: int = 100) -> str:
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
            "template_version"
        ]
    }
    return format_json_response(await make_fdm_request("/api/v1/search/global/", method="POST", json_payload=payload))

# --- SECTION: PROJECTS ---

@mcp.tool()
async def list_projects(limit: int = 100, offset: int = 0, search: str = "") -> str:
    """List Datatagger projects."""
    params = {"limit": limit, "offset": offset}
    if search: params["search"] = search
    return format_json_response(await make_fdm_request("/api/v1/project/", params=params))

@mcp.tool()
async def get_project(project_id: str) -> str:
    """Get details of a Datatagger project."""
    return format_json_response(await make_fdm_request(f"/api/v1/project/{project_id}/"))

@mcp.tool()
async def create_project(name: str) -> str:
    """Create a new project."""
    payload = {"name": name}
    return format_json_response(await make_fdm_request("/api/v1/project/", method="POST", json_payload=payload))

@mcp.tool()
async def update_project(project_id: str, name: Optional[str] = None, description: Optional[str] = None) -> str:
    """Update a project."""
    payload = {}
    if name is not None: payload["name"] = name
    if description is not None: payload["description"] = description
    if not payload: return "No fields provided to update."
    return format_json_response(await make_fdm_request(f"/api/v1/project/{project_id}/", method="PATCH", json_payload=payload))

@mcp.tool()
async def delete_project(project_id: str, confirm_danger: bool = False) -> str:
    """Delete a project. REQUIRED: confirm_danger=True"""
    if not confirm_danger: return "ERROR: Deletion rejected. You must set confirm_danger=True."
    return format_json_response(await make_fdm_request(f"/api/v1/project/{project_id}/", method="DELETE"))

# --- SECTION: FOLDERS ---

@mcp.tool()
async def list_folders(project: str = "", limit: int = 100, offset: int = 0, search: str = "") -> str:
    """List folders."""
    params = {"limit": limit, "offset": offset}
    if project: params["project"] = project
    if search: params["search"] = search
    return format_json_response(await make_fdm_request("/api/v1/folder/", params=params))

@mcp.tool()
async def get_folder(folder_id: str) -> str:
    """Get details of a folder."""
    return format_json_response(await make_fdm_request(f"/api/v1/folder/{folder_id}/"))

@mcp.tool()
async def create_folder(project_id: str, name: str) -> str:
    """Create a new folder inside a project."""
    payload = {"project": project_id, "name": name}
    return format_json_response(await make_fdm_request("/api/v1/folder/", method="POST", json_payload=payload))

@mcp.tool()
async def update_folder(folder_id: str, name: Optional[str] = None, description: Optional[str] = None) -> str:
    """Update a folder."""
    payload = {}
    if name is not None: payload["name"] = name
    if description is not None: payload["description"] = description
    if not payload: return "No fields provided to update."
    return format_json_response(await make_fdm_request(f"/api/v1/folder/{folder_id}/", method="PATCH", json_payload=payload))

@mcp.tool()
async def delete_folder(folder_id: str, confirm_danger: bool = False) -> str:
    """Delete a folder. REQUIRED: confirm_danger=True"""
    if not confirm_danger: return "ERROR: Deletion rejected. You must set confirm_danger=True."
    return format_json_response(await make_fdm_request(f"/api/v1/folder/{folder_id}/", method="DELETE"))

# --- SECTION: DATASETS & VERSIONS ---

@mcp.tool()
async def list_datasets(folder_id: str = "", limit: int = 100, offset: int = 0, search: str = "") -> str:
    """List dataset entries. Filter by folder_id optional."""
    params = {"limit": limit, "offset": offset}
    if folder_id: params["folder"] = folder_id
    if search: params["search"] = search
    return format_json_response(await make_fdm_request("/api/v1/uploads-dataset/", params=params))

@mcp.tool()
async def create_dataset(folder_id: str, name: str) -> str:
    """Create a new dataset entry inside a folder."""
    payload = {"folder": folder_id, "name": name}
    return format_json_response(await make_fdm_request("/api/v1/uploads-dataset/", method="POST", json_payload=payload))

@mcp.tool()
async def delete_dataset(dataset_id: str, confirm_danger: bool = False) -> str:
    """Delete a dataset. REQUIRED: confirm_danger=True"""
    if not confirm_danger: return "ERROR: Deletion rejected. set confirm_danger=True."
    return format_json_response(await make_fdm_request(f"/api/v1/uploads-dataset/{dataset_id}/", method="DELETE"))

@mcp.tool()
async def publish_dataset(dataset_id: str) -> str:
    """Finalize/Commit a dataset (often referred to as 'publishing' internally).
    Note: In Data Tagger, this is used to commit an upload into a folder, not to make it public on the web!
    """
    return format_json_response(await make_fdm_request(f"/api/v1/uploads-dataset/{dataset_id}/publish/", method="POST", json_payload={}))

@mcp.tool()
async def restore_dataset_version(dataset_id: str, uploads_version_id: str) -> str:
    """Restore a dataset to a previous historical version."""
    payload = {"uploads_version": uploads_version_id}
    return format_json_response(await make_fdm_request(f"/api/v1/uploads-dataset/{dataset_id}/restore/", method="POST", json_payload=payload))

@mcp.tool()
async def compare_dataset_versions(version_id: str, compare_to_id: str) -> str:
    """Get the diff/comparison between two dataset versions."""
    payload = {"compare": compare_to_id}
    return format_json_response(await make_fdm_request(f"/api/v1/uploads-version/{version_id}/diff/", method="POST", json_payload=payload))

# --- SECTION: UPLOAD & DOWNLOAD FILE DATA ---

@mcp.tool()
async def download_version_file(version_id: str, dest_path: str, overwrite: bool = False) -> str:
    """Download a version file dynamically to your local computer's absolute path."""
    return await download_fdm_file(f"/api/v1/uploads-version/{version_id}/download/", dest_path, overwrite)

@mcp.tool()
async def upload_dataset_file(dataset_id: str, source_path: str) -> str:
    """Upload a raw file from your local computer into a dataset."""
    return await upload_fdm_file(f"/api/v1/uploads-dataset/{dataset_id}/file/", source_path)

# --- SECTION: PERMISSIONS ---

@mcp.tool()
async def set_folder_permissions(folder_id: str, folder_users: List[Dict[str, Any]]) -> str:
    """Set the user permissions array for a folder.
    CRITICAL: The folder_users payload MUST be a list of dictionaries explicitly defining 'email' and 'is_folder_admin'.
    Example format: [{"email": "user@ub.tum.de", "is_folder_admin": False}]
    """
    payload = {"folder_users": folder_users}
    return format_json_response(await make_fdm_request(f"/api/v1/folder/{folder_id}/permissions/", method="PUT", json_payload=payload))

@mcp.tool()
async def get_folder_permissions(folder_id: str) -> str:
    """List all the active user permissions for a folder."""
    return format_json_response(await make_fdm_request("/api/v1/folder-permission/", params={"folder": folder_id}))

# --- SECTION: METADATA ---

@mcp.tool()
async def list_metadata(search: str = "", limit: int = 100) -> str:
    """List available metadata template mappings across Data Tagger."""
    params = {"limit": limit, "search": search}
    return format_json_response(await make_fdm_request("/api/v1/metadata/", params=params))

@mcp.tool()
async def add_metadata_to_dataset(dataset_id: str, metadata_items: List[Dict[str, Any]]) -> str:
    """Add a batch of metadata item tags (via json) to an existing dataset."""
    # Simulates fdm_uploads_dataset_version_create_with_metadata logic
    payload = {"metadata": metadata_items}
    return format_json_response(await make_fdm_request(f"/api/v1/uploads-dataset/{dataset_id}/version/", method="POST", json_payload=payload))


if __name__ == "__main__":
    mcp.run(transport="stdio")
