"""
JADX MCP Server - Code Refactoring Tools

This module provides MCP tools for refactoring decompiled Android code,
including renaming classes, methods, fields, and packages to improve
code readability during reverse engineering analysis.

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

from src.server import config
from src.server.config import post_to_jadx
from src.server.security import (
    first_error,
    require_refactor_enabled,
    validate_identifier,
    validate_non_negative_int,
    validate_opaque,
    validate_qualified_name,
)


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
    policy_error = require_refactor_enabled(config.REFACTOR_TOOLS_ENABLED)
    if policy_error:
        return policy_error
    validation_error = first_error(
        validate_opaque(class_name, "class_name"),
        validate_identifier(new_name, "new_name"),
    )
    if validation_error:
        return validation_error
    return await post_to_jadx("rename-class", {"class_name": class_name, "new_name": new_name})


async def rename_method(method_name: str, new_name: str, method_signature: str = None) -> dict:
    """
    Renames a specific method.

    Args:
        method_name: Current method name (can include signature)
        new_name: New name for the method
        method_signature: Optional method signature/descriptor (e.g. '(I)V') to distinguish overloads

    Returns:
        dict: Confirmation of rename operation

    MCP Tool: rename_method
    Description: Refactors method name and updates all call sites
    """
    policy_error = require_refactor_enabled(config.REFACTOR_TOOLS_ENABLED)
    if policy_error:
        return policy_error
    validation_error = first_error(
        validate_opaque(method_name, "method_name"),
        validate_identifier(new_name, "new_name"),
        validate_opaque(method_signature, "method_signature", required=False),
    )
    if validation_error:
        return validation_error
    params = {"method_name": method_name, "new_name": new_name}
    if method_signature:
        params["method_signature"] = method_signature
    return await post_to_jadx("rename-method", params)


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
    policy_error = require_refactor_enabled(config.REFACTOR_TOOLS_ENABLED)
    if policy_error:
        return policy_error
    validation_error = first_error(
        validate_opaque(class_name, "class_name"),
        validate_opaque(field_name, "field_name"),
        validate_identifier(new_name, "new_name"),
    )
    if validation_error:
        return validation_error
    return await post_to_jadx("rename-field", {
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
    policy_error = require_refactor_enabled(config.REFACTOR_TOOLS_ENABLED)
    if policy_error:
        return policy_error
    validation_error = first_error(
        validate_qualified_name(old_package_name, "old_package_name"),
        validate_qualified_name(new_package_name, "new_package_name"),
    )
    if validation_error:
        return validation_error
    return await post_to_jadx("rename-package", {
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
    policy_error = require_refactor_enabled(config.REFACTOR_TOOLS_ENABLED)
    if policy_error:
        return policy_error
    validation_error = first_error(
        validate_opaque(class_name, "class_name"),
        validate_opaque(method_name, "method_name"),
        validate_opaque(variable_name, "variable_name"),
        validate_identifier(new_name, "new_name"),
        validate_non_negative_int(reg, "reg"),
        validate_non_negative_int(ssa, "ssa"),
    )
    if validation_error:
        return validation_error
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

    return await post_to_jadx("rename-variable", params)
