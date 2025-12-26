# /// script
# requires-python = ">=3.10"
# dependencies = [ "fastmcp", "httpx", "logging", "argparse" ]
# ///

"""
Copyright (c) 2025 jadx mcp server developer(s) (https://github.com/zinja-coder/jadx-ai-mcp)
See the file 'LICENSE' for copying permission
"""

## TO DO break down code into smaller files

import httpx
import logging
import argparse
import json

from typing import Union
from fastmcp import FastMCP
#from fastmcp.server.middleware.logging import StructuredLoggingMiddleware # Comment out as not required in release build

from src.PaginationUtils import PaginationUtils
from src.banner import jadx_mcp_server_banner

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

# fastmcp logs
#mcp.add_middleware(StructuredLoggingMiddleware(include_payloads=True)) # Commented out as not required in release build

# Parse the arguments
parser = argparse.ArgumentParser("MCP Server for Jadx")
parser.add_argument("--http", help="Serve MCP Server over HTTP stream.", action="store_true", default=False)
parser.add_argument("--port", help="Specify the port number for --http to serve on. (default:8651)", default=8651, type=int)
parser.add_argument("--jadx-port", help="Specify the port on which JADX AI MCP Plugin is running on. (default:8650)", default=8650, type=int)
args = parser.parse_args()

JADX_HTTP_BASE = f"http://127.0.0.1:{args.jadx_port}" # Base URL for the JADX-AI-MCP Plugin

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
            response = resp.text
            if isinstance(response, str):
                try:
                    return json.loads(response)
                except Exception as e: # fix the `Unexpected error: Expecting value: line 1 column 1 (char 0).` error
                    response = {"response":resp.text}
            return response
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

@mcp.tool()
async def fetch_current_class() -> dict:
    """Fetch the currently selected class and its code from the JADX-GUI plugin.
    
    Returns:
        Dictionary containing currently opened class in jadx. 
    """
    return await get_from_jadx("current-class")

@mcp.tool()
async def get_selected_text() -> dict:
    """Returns the currently selected text in the decompiled code view.
    
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
    return await get_from_jadx("method-by-name", {"class_name": class_name, "method_name": method_name})

@mcp.tool()
async def get_all_classes(offset: int = 0, count: int = 0) -> dict:
    """Returns a list of all classes in the project with pagination support.
    
    Args:
        offset: Offset to start listing from (start at 0)
        count: Number of classes to return (0 means use server default)
    
    Returns:
        A dictionary containing paginated class list and metadata.
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="all-classes",
        offset=offset,
        count=count,
        data_extractor=lambda parsed: parsed.get("classes", []),
        fetch_function=get_from_jadx
    )

@mcp.tool()
async def get_class_source(class_name: str) -> dict:
    """Fetch the Java source of a specific class.
    
    Args:
        class_name: Name of the class whose source code will be returned

    Returns:
        Code of requested class as String.
    """
    return await get_from_jadx("class-source", {"class_name": class_name})

@mcp.tool()
async def search_method_by_name(method_name: str) -> dict:
    """Search for a method name across all classes.
    
    Args:
        method_name: The name of the method to search for
    
    Returns:
        A list of all classes containing the method.
    """
    return await get_from_jadx("search-method", {"method_name": method_name})

@mcp.tool()
async def get_methods_of_class(class_name: str) -> dict:
    """List all method names in a class.
    
    Args:
        class_name: The name of the class to search for

    Returns:
        A list of all methods in the class.
    """

    return await get_from_jadx("methods-of-class", {"class_name": class_name})

@mcp.tool()
async def search_classes_by_keyword(search_term:str, offset: int = 0, count: int = 20) -> dict:
    """searching for classes whose source code contains a specific keyword, 
    with pagination support for handling large result sets efficiently.
    
    Args:
        search_term: query keyword
        offset: Offset to start listing from (start at 0)
        count: Number of classes to return (default 20)
    
    Returns:
        A dictionary containing paginated class list and metadata.
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="search-classes-by-keyword",
        offset=offset,
        count=count,
        additional_params={"search_term": search_term},
        data_extractor=lambda parsed: parsed.get("classes", []),
        fetch_function=get_from_jadx
    )

@mcp.tool()
async def get_fields_of_class(class_name: str) -> dict:
    """List all field names in a class.
    
    Args:
        class_name: The name of the class to search for
    
    Returns:
        A list of all fields in the class.
    """

    return await get_from_jadx("fields-of-class", {"class_name": class_name})

@mcp.tool()
async def get_smali_of_class(class_name: str) -> dict:
    """Fetch the smali representation of a class.
    
    Args:
        class_name: Name of the class whose smali is to be returned

    Returns:
        Smali code of the requested class as String.
    """
    return await get_from_jadx("smali-of-class", {"class_name": class_name})

@mcp.tool()
async def get_android_manifest() -> dict:
    """Retrieve and return the AndroidManifest.xml content.
    
    Returns:
        Dictionary containing content of AndroidManifest.xml file.
    """
    return await get_from_jadx("manifest")

@mcp.tool()
async def get_strings(offset: int = 0, count: int = 0) -> dict:
    """Retrieve contents of strings.xml files that exists in application

    Args:
        offset: Offset to start listing from (start at 0)
        count: Number of strings to return (0 means user server default)

    Returns:
        Dictionary containing contents of strings.xml file.
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="strings",
        offset=offset,
        count=count,
        data_extractor=lambda parsed: parsed.get("strings", []),
        fetch_function=get_from_jadx
    )

@mcp.tool()
async def get_all_resource_file_names(offset: int = 0, count: int = 0) -> dict:
    """Retrieve all resource files names that exists in application

    Returns:
        List of all resource files names.
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="list-all-resource-files-names",
        offset=offset,
        count=count,
        data_extractor=lambda parsed: parsed.get("files", []),
        fetch_function=get_from_jadx
    )

@mcp.tool()
async def get_resource_file(resource_name: str) -> dict:
    """Retrieve resource file content

    Args:
        resource_name: Name of the resource file

    Returns:
        Gets the content of resource file specified in 'resource_name' parameter
    """
    return await get_from_jadx("get-resource-file", {"name": resource_name})
    
@mcp.tool()
async def get_main_application_classes_names() -> dict:
    """Fetch all the main application classes' names based on the package name defined in the AndroidManifest.xml.
    
    Args:
        None
        
    Returns:
        Dictionary containing all the main application's classes' names based on the package name defined in the AndroidManifest.xml file.
    """
    
    return await get_from_jadx("main-application-classes-names")

@mcp.tool()
async def get_main_application_classes_code(offset: int = 0, count: int = 0) -> dict:
    """Fetch main application classes' code with pagination.
    
    Args:
        offset: Offset to start listing from (start at 0)
        count: Number of classes to return (0 means use server default)

    Returns:
        Dictionary containing paginated main application classes with code.
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="main-application-classes-code",
        offset=offset,
        count=count,
        data_extractor=lambda parsed: parsed.get("classes", []),
        fetch_function=get_from_jadx
    )
    
@mcp.tool()
async def get_main_activity_class() -> dict:
    """Fetch the main activity class as defined in the AndroidManifest.xml.
    
    Returns:
        Dictionary containing content of main activity class defined in AndroidManifest.xml file.
    """
    return await get_from_jadx("main-activity")

@mcp.tool()
async def rename_class(class_name: str, new_name: str):
    """Renames a specific class.

    Args:
        class_name: The full name of the class to be renamed, including package name.
        new_name: The new name for the class.

    Returns:
        The response from the JADX server.
    """
    return await get_from_jadx("rename-class", {"class_name": class_name, "new_name": new_name})

@mcp.tool()
async def rename_method(method_name: str, new_name: str):
    """Renames a specific method.

    Args:
        method_name: The full name of the method to be renamed, including package and class name.
        new_name: The new name for the method.

    Returns:
        The response from the JADX server.
    """
    return await get_from_jadx("rename-method", {"method_name": method_name, "new_name": new_name})

@mcp.tool()
async def rename_field(class_name: str, field_name: str, new_field_name: str):
    """Renames a specific field.

    Args:
        class_name: The full class name of field
        field_name: The field to be rename.
        new_name: The new name for the field.

    Returns:
        The response from the JADX server.
    """
    return await get_from_jadx("rename-field", {"class_name": class_name, "field_name": field_name, "new_field_name": new_field_name})

@mcp.tool()
async def rename_package(old_package_name: str, new_package_name: str):
    """Renames a package and all its classes.

    Args:
        old_package_name: The current package path to be renamed (e.g., "com.abc.def")
        new_package_name: The target package path (e.g., "com.example.newpkg")

    Returns:
        The response from the JADX server with rename results.
    """
    return await get_from_jadx("rename-package", {
        "old_package_name": old_package_name, 
        "new_package_name": new_package_name
    })

@mcp.tool()
async def debug_get_stack_frames() -> dict:
    """Get current stack frames (call stack).
    
    Shows the execution path from current location back to entry point.
    Process must be suspended to use this.
    
    Returns:
        Dict with:
        - stackFrames: Array of stack frame strings showing method calls
        - count: Total number of stack frames
    """
    try:
        response = await get_from_jadx("debug/stack-frames")
        return response
    except Exception as e:
        return {"error": str(e)}
    
@mcp.tool()
async def debug_get_threads() -> dict:
    """Get all threads in the debugged process.
    
    Returns list of threads and which one is currently selected.
    
    Returns:
        Dict with:
        - threads: Array of thread names
        - selectedThread: Currently selected/active thread
        - count: Total number of threads
    """
    try:
        response = await get_from_jadx("debug/threads")
        return response
    except Exception as e:
        return {"error": str(e)}
    
@mcp.tool()
async def debug_get_variables() -> dict:
    """Get current variables when process is suspended.
    
    Returns registers (local variables) and 'this' object fields.
    Process must be suspended to use this.
    
    Returns:
        Dict with 'registers' and 'thisObject' arrays containing:
        - name: Variable/register name (e.g., 'v0', 'p1')
        - value: Current value as string
        - type: Type name (e.g., 'java.lang.String')
        - typeId: Type ID for object references
        - updated: Boolean indicating if value changed since last step
        - children: Nested fields for complex objects (recursive)
    """
    try:
        response = await get_from_jadx("debug/variables")
        return response
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_xrefs_to_class(class_name: str, offset: int = 0, count: int = 20) -> dict:
    """Find all references to a class (including constructor calls) with pagination.
    
    Args:
        class_name: The full name of the class to find references for.
        offset: Offset to start listing from (start at 0).
        count: Number of references to return (default 20).
        
    Returns:
        A dictionary containing a list of references.
        Structure:
        {
            "references": [
                {
                    "class_name": "com.example.CallerClass",
                    "method_name": "callerMethod"  # Empty string "" if reference is at class level
                },
                ...
            ],
            ... # Pagination metadata
        }
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="xrefs-to-class",
        offset=offset,
        count=count,
        additional_params={"class_name": class_name},
        data_extractor=lambda parsed: parsed.get("references", []),
        fetch_function=get_from_jadx
    )

@mcp.tool()
async def get_xrefs_to_method(class_name: str, method_name: str, offset: int = 0, count: int = 20) -> dict:
    """Find all references to a method (includes overrides) with pagination.
    
    Args:
        class_name: The full name of the class containing the method.
        method_name: The name of the method to find references for.
        offset: Offset to start listing from (start at 0).
        count: Number of references to return (default 20).
        
    Returns:
        A dictionary containing a list of references.
        Structure:
        {
            "references": [
                {
                    "class_name": "com.example.CallerClass",
                    "method_name": "callerMethod"
                },
                ...
            ],
            ... # Pagination metadata
        }
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="xrefs-to-method",
        offset=offset,
        count=count,
        additional_params={"class_name": class_name, "method_name": method_name},
        data_extractor=lambda parsed: parsed.get("references", []),
        fetch_function=get_from_jadx
    )

@mcp.tool()
async def get_xrefs_to_field(class_name: str, field_name: str, offset: int = 0, count: int = 20) -> dict:
    """Find all references to a field with pagination.
    
    Args:
        class_name: The full name of the class containing the field.
        field_name: The name of the field to find references for.
        offset: Offset to start listing from (start at 0).
        count: Number of references to return (default 20).
        
    Returns:
        A dictionary containing a list of references.
        Structure:
        {
            "references": [
                {
                    "class_name": "com.example.CallerClass",
                    "method_name": "callerMethod"
                },
                ...
            ],
            ... # Pagination metadata
        }
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="xrefs-to-field",
        offset=offset,
        count=count,
        additional_params={"class_name": class_name, "field": field_name},
        data_extractor=lambda parsed: parsed.get("references", []),
        fetch_function=get_from_jadx
    )


def main():
    try:
        print(jadx_mcp_server_banner())
    except UnicodeEncodeError:
        print("""
           [----------------------------------------------- JADX AI MCP -----------------------------------------------]
            Author         -> Jafar Pathan (zinja-coder@github)
            For Issues     -> https://github.com/zinja-coder/jadx-mcp-server
            Server Version -> v3.3.5
           """)


    print("[------------------------------ Stand By Checking JADX AI MCP Plugin Connectivity ------------------------------]")
    print("Testing health check...")
    result = health_ping()
    print(f"Final result: {result}")
    
    if args.http:
        port = args.port if args.port else 8651
        mcp.run(transport="streamable-http", port=port)
    else:
        mcp.run()

if __name__ == "__main__":
    main()
