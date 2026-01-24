"""
JADX MCP Server - Code Search Tools

This module provides MCP tools for searching through decompiled Android code,
enabling discovery of classes, methods, and keywords across the entire APK.

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

from src.server.config import get_from_jadx
from src.PaginationUtils import PaginationUtils


async def get_method_by_name(class_name: str, method_name: str) -> dict:
    """
    Fetch the source code of a method from a specific class.

    Args:
        class_name: Fully qualified class name
        method_name: Method name (can include signature)

    Returns:
        dict: Method source code and metadata

    MCP Tool: get_method_by_name
    Description: Retrieves specific method implementation from a known class
    """
    return await get_from_jadx(
        "method-by-name", {"class_name": class_name, "method_name": method_name}
    )


async def search_method_by_name(method_name: str) -> dict:
    """
    Search for a method name across all classes.

    Args:
        method_name: Method name to search for (partial matching supported)

    Returns:
        dict: List of all classes containing methods with matching names

    MCP Tool: search_method_by_name
    Description: Finds all occurrences of a method name across the APK
    """
    return await get_from_jadx("search-method", {"method_name": method_name})


async def search_classes_by_keyword(
    search_term: str,
    package: str = "",
    search_in: str = "code",
    offset: int = 0,
    count: int = 20,
) -> dict:
    """
    Search for classes containing a specific keyword with flexible filtering options.

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
                 patterns, class names, method names, or other identifiers across the decompiled APK.

    """
    return await PaginationUtils.get_paginated_data(
        endpoint="search-classes-by-keyword",
        offset=offset,
        count=count,
        additional_params={
            "search_term": search_term,
            "package": package,
            "search_in": search_in,
        },
        data_extractor=lambda parsed: parsed.get("classes", []),
        fetch_function=get_from_jadx,
    )
