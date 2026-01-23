"""
JADX MCP Server - Code Refactoring Tools

This module provides MCP tools for refactoring decompiled Android code,
including renaming classes, methods, fields, and packages to improve
code readability during reverse engineering analysis.

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

from src.server.config import get_from_jadx


async def rename_class(class_name: str, new_name: str) -> dict:
    """
    Renames a specific class.

    Args:
        class_name: Fully qualified current class name
        new_name: New name for the class (without package)

    Returns:
        dict: Confirmation of rename operation

    MCP Tool: rename_class
    Description: Refactors class name across the entire decompiled codebase
    """
    return await get_from_jadx("rename-class", {"class_name": class_name, "new_name": new_name})


async def rename_method(method_name: str, new_name: str) -> dict:
    """
    Renames a specific method.

    Args:
        method_name: Current method name (can include signature)
        new_name: New name for the method

    Returns:
        dict: Confirmation of rename operation

    MCP Tool: rename_method
    Description: Refactors method name and updates all call sites
    """
    return await get_from_jadx("rename-method", {"method_name": method_name, "new_name": new_name})


async def rename_field(class_name: str, field_name: str, new_name: str) -> dict:
    """
    Renames a specific field.

    Args:
        class_name: Fully qualified class name containing the field
        field_name: Current field name
        new_name: New name for the field

    Returns:
        dict: Confirmation of rename operation

    MCP Tool: rename_field
    Description: Refactors field name and updates all references
    """
    return await get_from_jadx("rename-field", {
        "class_name": class_name,
        "field_name": field_name,
        "new_field_name": new_name
    })


async def rename_package(old_package_name: str, new_package_name: str) -> dict:
    """
    Renames a package and all its classes.

    Args:
        old_package_name: Current package name (e.g., com.example.old)
        new_package_name: New package name (e.g., com.example.new)

    Returns:
        dict: Confirmation of rename operation

    MCP Tool: rename_package
    Description: Refactors entire package structure and class namespaces
    """
    return await get_from_jadx("rename-package", {
        "old_package_name": old_package_name,
        "new_package_name": new_package_name
    })


async def rename_variable(class_name: str, method_name: str, variable_name: str, new_name: str, reg: str = None, ssa: str = None) -> dict:
    """
    Renames a specific variable in a method.

    Args:
        class_name: Fully qualified class name
        method_name: Name of the method containing the variable
        variable_name: Current variable name
        new_name: New name for the variable
        reg (optional): Register number to target matching variable (e.g. "3")
        ssa (optional): SSA version to target matching variable (e.g. "1")

    Returns:
        dict: Confirmation of rename operation

    MCP Tool: rename_variable
    Description: Refactors variable name within a method
    """
    params = {
        "class_name": class_name,
        "method_name": method_name,
        "variable_name": variable_name,
        "new_name": new_name
    }
    if reg:
        params["reg"] = reg
    if ssa:
        params["ssa"] = ssa

    return await get_from_jadx("rename-variable", params)


async def add_comment(target_type: str, class_name: str, comment: str, method_name: str = None, field_name: str = None, style: str = "LINE") -> dict:
    """
    Adds a comment to a class, method, or field in the decompiled code.

    Args:
        target_type: Type of target ("class", "method", or "field")
        class_name: Fully qualified class name
        comment: The comment text to add
        method_name (optional): Method name (required for method comments, can include full signature for overloaded methods)
        field_name (optional): Field name (required for field comments)
        style (optional): Comment style (default: "LINE")
            - "LINE": Single-line comment (// comment)
            - "BLOCK": Multi-line block comment (/* comment */)
            - "BLOCK_CONDENSED": Condensed block comment (/* comment */)
            - "JAVADOC": Javadoc style (/** comment */)
            - "JAVADOC_CONDENSED": Condensed Javadoc (/** comment */)

    Returns:
        dict: Confirmation of comment addition with style information

    MCP Tool: add_comment
    Description: Adds explanatory comments to decompiled code elements (classes, methods, or fields) with customizable comment styles
    
    Examples:
        # Add single-line comment to a class (default style)
        add_comment("class", "com.example.MyClass", "This class handles user authentication")
        
        # Add block comment to a method
        add_comment("method", "com.example.MyClass", "Validates user credentials\\nChecks password hash\\nReturns auth token", 
                   method_name="validateUser", style="BLOCK")
        
        # Add Javadoc to overloaded method
        add_comment("method", "com.example.MyClass", "Validates user with email\\n@param email User email\\n@return true if valid", 
                   method_name="com.example.MyClass.validateUser(java.lang.String):boolean",
                   style="JAVADOC")
        
        # Add comment to a field
        add_comment("field", "com.example.MyClass", "User session token", field_name="sessionToken", style="LINE")
    """
    params = {
        "target_type": target_type,
        "class_name": class_name,
        "comment": comment,
        "style": style
    }
    
    if method_name:
        params["method_name"] = method_name
    if field_name:
        params["field_name"] = field_name

    return await get_from_jadx("add-comment", params)
