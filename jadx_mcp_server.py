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

from typing import Dict, List, Any, Optional, Union, Callable
from fastmcp import FastMCP

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

## to do separate this in it's own PaginationUtils.py file
# pagination logic 
class PaginationUtils:
    """Utility class for handling pagination across different MCP tools"""
    
    # Configuration constants
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 10000
    MAX_OFFSET = 1000000
    
    @staticmethod
    def validate_pagination_params(offset: int, count: int) -> tuple[int, int]:
        """Validate and normalize pagination parameters"""
        offset = max(0, min(offset, PaginationUtils.MAX_OFFSET))
        count = max(0, min(count, PaginationUtils.MAX_PAGE_SIZE))
        return offset, count
    
    @staticmethod
    async def get_paginated_data(
        endpoint: str, 
        offset: int = 0, 
        count: int = 0,
        additional_params: dict = None,
        data_extractor: Callable[[Any], List[Any]] = None,
        item_transformer: Callable[[Any], Any] = None
    ) -> Union[Dict[str, Any], str]:
        """
        Generic pagination handler for JADX endpoints
        
        Args:
            endpoint: The JADX endpoint to call
            offset: Starting offset
            count: Number of items to return
            additional_params: Additional query parameters
            data_extractor: Function to extract data list from response
            item_transformer: Function to transform individual items
        """
        
        # Validate parameters
        offset, count = PaginationUtils.validate_pagination_params(offset, count)
        
        # Build query parameters
        params = {"offset": offset}
        if count > 0:
            params["limit"] = count
        
        if additional_params:
            params.update(additional_params)
        
        try:
            response = await get_from_jadx(endpoint, params)
            
            if isinstance(response, dict):
                # Handle error responses
                if "error" in response:
                    return response
                return response
            
            # Parse JSON response
            try:
                parsed = json.loads(response)
                
                # Extract data using custom extractor or default behavior
                if data_extractor:
                    items = data_extractor(parsed)
                else:
                    # Default extractors for common patterns
                    items = (parsed.get("classes") or 
                            parsed.get("methods") or 
                            parsed.get("fields") or 
                            parsed.get("items", []))
                
                # Transform items if transformer provided
                if item_transformer and items:
                    items = [item_transformer(item) for item in items]
                
                # Build standardized response
                return PaginationUtils._build_standardized_response(parsed, items)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response from JADX: {e}")
                return {"error": f"Invalid JSON response from JADX server: {str(e)}"}
                
        except Exception as e:
            logger.error(f"Error in paginated request to {endpoint}: {e}")
            return {"error": f"Failed to fetch data from {endpoint}: {str(e)}"}
    
    @staticmethod
    def _build_standardized_response(parsed_response: dict, items: List[Any]) -> dict:
        """Build standardized pagination response"""
        
        pagination_info = parsed_response.get("pagination", {})
        
        result = {
            "type": parsed_response.get("type", "paginated-list"),
            "items": items,
            "pagination": {
                "total": pagination_info.get("total", len(items)),
                "offset": pagination_info.get("offset", 0),
                "limit": pagination_info.get("limit", 0),
                "count": pagination_info.get("count", len(items)),
                "has_more": pagination_info.get("has_more", False)
            }
        }
        
        # Add navigation helpers if available
        if "next_offset" in pagination_info:
            result["pagination"]["next_offset"] = pagination_info["next_offset"]
        if "prev_offset" in pagination_info:
            result["pagination"]["prev_offset"] = pagination_info["prev_offset"]
        if "current_page" in pagination_info:
            result["pagination"]["current_page"] = pagination_info["current_page"]
            result["pagination"]["total_pages"] = pagination_info.get("total_pages", 1)
            result["pagination"]["page_size"] = pagination_info.get("page_size", 0)
        
        return result
    
    @staticmethod
    def create_page_based_tool(base_func: Callable) -> Callable:
        """Decorator to create page-based versions of offset-based functions"""
        async def page_wrapper(page: int = 1, page_size: int = DEFAULT_PAGE_SIZE, **kwargs) -> dict:
            page = max(1, page)
            page_size = max(1, min(page_size, PaginationUtils.MAX_PAGE_SIZE))
            offset = (page - 1) * page_size
            
            return await base_func(offset=offset, count=page_size, **kwargs)
        
        return page_wrapper

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

@mcp.tool()
async def fetch_current_class() -> dict:
    """Fetch the currently selected class and its code from the JADX-GUI plugin.
    
    Returns:
        Dictionary containing currently opened class in jadx. 
    """
    return await get_from_jadx("current-class")

@mcp.tool()
async def get_selected_text() -> str:
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
    return await get_from_jadx("method-by-name", {"class": class_name, "method": method_name})

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
        data_extractor=lambda parsed: parsed.get("classes", [])
    )

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
async def search_method_by_name(method_name: str) -> List[str]:
    """Search for a method name across all classes.
    
    Args:
        method_name: The name of the method to search for
    
    Returns:
        A list of all classes containing the method.
    """
    
    response = await get_from_jadx("search-method", {"method": method_name})
    all_matches = response.splitlines() if response else []
    
    return all_matches

@mcp.tool()
async def get_methods_of_class(class_name: str) -> List[str]:
    """List all method names in a class.
    
    Args:
        class_name: The name of the class to search for

    Returns:
        A list of all methods in the class.
    """

    response = await get_from_jadx("methods-of-class", {"class": class_name})
    all_methods = response.splitlines() if response else []

    return all_methods

@mcp.tool()
async def get_fields_of_class(class_name: str) -> List[str]:
    """List all field names in a class.
    
    Args:
        class_name: The name of the class to search for
    
    Returns:
        A list of all fields in the class.
    """

    response = await get_from_jadx("fields-of-class", {"class": class_name})
    all_fields = response.splitlines() if response else []

    return all_fields

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
    
    Returns:
        Dictionary containing content of AndroidManifest.xml file.
    """
    manifest = await get_from_jadx("manifest")
    if isinstance(manifest, str):
        return json.loads(manifest)
    return manifest

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
        data_extractor=lambda parsed: parsed.get("strings", [])
    )

@mcp.tool()
async def get_all_resource_file_names() -> dict:
    """Retrieve all resource files names that exists in application

    Returns:
        List of all resource files names.
    """
    return await get_from_jadx("list-all-resource-files-names")

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
async def get_main_application_classes_names() -> List[str]:
    """Fetch all the main application classes' names based on the package name defined in the AndroidManifest.xml.
    
    Args:
        None
        
    Returns:
        Dictionary containing all the main application's classes' names based on the package name defined in the AndroidManifest.xml file.
    """
    
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
    
    return class_names

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
        data_extractor=lambda parsed: parsed.get("allClassesInPackage", [])
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
    return await get_from_jadx("rename-class", {"class": class_name, "newName": new_name})

@mcp.tool()
async def rename_method(method_name: str, new_name: str):
    """Renames a specific method.

    Args:
        method_name: The full name of the method to be renamed, including package and class name.
        new_name: The new name for the method.

    Returns:
        The response from the JADX server.
    """
    return await get_from_jadx("rename-method", {"method": method_name, "newName": new_name})

@mcp.tool()
async def rename_field(class_name: str, field_name: str, new_name: str):
    """Renames a specific field.

    Args:
        class_name: The full class name of field
        field_name: The field to be rename.
        new_name: The new name for the field.

    Returns:
        The response from the JADX server.
    """
    return await get_from_jadx("rename-field", {"class": class_name, "field": field_name, "newFieldName": new_name})

def main():
    print("JADX MCP SERVER\n - By ZinjaCoder (https://github.com/zinja-coder) \n - To Report Issues: https://github.com/zinja-coder/jadx-mcp-server/issues\n")
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
