import os
import mimetypes
from typing import Any, Optional
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("datatagger")

USER_AGENT = "fdmMCP/1.0"

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

async def make_fdm_request(endpoint: str, params: Optional[dict] = None) -> dict[str, Any] | str | None:
    """Make a request to the FDM API."""
    base_url = get_base_url()
    token = get_token()
    
    # Ensure endpoint starts with /
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
        
    url = f"{base_url}{endpoint}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # Filter out None params
    if params:
        params = {k: v for k, v in params.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            if "json" in content_type.lower():
                return response.json()
            else:
                return response.text
        except Exception as e:
            return f"Error making request to API: {e}"

async def download_fdm_file(endpoint: str, dest_path: str, overwrite: bool = False) -> str:
    """Download a file from FDM API streaming to dest_path."""
    if os.path.exists(dest_path) and not overwrite:
        return f"Error: File already exists at {dest_path} and overwrite is False. If you are sure, use overwrite=True."
    
    base_url = get_base_url()
    token = get_token()
    
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
        
    url = f"{base_url}{endpoint}"
    headers = {
        "User-Agent": USER_AGENT,
        "Authorization": f"Bearer {token}"
    }
    
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
    """Upload a local file to FDM API."""
    if not os.path.exists(file_path):
        return f"Error: File not found exactly at {file_path}. Please check your spelling and absolute path."
        
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

def format_json_response(data: Any) -> str:
    import json
    if isinstance(data, str):
        return data
    return json.dumps(data, indent=2)


@mcp.tool()
async def list_projects(limit: int = 100, offset: int = 0, search: str = "") -> str:
    """List Datatagger projects.
    
    Args:
        limit: Max number of projects to return.
        offset: Offset for pagination.
        search: Optional search term to filter projects.
    """
    params = {
        "limit": limit,
        "offset": offset,
    }
    if search:
        params["search"] = search

    data = await make_fdm_request("/api/v1/project/", params=params)
    return format_json_response(data)


@mcp.tool()
async def list_folders(project: str = "", limit: int = 100, offset: int = 0, search: str = "") -> str:
    """List Datatagger folders.
    
    Args:
        project: Optional project ID (UUID) to filter folders by project.
        limit: Max number of folders to return.
        offset: Offset for pagination.
        search: Optional search term.
    """
    params = {
        "limit": limit,
        "offset": offset,
    }
    if project:
        params["project"] = project
    if search:
        params["search"] = search

    data = await make_fdm_request("/api/v1/folder/", params=params)
    return format_json_response(data)


@mcp.tool()
async def search_datatagger(term: str, limit: int = 100) -> str:
    """Search globally across projects, folders, and other items in Datatagger.
    
    Args:
        term: The search term.
        limit: Max number of results.
    """
    params = {
        "term": term,
        "limit": limit,
        "content_types": "folders.folder,projects.project,uploads.uploadsversion,uploads.uploadsversionfile"
    }
    data = await make_fdm_request("/api/v1/search/global/", params=params)
    return format_json_response(data)


@mcp.tool()
async def get_project(project_id: str) -> str:
    """Get details of a specific Datatagger project by its UUID.
    
    Args:
        project_id: The UUID of the project.
    """
    data = await make_fdm_request(f"/api/v1/project/{project_id}/")
    return format_json_response(data)


@mcp.tool()
async def get_folder(folder_id: str) -> str:
    """Get details of a specific Datatagger folder by its UUID.
    
    Args:
        folder_id: The UUID of the folder.
    """
    data = await make_fdm_request(f"/api/v1/folder/{folder_id}/")
    return format_json_response(data)

@mcp.tool()
async def download_version_file(version_id: str, dest_path: str, overwrite: bool = False) -> str:
    """Download a Datatagger uploads-version file to a local destination.
    
    Args:
        version_id: The UUID of the uploads-version.
        dest_path: The absolute path on your computer where the file should be saved (e.g. C:\\temp\\data.csv).
        overwrite: Set to True to overwrite if the file already exists.
    """
    return await download_fdm_file(f"/api/v1/uploads-version/{version_id}/download/", dest_path, overwrite)

@mcp.tool()
async def upload_dataset_file(dataset_id: str, source_path: str) -> str:
    """Upload a local file into a Datatagger uploads-dataset.
    
    Args:
        dataset_id: The UUID of the uploads-dataset to upload to.
        source_path: The absolute path on your computer of the file to upload (e.g. C:\\temp\\data.csv).
    """
    return await upload_fdm_file(f"/api/v1/uploads-dataset/{dataset_id}/file/", source_path)


if __name__ == "__main__":
    mcp.run(transport="stdio")
