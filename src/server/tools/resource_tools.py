"""
JADX MCP Server - Android Resource Analysis Tools

This module provides MCP tools for analyzing Android application resources
including the AndroidManifest.xml, strings, and resource files.

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

from src.server.config import get_from_jadx
from src.PaginationUtils import PaginationUtils
import xml.etree.ElementTree as ET
from typing import Dict, List


async def get_android_manifest() -> dict:
    """
    Retrieve and return the AndroidManifest.xml content.

    Returns:
        dict: Parsed AndroidManifest.xml with permissions, activities, and metadata

    MCP Tool: get_android_manifest
    Description: Extracts app configuration, permissions, and component declarations
    """
    return await get_from_jadx("manifest")


async def get_manifest_component(component_type: str, only_exported: bool = False) -> dict:
    """
    Retrieve specified component data from AndroidManifest.xml, support filter exported components.
    Support standard Android components: activity, provider, service, receiver.

    Args:
        component_type: Exact type of component to fetch (activity/provider/service/receiver)
        only_exported: Whether to return only exported components, default False

    Returns:
        dict: All data for the specified component type in manifest

    MCP Tool: get_manifest_component
    Description: Extracts specific component data (activity/provider/service/receiver) from AndroidManifest.xml
    """
    manifest_data = await get_android_manifest()
    manifest_xml = manifest_data.get("content", "")
    if not manifest_xml:
        return {"error": "AndroidManifest.xml content is empty, no data to parse"}

    supported_types = {"activity", "provider", "service", "receiver"}
    ALIAS_MAP = {"activity": ["activity-alias"]}
    if component_type not in supported_types:
        return {
            "error": f"Unsupported component type: {component_type}, exact match required",
            "supported_types": list(supported_types)
        }

    try:
        ET.register_namespace("android", "http://schemas.android.com/apk/res/android")
        root = ET.fromstring(manifest_xml)
        component_xml_list: List[str] = []
        target_tags = [component_type] + ALIAS_MAP.get(component_type, [])
        for tag in target_tags:
            for component_elem in root.iter(tag):
                component_xml = ET.tostring(component_elem, encoding="utf-8", short_empty_elements=True).decode("utf-8")
                component_xml = component_xml.replace('xmlns:android="http://schemas.android.com/apk/res/android"', '')
                if not only_exported:
                    component_xml_list.append(component_xml)
                    continue
                exported_attr = component_elem.attrib.get("{http://schemas.android.com/apk/res/android}exported", "").lower()
                is_exported = exported_attr != "false" and len(component_elem.findall(".//intent-filter")) > 0
                if is_exported:
                    component_xml_list.append(component_xml)
        return {
            "component_type": component_type,
            "only_exported": only_exported,
            "count": len(component_xml_list),
            "components": component_xml_list
        }

    except ET.ParseError as e:
        return {"error": f"AndroidManifest.xml parse failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error when fetching component: {str(e)}"}


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
