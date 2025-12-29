"""
JADX MCP Server - Class Analysis Tools

This module provides MCP tools for analyzing and retrieving Android application
classes through the JADX decompilation framework. These tools enable automated
reverse engineering workflows for Android APK analysis.

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

from src.server.config import get_from_jadx
from src.PaginationUtils import PaginationUtils


async def fetch_current_class() -> dict:
    """
    Fetch the currently selected class and its code from the JADX-GUI plugin.

    Returns:
        dict: Contains class name, package, and decompiled Java source code

    MCP Tool: fetch_current_class
    Description: Retrieves the class currently open in JADX-GUI editor
    """
    return await get_from_jadx("current-class")


async def get_selected_text() -> dict:
    """
    Returns the currently selected text in the decompiled code view.

    Returns:
        dict: Contains the selected text snippet from the code editor

    MCP Tool: get_selected_text
    Description: Gets text selection from JADX-GUI for focused analysis
    """
    return await get_from_jadx("selected-text")


async def get_class_source(class_name: str) -> dict:
    """
    Fetch the Java source of a specific class.

    Args:
        class_name: Fully qualified class name (e.g., com.example.MainActivity)

    Returns:
        dict: Contains complete decompiled Java source code for the class

    MCP Tool: get_class_source
    Description: Retrieves decompiled Java source for any class in the APK
    """
    return await get_from_jadx("class-source", {"class_name": class_name})


async def get_all_classes(offset: int = 0, count: int = 0) -> dict:
    """
    Returns a list of all classes in the project with pagination support.

    Args:
        offset: Starting index for pagination (default: 0)
        count: Number of classes to return (0 = all, default: 0)

    Returns:
        dict: Paginated list of all class names in the decompiled APK

    MCP Tool: get_all_classes
    Description: Enumerates all classes with pagination for large APKs
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="all-classes",
        offset=offset,
        count=count,
        data_extractor=lambda parsed: parsed.get("classes", []),
        fetch_function=get_from_jadx
    )


async def get_methods_of_class(class_name: str) -> dict:
    """
    List all method names in a class.

    Args:
        class_name: Fully qualified class name

    Returns:
        dict: List of all method signatures in the specified class

    MCP Tool: get_methods_of_class
    Description: Extracts all method declarations from a class
    """
    return await get_from_jadx("methods-of-class", {"class_name": class_name})


async def get_fields_of_class(class_name: str) -> dict:
    """
    List all field names in a class.

    Args:
        class_name: Fully qualified class name

    Returns:
        dict: List of all field declarations in the specified class

    MCP Tool: get_fields_of_class
    Description: Extracts all field variables from a class
    """
    return await get_from_jadx("fields-of-class", {"class_name": class_name})


async def get_smali_of_class(class_name: str) -> dict:
    """
    Fetch the smali representation of a class.

    Args:
        class_name: Fully qualified class name

    Returns:
        dict: Smali/Dalvik bytecode representation of the class

    MCP Tool: get_smali_of_class
    Description: Retrieves low-level smali bytecode for advanced analysis
    """
    return await get_from_jadx("smali-of-class", {"class_name": class_name})


async def get_main_application_classes_names() -> dict:
    """
    Fetch all the main application classes' names based on the package name defined in Manifest.

    Returns:
        dict: List of class names belonging to the main application package

    MCP Tool: get_main_application_classes_names
    Description: Identifies core application classes (excludes libraries)
    """
    return await get_from_jadx("main-application-classes-names")


async def get_main_application_classes_code(offset: int = 0, count: int = 0) -> dict:
    """
    Fetch main application classes' code with pagination.

    Args:
        offset: Starting index for pagination (default: 0)
        count: Number of classes to return (0 = all, default: 0)

    Returns:
        dict: Paginated decompiled source code of main application classes

    MCP Tool: get_main_application_classes_code
    Description: Retrieves source code for core app classes with pagination
    """
    return await PaginationUtils.get_paginated_data(
        endpoint="main-application-classes-code",
        offset=offset,
        count=count,
        data_extractor=lambda parsed: parsed.get("classes", []),
        fetch_function=get_from_jadx
    )


async def get_main_activity_class() -> dict:
    """
    Fetch the main activity class as defined in the AndroidManifest.xml.

    Returns:
        dict: Main launcher activity class name and source code

    MCP Tool: get_main_activity_class
    Description: Identifies and retrieves the app's entry point activity
    """
    return await get_from_jadx("main-activity")
