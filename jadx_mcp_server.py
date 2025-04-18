# /// script
# dependencies = [ "fastmcp", "httpx", "logging" ]
# ///

import httpx
from typing import List, Union
from mcp.server.fastmcp import FastMCP

# Set up logging configuration
logger = logging.getLogger()
logger.setLevel(logging.ERROR)

# Console handler for logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Initialize the MCP server
mcp = FastMCP("JADX-AI-MCP Plugin Reverse Engineering Server")

# To do : implement logic to handle the scenario where port is not available
JADX_HTTP_BASE = "http://localhost:8650" # Base URL for the JADX-AI-MCP Plugin

async def get_from_jadx(endpoint: str, params: dict = {}) -> Union[str, dict]:
    """Generic helper to request data from the JADX plugin with proper error reporting and logging."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{JADX_HTTP_BASE}/{endpoint}", params=params, timeout=60)
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPStatusError as e:
        error_message = f"HTTP error {e.response.status_code}: {e.response.text}"
        logger.error(error_message)
        return {"error": f"{error_message}."}
    except httpx.RequestError as e:
        error_message = f"Request failed: {str(e)}"
        logger.error(error_message)
        return {"error": f"{error_message}."}
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logger.error(error_message)
        return {"error": f"{error_message}."}

# Specific MCP tools

@mcp.tool(name="fetch_current_class", description="Fetch the currently selected class and its code from the JADX-GUI plugin.")
async def fetch_current_class() -> dict:
    """Fetch currently opened class in jadx"""
    return await get_from_jadx("current-class")

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

@mcp.tool()
async def get_android_manifest() -> dict:
    """Retrieve and return the AndroidManifest.xml content."""
    return await get_from_jadx("manifest")
    
@mcp.tool()
async def get_main_application_class() -> dict:
    """Fetch the main application class as defined in the AndroidManifest.xml."""
    return await get_from_jadx("main-application")
    
@mcp.tool()
async def get_main_activity_class() -> dict:
    """Fetch the main activity class as defined in the AndroidManifest.xml."""
    return await get_from_jadx("main-activity")
    
if __name__ == "__main__":
    mcp.run(transport="stdio")
