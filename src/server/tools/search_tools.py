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
    return await get_from_jadx("method-by-name", {"class_name": class_name, "method_name": method_name})


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


async def search_classes_by_keyword(search_term: str, offset: int = 0, count: int = 20) -> dict:
    """
    Search for classes whose source code contains a specific keyword.

    Args:
        search_term: Keyword or string to search for in class source code
        offset: Starting index for pagination (default: 0)
        count: Number of results to return (default: 20)

    Returns:
        dict: Paginated list of classes containing the search term

    MCP Tool: search_classes_by_keyword
    Description: Performs full-text search across all decompiled class code
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="search-classes-by-keyword",
        offset=offset,
        count=count,
        additional_params={"search_term": search_term},
        data_extractor=lambda parsed: parsed.get("classes", []),
        fetch_function=get_from_jadx
    )
