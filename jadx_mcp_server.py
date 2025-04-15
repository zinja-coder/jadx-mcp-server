import httpx
from typing import List, Optional
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("JADX-AI-MCP Plugin Reverse Engineering Server")

# To do : implement logic to handle the scenario where port is not available
JADX_HTTP_BASE = "http://localhost:8650" # Base URL for the JADX-AI-MCP Plugin


# Generic function to request data from the plugin
async def get_from_jadx(endpoint: str, params: dict = {}) -> Optional[str]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{JADX_HTTP_BASE}/{endpoint}", params=params, timeout=10)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        return f"Error: {e}"

# Specific MCP tools

@mcp.tool(name="fetch_current_class", description="Fetch the currently selected class and its code from the JADX-GUI plugin.")
async def fetch_current_class() -> dict:
    """Fetch the current class name and source code from the JADX-GUI plugin running locally."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{JADX_HTTP_BASE}/current-class", timeout=10.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        return {"error": f"Failed to fetch from JADX plugin: {str(e)}"}

@mcp.tool()
async def get_selected_text() -> str:
    """Returns the currently selected text in the decompiled code view."""
    return await get_from_jadx("selected-text")

@mcp.tool()
async def get_method_by_name(class_name: str, method_name: str) -> str:
    """Fetch the source code of a method from a specific class."""
    return await get_from_jadx("method-by-name", {"class": class_name, "method": method_name})

@mcp.tool()
async def get_all_classes() -> List[str]:
    """Returns a list of all classes in the project."""
    response = await get_from_jadx(f"all-classes")
    return response.splitlines() if response else []

@mcp.tool()
async def get_class_source(class_name: str) -> str:
    """Fetch the Java source of a specific class."""
    return await get_from_jadx("class-source", {"class": class_name})

@mcp.tool()
async def search_method_by_name(method_name: str) -> List[str]:
    """Search for a method name across all classes."""
    response = await get_from_jadx("search-method", {"method": method_name})
    return response.splitlines() if response else []

@mcp.tool()
async def get_methods_of_class(class_name: str) -> List[str]:
    """List all method names in a class."""
    response = await get_from_jadx("methods-of-class", {"class": class_name})
    return response.splitlines() if response else []

@mcp.tool()
async def get_fields_of_class(class_name: str) -> List[str]:
    """List all field names in a class."""
    response = await get_from_jadx("fields-of-class", {"class": class_name})
    return response.splitlines() if response else []

@mcp.tool()
async def get_method_code(class_name: str, method_name: str) -> str:
    """Fetch the full method code (alias for get_method_by_name)."""
    return await get_method_by_name(class_name, method_name)

@mcp.tool()
async def get_smali_of_class(class_name: str) -> str:
    """Fetch the smali representation of a class."""
    return await get_from_jadx("smali-of-class", {"class": class_name})

if __name__ == "__main__":
    mcp.run(transport="stdio")
