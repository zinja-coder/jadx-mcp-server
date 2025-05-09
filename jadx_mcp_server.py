# /// script
# dependencies = [ "fastmcp", "httpx", "logging" ]
# ///

import httpx
import logging
import time  
import random

from typing import List, Union, Dict, Optional
from mcp.server.fastmcp import FastMCP

# Cache configuration
CACHE_EXPIRY = 300  # 5 minutes in seconds
_cache: Dict[str, tuple[float, List[str]]] = {}  # {key: (timestamp, data)}

def _get_from_cache(key: str) -> Optional[List[str]]:
    """Get data from cache if it exists and is not expired."""
    current_time = time.time()
    
    # Check if key exists and is not expired
    if key in _cache:
        timestamp, data = _cache[key]
        if current_time - timestamp < CACHE_EXPIRY:
            return data
        # Remove expired item
        del _cache[key]
    
    # Periodically clean up other expired items (e.g., every 10 accesses)
    # This helps prevent memory issues from accumulating expired entries
    if random.random() < 0.1:  # ~10% chance to clean up
        expired_keys = [k for k, (ts, _) in _cache.items() 
                      if current_time - ts >= CACHE_EXPIRY]
        for k in expired_keys:
            del _cache[k]
            
    return None

def _set_cache(key: str, data: List[str]) -> None:
    """Store data in cache with current timestamp."""
    _cache[key] = (time.time(), data)

def _clear_cache() -> None:
    """Clear all cached data."""
    _cache.clear()


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


# Generic method to fetch data from jadx
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
    """Fetch currently opened class in jadx.
    
    Args:
        None

    Returns:
        Dictionary containing currently opened class in jadx. 
    """
    return await get_from_jadx("current-class")

@mcp.tool()
async def get_selected_text() -> str:
    """Returns the currently selected text in the decompiled code view.
    
    Args:
        None

    Returns:
        String containing currently highlighted/selected text in jadx-gui.
    """
    return await get_from_jadx("selected-text")

@mcp.tool()
async def get_method_by_name(class_name: str, method_name: str) -> dict:
    """Fetch the source code of a method from a specific class.
    
    Args:
        class_name: Name of the class whose method's code will be returned
        method_name: Name of the method whose code will be returned

    Returns:
        Code of requested method as String.
    """
    return await get_from_jadx("method-by-name", {"class": class_name, "method": method_name})

@mcp.tool()
async def get_all_classes(offset: int = 0, count: int = 0) -> List[str]:
    """Returns a list of all classes in the project with pagination.
    
    Args:
        offset: Offset to start listing from (start at 0)
        count: Number of strings to list (0 means remainder)
    
    Returns:
        A list of all classes in the project.
    """
    # Validate offset and count are non-negative
    offset = max(0, offset)
    count = max(0, count)
    
    cache_key = "all_classes"
    all_classes = _get_from_cache(cache_key)
    
    if all_classes is None:
        response = await get_from_jadx(f"all-classes")
        if isinstance(response, dict):
            all_classes = response.get("classes", [])
        else:
            import json
            try:
                parsed = json.loads(response)
                all_classes = parsed.get("classes", [])
            except (json.JSONDecodeError, AttributeError):
                all_classes = []
        _set_cache(cache_key, all_classes)
    
    if offset >= len(all_classes):
        return []
    
    if count > 0:
        return all_classes[offset:offset + count]
    return all_classes[offset:]

@mcp.tool()
async def get_class_source(class_name: str) -> str:
    """Fetch the Java source of a specific class.
    
    Args:
        class_name: Name of the class whose source code will be returned

    Returns:
        Code of requested class as String.
    """
    return await get_from_jadx("class-source", {"class": class_name})

@mcp.tool()
async def search_method_by_name(method_name: str, offset: int = 0, count: int = 0) -> List[str]:
    """Search for a method name across all classes with pagination.
    
    Args:
        method_name: The name of the method to search for
        offset: Offset to start listing from (start at 0)
        count: Number of strings to list (0 means remainder)
    
    Returns:
        A list of all classes containing the method.
    """
    # Validate offset and count are non-negative
    offset = max(0, offset)
    count = max(0, count)
    
    cache_key = f"search_method_{method_name}"
    all_matches = _get_from_cache(cache_key)
    
    if all_matches is None:
        response = await get_from_jadx("search-method", {"method": method_name})
        all_matches = response.splitlines() if response else []
        _set_cache(cache_key, all_matches)
    
    if offset >= len(all_matches):
        return []
    
    if count > 0:
        return all_matches[offset:offset + count]
    return all_matches[offset:]

@mcp.tool()
async def get_methods_of_class(class_name: str, offset: int = 0, count: int = 0) -> List[str]:
    """List all method names in a class with pagination.
    
    Args:
        class_name: The name of the class to search for
        offset: Offset to start listing from (start at 0)
        count: Number of strings to list (0 means remainder)
    
    Returns:
        A list of all methods in the class.
    """
    # Validate offset and count are non-negative
    offset = max(0, offset)
    count = max(0, count)
    
    cache_key = f"methods_of_class_{class_name}"
    all_methods = _get_from_cache(cache_key)
    
    if all_methods is None:
        response = await get_from_jadx("methods-of-class", {"class": class_name})
        all_methods = response.splitlines() if response else []
        _set_cache(cache_key, all_methods)
    
    if offset >= len(all_methods):
        return []
    
    if count > 0:
        return all_methods[offset:offset + count]
    return all_methods[offset:]

@mcp.tool()
async def get_fields_of_class(class_name: str, offset: int = 0, count: int = 0) -> List[str]:
    """List all field names in a class with pagination.
    
    Args:
        class_name: The name of the class to search for
        offset: Offset to start listing from (start at 0)
        count: Number of strings to list (0 means remainder)
    
    Returns:
        A list of all fields in the class.
    """
    # Validate offset and count are non-negative
    offset = max(0, offset)
    count = max(0, count)
    
    cache_key = f"fields_of_class_{class_name}"
    all_fields = _get_from_cache(cache_key)
    
    if all_fields is None:
        response = await get_from_jadx("fields-of-class", {"class": class_name})
        all_fields = response.splitlines() if response else []
        _set_cache(cache_key, all_fields)
    
    if offset >= len(all_fields):
        return []
    
    if count > 0:
        return all_fields[offset:offset + count]
    return all_fields[offset:]

@mcp.tool()
async def get_smali_of_class(class_name: str) -> str:
    """Fetch the smali representation of a class.
    
    Args:
        class_name: Name of the class whose smali is to be returned

    Returns:
        Smali code of the requested class as String.
    """
    return await get_from_jadx("smali-of-class", {"class": class_name})

@mcp.tool()
async def get_android_manifest() -> dict:
    """Retrieve and return the AndroidManifest.xml content.
    
    Args:
        None

    Returns:
        Dictionary containing content of AndroidManifest.xml file.
    """
    return await get_from_jadx("manifest")

@mcp.tool()
async def get_strings() -> dict:
    """Retrieve contents of strings.xml files that exists in application

    Args:
        None

    Returns:
        Dictionary containing contents of strings.xml file.
    """
    return await get_from_jadx("strings")

@mcp.tool()
async def get_all_resource_file_names() -> list[str]:
    """Retrieve all resource files names that exists in application

    Args:
        None

    Returns:
        List of all resource files names.
    """
    return await get_from_jadx("list-all-resource-files-names")

@mcp.tool()
async def get_resource_file(resource_name: str) -> list[str]:
    """Retrieve resource file content

    Args:
        resource_name: Name of the resource file

    Returns:
        Gets the content of resource file specified in 'resource_name' parameter
    """
    return await get_from_jadx("get-resource-file", {"name": resource_name})
    
@mcp.tool()
async def get_main_application_classes_names(offset: int = 0, count: int = 0) -> List[str]:
    """Fetch all the main application classes' names based on the package name defined in the AndroidManifest.xml.
    
    Args:
        offset: Offset to start listing from (start at 0)
        count: Number of strings to list (0 means remainder)

    Returns:
        Dictionary containing all the main application's classes' names based on the package name defined in the AndroidManifest.xml file.
    """
    
    offset = max(0, offset)
    count = max(0, count)

    cache_key = "main_application_classes_names"
    class_names = _get_from_cache(cache_key)

    if class_names is None:
        response = await get_from_jadx("main-application-classes-names")
        if isinstance(response, dict):
            class_names = response.get("classes", [])
        else:
            import json
            try:
                parsed = json.loads(response)
                class_info_list = parsed.get("classes", [])
                class_names = [cls_info.get("name") for cls_info in class_info_list if "name" in cls_info]
            except (json.JSONDecodeError, AttributeError):
                class_names = []
            _set_cache(cache_key, class_names)
    
    if offset >= len(class_names):
        return []
    
    return class_names[offset:offset + count] if count > 0 else class_names[offset:]

@mcp.tool()
async def get_main_application_classes_code(offset: int = 0, count: int = 0) -> List[dict]:
    """Fetch all the main application classes' code based on the package name defined in the AndroidManifest.xml.
    
    Args:
        offset: Offset to start listing from (start at 0)
        count: Number of strings to list (0 means remainder)

    Returns:
        Dictionary containing all classes' source code which are under main package only based on package name defined in the AndroidManifest.xml file.
    """

    offset = max(0, offset)
    count = max(0, count)

    cache_key = "main_application_classes_code"
    class_sources = _get_from_cache(cache_key)

    if class_sources is None:
        response = await get_from_jadx("main-application-classes-code")
        import json
        try:
            parsed = json.loads(response)
            class_sources = parsed.get("allClassesInPackage", [])
        except (json.JSONDecodeError, AttributeError):
            class_sources = []
        _set_cache(cache_key, class_sources)
    
    if offset >= len(class_sources):
        return []
    
    return class_sources[offset:offset + count] if count > 0 else class_sources[offset:]
    
@mcp.tool()
async def get_main_activity_class(offset: int = 0, count: int = 0) -> List[dict]:
    """Fetch the main activity class as defined in the AndroidManifest.xml.
    
    Args:
        None

    Returns:
        Dictionary containing content of main activity class defined in AndroidManifest.xml file.
    """
    return await get_from_jadx("main-activity")
    
if __name__ == "__main__":
    mcp.run(transport="stdio")
