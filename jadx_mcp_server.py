# /// script
# requires-python = ">=3.10"
# dependencies = [ "fastmcp", "httpx", "logging", "argparse" ]
# ///

"""
Copyright (c) 2025 jadx mcp server developer(s) (https://github.com/zinja-coder/jadx-ai-mcp)
See the file 'LICENSE' for copying permission
"""

import httpx
import logging
import argparse
import json

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

# Parse the arguments
parser = argparse.ArgumentParser("MCP Server for Jadx")
parser.add_argument("--http", help="Serve MCP Server over HTTP stream.", action="store_true", default=False)
parser.add_argument("--port", help="Specify the port number for --http to serve on. (default:8651)", default=8651, type=int)
parser.add_argument("--jadx-port", help="Specify the port on which JADX AI MCP Plugin is running on. (default:8650)", default=8650, type=int)
args = parser.parse_args()

JADX_HTTP_BASE = f"http://127.0.0.1:{args.jadx_port}" # Base URL for the JADX-AI-MCP Plugin
#print(JADX_HTTP_BASE)

## jadx ai mcp plugin server health ping

def health_ping() -> Union[str, dict]:
    print(f"Attempting to connect to {JADX_HTTP_BASE}/health")
    try:
        with httpx.Client() as client:
            print("Making HTTP request...")
            resp = client.get(f"{JADX_HTTP_BASE}/health", timeout=60)
            print(f"Response status: {resp.status_code}")
            resp.raise_for_status()
            print(f"Response text: {resp.text}")
            return resp.text
    except httpx.HTTPStatusError as e:
        error_message = f"HTTP error {e.response.status_code}: {e.response.text}"
        print(f"HTTP Status Error: {error_message}")
        return {"error": f"{error_message}."}
    except httpx.RequestError as e:
        error_message = f"Request failed: {str(e)}"
        print(f"Request Error: {error_message}")
        return {"error": f"{error_message}."}
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        print(f"Unexpected Error: {error_message}")
        return {"error": f"{error_message}."}      

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

@mcp.tool(name="get_selected_text", description="Returns the currently selected text in the decompiled code view.")
async def get_selected_text() -> str:
    """Returns the currently selected text in the decompiled code view.
    
    Args:
        None

    Returns:
        String containing currently highlighted/selected text in jadx-gui.
    """
    return await get_from_jadx("selected-text")

@mcp.tool(name="get_method_by_name", description="Fetch the source code of a method from a specific class.")
async def get_method_by_name(class_name: str, method_name: str) -> dict:
    """Fetch the source code of a method from a specific class.
    
    Args:
        class_name: Name of the class whose method's code will be returned
        method_name: Name of the method whose code will be returned

    Returns:
        Code of requested method as String.
    """
    return await get_from_jadx("method-by-name", {"class": class_name, "method": method_name})

@mcp.tool(name="get_all_classes", description="Returns a list of all classes in the project.")
async def get_all_classes(offset: int = 0, count: int = 0) -> List[str]:
    """Returns a list of all classes in the project.
    
    Args:
        offset: Offset to start listing from (start at 0)
        count: Number of strings to list (0 means remainder)
    
    Returns:
        A list of all classes in the project.
    """
    offset = max(0, offset)
    count = max(0, count)
    
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
    
    if offset >= len(all_classes):
        return []
    
    if count > 0:
        return all_classes[offset:offset + count]
    return all_classes[offset:]

@mcp.tool(name="get_class_sources", description="Fetch the Java source of a specific class.")
async def get_class_source(class_name: str) -> str:
    """Fetch the Java source of a specific class.
    
    Args:
        class_name: Name of the class whose source code will be returned

    Returns:
        Code of requested class as String.
    """
    return await get_from_jadx("class-source", {"class": class_name})

@mcp.tool(name="search_method_by_name", description="Search for a method name across all classes.")
async def search_method_by_name(method_name: str, offset: int = 0, count: int = 0) -> List[str]:
    """Search for a method name across all classes.
    
    Args:
        method_name: The name of the method to search for
        offset: Offset to start listing from (start at 0)
        count: Number of strings to list (0 means remainder)
    
    Returns:
        A list of all classes containing the method.
    """
    offset = max(0, offset)
    count = max(0, count)
    
    response = await get_from_jadx("search-method", {"method": method_name})
    all_matches = response.splitlines() if response else []
    
    if offset >= len(all_matches):
        return []
    
    if count > 0:
        return all_matches[offset:offset + count]
    return all_matches[offset:]

@mcp.tool(name="get_methods_of_class", description="List all method names in a class.")
async def get_methods_of_class(class_name: str, offset: int = 0, count: int = 0) -> List[str]:
    """List all method names in a class.
    
    Args:
        class_name: The name of the class to search for
        offset: Offset to start listing from (start at 0)
        count: Number of strings to list (0 means remainder)
    
    Returns:
        A list of all methods in the class.
    """
    offset = max(0, offset)
    count = max(0, count)
    
    response = await get_from_jadx("methods-of-class", {"class": class_name})
    all_methods = response.splitlines() if response else []
    
    if offset >= len(all_methods):
        return []
    
    if count > 0:
        return all_methods[offset:offset + count]
    return all_methods[offset:]

@mcp.tool(name="get_fields_of_class", description="List all field names in a class.")
async def get_fields_of_class(class_name: str, offset: int = 0, count: int = 0) -> List[str]:
    """List all field names in a class.
    
    Args:
        class_name: The name of the class to search for
        offset: Offset to start listing from (start at 0)
        count: Number of strings to list (0 means remainder)
    
    Returns:
        A list of all fields in the class.
    """
    offset = max(0, offset)
    count = max(0, count)
    
    response = await get_from_jadx("fields-of-class", {"class": class_name})
    all_fields = response.splitlines() if response else []
    
    if offset >= len(all_fields):
        return []
    
    if count > 0:
        return all_fields[offset:offset + count]
    return all_fields[offset:]

@mcp.tool(name="get_smali_of_class", description="Fetch the smali representation of a class.")
async def get_smali_of_class(class_name: str) -> str:
    """Fetch the smali representation of a class.
    
    Args:
        class_name: Name of the class whose smali is to be returned

    Returns:
        Smali code of the requested class as String.
    """
    return await get_from_jadx("smali-of-class", {"class": class_name})

@mcp.tool(name="get_android_manifest", description="Retrieve and return the AndroidManifest.xml content.")
async def get_android_manifest() -> dict:
    """Retrieve and return the AndroidManifest.xml content.
    
    Args:
        None

    Returns:
        Dictionary containing content of AndroidManifest.xml file.
    """
    manifest = await get_from_jadx("manifest")
    if isinstance(manifest, str):
        return json.loads(manifest)
    return manifest

@mcp.tool(name="get_strings", description="Retrieve contents of strings.xml files that exists in application.")
async def get_strings() -> dict:
    """Retrieve contents of strings.xml files that exists in application

    Args:
        None

    Returns:
        Dictionary containing contents of strings.xml file.
    """
    return await get_from_jadx("strings")

@mcp.tool(name="get_all_resource_file_names", description="Retrieve all resource files names that exists in application.")
async def get_all_resource_file_names() -> dict:
    """Retrieve all resource files names that exists in application

    Args:
        None

    Returns:
        List of all resource files names.
    """
    return await get_from_jadx("list-all-resource-files-names")

@mcp.tool(name="get_resource_file", description="Retrieve resource file content.")
async def get_resource_file(resource_name: str) -> dict:
    """Retrieve resource file content

    Args:
        resource_name: Name of the resource file

    Returns:
        Gets the content of resource file specified in 'resource_name' parameter
    """
    return await get_from_jadx("get-resource-file", {"name": resource_name})
    
@mcp.tool(name="get_main_application_classes_names", description="Fetch all the main application classes' names based on the package name defined in the AndroidManifest.xml.")
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
    
    if offset >= len(class_names):
        return []
    
    return class_names[offset:offset + count] if count > 0 else class_names[offset:]

@mcp.tool(name="get_main_application_classes_code", description="Fetch all the main application classes' code based on the package name defined in the AndroidManifest.xml.")
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

    response = await get_from_jadx("main-application-classes-code")
    import json
    try:
        parsed = json.loads(response)
        class_sources = parsed.get("allClassesInPackage", [])
    except (json.JSONDecodeError, AttributeError):
        class_sources = []
    
    if offset >= len(class_sources):
        return []
    
    return class_sources[offset:offset + count] if count > 0 else class_sources[offset:]
    
@mcp.tool(name="get_main_activity_class", description="Fetch the main activity class as defined in the AndroidManifest.xml.")
async def get_main_activity_class() -> dict:
    """Fetch the main activity class as defined in the AndroidManifest.xml.
    
    Args:
        None

    Returns:
        Dictionary containing content of main activity class defined in AndroidManifest.xml file.
    """
    return await get_from_jadx("main-activity")

@mcp.tool(name="rename_class", description="rename specific class name to one better understanding name,input class name must contain package name")
async def rename_class(class_name: str, new_name: str):
    """Renames a specific class.

    Args:
        class_name (str): The full name of the class to be renamed, including package name.
        new_name (str): The new name for the class.

    Returns:
        dict: The response from the JADX server.
    """
    return await get_from_jadx("rename-class", {"class": class_name, "newName": new_name})

@mcp.tool(name="rename_method", description="rename specific method name to one better understanding name,input method name must contain package name and class name")
async def rename_method(method_name: str, new_name: str):
    """Renames a specific method.

    Args:
        method_name (str): The full name of the method to be renamed, including package and class name.
        new_name (str): The new name for the method.

    Returns:
        dict: The response from the JADX server.
    """
    return await get_from_jadx("rename-method", {"method": method_name, "newName": new_name})

@mcp.tool(name="rename_field", description="rename specific field name to one better understanding name,must input full class name and field name")
async def rename_field(class_name: str,field_name: str, new_name: str):
    """Renames a specific field.

    Args:
        class_name (str): The full class name of field
        field_name (str): The field to be rename.
        new_name (str): The new name for the field.

    Returns:
        dict: The response from the JADX server.
    """
    return await get_from_jadx("rename-field", {"class": class_name, "field":field_name,"newFieldName": new_name})
    
if __name__ == "__main__":
    print("JADX MCP SERVER\n - By ZinjaCoder (https://github.com/zinja-coder) \n - To Report Issues: https://github.com/zinja-coder/jadx-mcp-server/issues\n")
    print("[------------------------------ Stand By Checking JADX AI MCP Plugin Connectivity ------------------------------]")
    print("Testing health check...")
    result = health_ping()
    print(f"Final result: {result}")
    if args.http:
        if args.port:
            mcp.run(transport="http",port=args.port)
        else:
            mcp.run(transport="http",port=8651)
    else:
        mcp.run(transport="stdio")
