"""
JADX MCP Server - Android Resource Analysis Tools

This module provides MCP tools for analyzing Android application resources
including the AndroidManifest.xml, strings, and resource files.

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

from src.server.config import get_from_jadx
from src.PaginationUtils import PaginationUtils


async def get_android_manifest() -> dict:
    """
    Retrieve and return the AndroidManifest.xml content.

    Returns:
        dict: Parsed AndroidManifest.xml with permissions, activities, and metadata

    MCP Tool: get_android_manifest
    Description: Extracts app configuration, permissions, and component declarations
    """
    return await get_from_jadx("manifest")


async def get_strings(offset: int = 0, count: int = 0) -> dict:
    """
    Retrieve contents of strings.xml files that exist in application.

    Args:
        offset: Starting index for pagination (default: 0)
        count: Number of strings to return (0 = all, default: 0)

    Returns:
        dict: Paginated string resources from all strings.xml files

    MCP Tool: get_strings
    Description: Extracts localized string resources for analysis
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="strings",
        offset=offset,
        count=count,
        data_extractor=lambda parsed: parsed.get("strings", []),
        fetch_function=get_from_jadx
    )


async def get_all_resource_file_names(offset: int = 0, count: int = 0) -> dict:
    """
    Retrieve all resource files names that exist in application.

    Args:
        offset: Starting index for pagination (default: 0)
        count: Number of filenames to return (0 = all, default: 0)

    Returns:
        dict: Paginated list of all resource file paths in the APK

    MCP Tool: get_all_resource_file_names
    Description: Enumerates all resource files (layouts, drawables, etc.)
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="list-all-resource-files-names",
        offset=offset,
        count=count,
        data_extractor=lambda parsed: parsed.get("files", []),
        fetch_function=get_from_jadx
    )


async def get_resource_file(resource_name: str) -> dict:
    """
    Retrieve resource file content.

    Args:
        resource_name: Path to the resource file (e.g., res/layout/activity_main.xml)

    Returns:
        dict: Contents of the specified resource file

    MCP Tool: get_resource_file
    Description: Fetches content of any resource file by path
    """
    return await get_from_jadx("get-resource-file", {"file_name": resource_name})
