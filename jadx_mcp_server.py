#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [ "fastmcp", "httpx" ]
# ///

"""
Copyright (c) 2025 jadx mcp server developer(s) (https://github.com/zinja-coder/jadx-ai-mcp)
See the file 'LICENSE' for copying permission
"""

import argparse
import sys
from fastmcp import FastMCP
from src.banner import jadx_mcp_server_banner
from src.server import config, tools

# Initialize MCP Server
mcp = FastMCP("JADX-AI-MCP Plugin Reverse Engineering Server")

# Import and register ALL tools using correct FastMCP pattern
from src.server.tools.class_tools import (
    fetch_current_class, get_selected_text, get_class_source,
    get_all_classes, get_methods_of_class, get_fields_of_class, get_smali_of_class,
    get_main_application_classes_names, get_main_application_classes_code, get_main_activity_class
)
from src.server.tools.search_tools import (
    get_method_by_name, search_method_by_name, search_classes_by_keyword
)
from src.server.tools.resource_tools import (
    get_android_manifest, get_strings, get_all_resource_file_names,
    get_resource_file
)
from src.server.tools.refactor_tools import (
    rename_class, rename_method, rename_field, rename_package, rename_variable, add_comment
)
from src.server.tools.debug_tools import (
    debug_get_stack_frames, debug_get_threads, debug_get_variables
)
from src.server.tools.xrefs_tools import (
    get_xrefs_to_class, get_xrefs_to_method, get_xrefs_to_field
)


# CORRECT REGISTRATION PATTERN for FastMCP
@mcp.tool()
async def fetch_current_class() -> dict:
    """Fetch the currently selected class and its code from the JADX-GUI plugin."""
    return await tools.class_tools.fetch_current_class()


@mcp.tool()
async def get_selected_text() -> dict:
    """Returns the currently selected text in the decompiled code view."""
    return await tools.class_tools.get_selected_text()


@mcp.tool()
async def get_method_by_name(class_name: str, method_name: str) -> dict:
    """Fetch the source code of a method from a specific class."""
    return await tools.search_tools.get_method_by_name(class_name, method_name)


@mcp.tool()
async def get_all_classes(offset: int = 0, count: int = 0) -> dict:
    """Returns a list of all classes in the project with pagination support."""
    return await tools.class_tools.get_all_classes(offset, count)


@mcp.tool()
async def get_class_source(class_name: str) -> dict:
    """Fetch the Java source of a specific class."""
    return await tools.class_tools.get_class_source(class_name)


@mcp.tool()
async def search_method_by_name(method_name: str) -> dict:
    """Search for a method name across all classes."""
    return await tools.search_tools.search_method_by_name(method_name)


@mcp.tool()
async def get_methods_of_class(class_name: str) -> dict:
    """List all method names in a class."""
    return await tools.class_tools.get_methods_of_class(class_name)


@mcp.tool()
async def search_classes_by_keyword(
    search_term: str,
    package: str = "",
    search_in: str = "code",
    offset: int = 0,
    count: int = 20,
) -> dict:
    """Search for classes containing a specific keyword with flexible filtering options.

    This tool performs a comprehensive search across decompiled Android code, allowing you to:
    1. Search within specific packages by providing a package name
    2. Target specific search scopes (class names, method names, fields, code content, comments)
    3. Combine multiple search scopes for precise results

    Args:
        search_term: The keyword or string to search for. This is the main search query.

        package (optional): Package name to limit the search scope.
            - If empty string (default), searches across all packages in the APK
            - If provided, only searches within classes belonging to the specified package
            - Example: "com.example.app" to search only in that package

        search_in (optional): Comma-separated list of search scopes to target.
            Valid values:
            - "class": Search in class names only
            - "method": Search in method names only
            - "field": Search in field names only
            - "code": Search in code content (method bodies, statements, etc.)
            - "comment": Search in comments

            You can specify one or multiple scopes:
            - Single scope: "class" (only class names)
            - Multiple scopes: "class,method" (class names OR method names)
            - Combined: "class,method,code" (searches in all three scopes)

            Default: "code" (searches in code content)

        offset (optional): Starting index for pagination. Default: 0
        count (optional): Maximum number of results to return. Default: 20

    Returns:
        dict: Paginated list of classes containing the search term, with metadata about matches

    MCP Tool: search_classes_by_keyword
    Description: Advanced search tool that finds classes matching a keyword with package filtering
                 and scope targeting capabilities. Use this when you need to find specific code
                 patterns, class names, method names, or other identifiers across the decompiled APK."""
    return await tools.search_tools.search_classes_by_keyword(
        search_term, package, search_in, offset, count
    )


@mcp.tool()
async def get_fields_of_class(class_name: str) -> dict:
    """List all field names in a class."""
    return await tools.class_tools.get_fields_of_class(class_name)


@mcp.tool()
async def get_smali_of_class(class_name: str) -> dict:
    """Fetch the smali representation of a class."""
    return await tools.class_tools.get_smali_of_class(class_name)


@mcp.tool()
async def get_android_manifest() -> dict:
    """Retrieve and return the AndroidManifest.xml content."""
    return await tools.resource_tools.get_android_manifest()


@mcp.tool()
async def get_strings(offset: int = 0, count: int = 0) -> dict:
    """Retrieve contents of strings.xml files."""
    return await tools.resource_tools.get_strings(offset, count)


@mcp.tool()
async def get_all_resource_file_names(offset: int = 0, count: int = 0) -> dict:
    """Retrieve all resource files names."""
    return await tools.resource_tools.get_all_resource_file_names(offset, count)


@mcp.tool()
async def get_resource_file(resource_name: str) -> dict:
    """Retrieve resource file content."""
    return await tools.resource_tools.get_resource_file(resource_name)


@mcp.tool()
async def get_main_application_classes_names() -> dict:
    """Fetch main application classes' names from Manifest package."""
    return await tools.class_tools.get_main_application_classes_names()


@mcp.tool()
async def get_main_application_classes_code(offset: int = 0, count: int = 0) -> dict:
    """Fetch main application classes' code with pagination."""
    return await tools.class_tools.get_main_application_classes_code(offset, count)


@mcp.tool()
async def get_main_activity_class() -> dict:
    """Fetch the main activity class from AndroidManifest.xml."""
    return await tools.class_tools.get_main_activity_class()


@mcp.tool()
async def rename_class(class_name: str, new_name: str) -> dict:
    """Renames a specific class."""
    return await tools.refactor_tools.rename_class(class_name, new_name)


@mcp.tool()
async def rename_method(method_name: str, new_name: str) -> dict:
    """Renames a specific method."""
    return await tools.refactor_tools.rename_method(method_name, new_name)


@mcp.tool()
async def rename_field(class_name: str, field_name: str, new_name: str) -> dict:
    """Renames a specific field."""
    return await tools.refactor_tools.rename_field(class_name, field_name, new_name)


@mcp.tool()
async def rename_package(old_package_name: str, new_package_name: str) -> dict:
    """Renames a package and all its classes."""
    return await tools.refactor_tools.rename_package(old_package_name, new_package_name)


@mcp.tool()
async def rename_variable(class_name: str, method_name: str, variable_name: str, new_name: str, reg: str = None, ssa: str = None) -> dict:
    """Renames a specific variable in a method."""
    return await tools.refactor_tools.rename_variable(class_name, method_name, variable_name, new_name, reg, ssa)


@mcp.tool()
async def add_comment(target_type: str, class_name: str, comment: str, method_name: str = None, field_name: str = None, style: str = "LINE") -> dict:
    """Adds a comment to a class, method, or field in the decompiled code with customizable comment style."""
    return await tools.refactor_tools.add_comment(target_type, class_name, comment, method_name, field_name, style)


@mcp.tool()
async def debug_get_stack_frames() -> dict:
    """Get current stack frames (call stack)."""
    return await tools.debug_tools.debug_get_stack_frames()


@mcp.tool()
async def debug_get_threads() -> dict:
    """Get all threads in the debugged process."""
    return await tools.debug_tools.debug_get_threads()


@mcp.tool()
async def debug_get_variables() -> dict:
    """Get current variables when process is suspended."""
    return await tools.debug_tools.debug_get_variables()


@mcp.tool()
async def get_xrefs_to_class(class_name: str, offset: int = 0, count: int = 20) -> dict:
    """Find all references to a class."""
    return await tools.xrefs_tools.get_xrefs_to_class(class_name, offset, count)


@mcp.tool()
async def get_xrefs_to_method(
    class_name: str, method_name: str, offset: int = 0, count: int = 20
) -> dict:
    """Find all references to a method."""
    return await tools.xrefs_tools.get_xrefs_to_method(
        class_name, method_name, offset, count
    )


@mcp.tool()
async def get_xrefs_to_field(
    class_name: str, field_name: str, offset: int = 0, count: int = 20
) -> dict:
    """Find all references to a field."""
    return await tools.xrefs_tools.get_xrefs_to_field(
        class_name, field_name, offset, count
    )


def main():
    parser = argparse.ArgumentParser("MCP Server for Jadx")
    parser.add_argument(
        "--http",
        help="Serve MCP Server over HTTP stream.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--port", help="Port for --http (default:8651)", default=8651, type=int
    )
    parser.add_argument(
        "--jadx-port",
        help="JADX AI MCP Plugin port (default:8650)",
        default=8650,
        type=int,
    )
    args = parser.parse_args()

    # Configure
    config.set_jadx_port(args.jadx_port)

    # Banner & Health Check
    try:
        print(jadx_mcp_server_banner())
    except:
        print(
            "[JADX AI MCP Server] v3.3.5 | MCP Port:",
            args.port,
            "| JADX Port:",
            args.jadx_port,
        )

    print("Testing JADX AI MCP Plugin connectivity...")
    result = config.health_ping()
    print(f"Health check result: {result}")

    # Run Server
    if args.http:
        mcp.run(transport="streamable-http", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
