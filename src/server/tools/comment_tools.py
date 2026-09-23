"""
JADX MCP Server - Code Commenting Tools

This module provides MCP tools for annotating decompiled Android code with
comments. Comments are stored in the JADX project code data, exactly like the
ones added through the JADX-GUI "Add comment" dialog, so they show up in the
decompiled view and are saved with the .jadx project file.

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

from src.server.config import get_from_jadx


async def add_comment(
    class_name: str,
    comment: str,
    method_name: str = None,
    method_signature: str = None,
    field_name: str = None,
    line: int = None,
    style: str = "LINE",
) -> dict:
    """
    Adds, updates or removes a comment on a class, method, field or single code line.

    Args:
        class_name: Fully qualified class name of the comment target
        comment: Comment text. Pass an empty string to remove an existing comment
        method_name: Optional method name to comment a method instead of the class
        method_signature: Optional method signature/descriptor (e.g. '(I)V') to distinguish overloads
        field_name: Optional field name to comment a field instead of the class
        line: Optional 1-based line number in the decompiled source of the class.
              The comment is appended to that line; on a class, method or field
              declaration line it comments that declaration instead, the same way the
              comment shortcut behaves in JADX-GUI. Use
              get_class_source(with_line_numbers=True) to pick a line
        style: Comment style - LINE, BLOCK, BLOCK_CONDENSED, JAVADOC or JAVADOC_CONDENSED (default: LINE)

    Returns:
        dict: Confirmation of the comment operation, including whether the comment
              was added, updated or removed, the line used and what it attached to,
              and 'rendered' plus 'rendered_at_line': the decompiled line the comment
              actually shows up on. A write that does not render is rolled back and
              returns an error instead, so a success response means the comment is
              really in the code

    MCP Tool: add_comment
    Description: Annotates decompiled code with a comment shown in JADX-GUI.
                 A second comment on the same target replaces the previous one.
    """
    params = {"class_name": class_name, "comment": comment, "style": style}
    if method_name:
        params["method_name"] = method_name
    if method_signature:
        params["method_signature"] = method_signature
    if field_name:
        params["field_name"] = field_name
    if line is not None:
        params["line"] = line

    return await get_from_jadx("add-comment", params)


async def list_comments(class_name: str = "") -> dict:
    """
    Lists the comments stored in the current project.

    Args:
        class_name: Optional fully qualified class name to only list comments
                    declared in that class (default: all comments)

    Returns:
        dict: List of comments with their target class, node type, node id,
              comment text and style

    MCP Tool: list_comments
    Description: Reads back previously added comments, useful to check what has
                 already been annotated before writing new comments
    """
    params = {}
    if class_name:
        params["class_name"] = class_name
    return await get_from_jadx("list-comments", params)
