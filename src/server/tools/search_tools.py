"""
JADX MCP Server - Code Search Tools

This module provides MCP tools for searching through decompiled Android code,
enabling discovery of classes, methods, and keywords across the entire APK.

Includes progress-aware search that polls the JADX plugin's /search-progress
endpoint and reports progress to the MCP client via ctx.report_progress().

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

import asyncio
import logging
from typing import Optional

from src.server.config import get_from_jadx, get_search_progress
from src.PaginationUtils import PaginationUtils

logger = logging.getLogger("jadx-mcp-server.search")


async def _poll_progress(report_progress, poll_interval: float = 2.0, max_poll_seconds: float = 630.0):
    """
    Continuously poll /search-progress and report via MCP progress notifications.
    Runs as a concurrent task alongside the actual search request.

    Args:
        report_progress: Callable(progress, total) from FastMCP Context,
                         or None if no progress reporting is available.
        poll_interval: Seconds between progress polls.
        max_poll_seconds: Safety cap — stop polling after this many seconds even
                          if the search still appears to be running.  Guards against
                          a crashed search thread leaving the tracker stuck in
                          "running" state.  Set slightly above the HTTP timeout (600s).
    """
    if report_progress is None:
        return

    last_scanned = -1
    seen_running = False
    consecutive_failures = 0
    # After we've confirmed the search is active (seen_running), a dead server
    # is a real problem.  Before that, be more tolerant — the plugin may still
    # be initialising or the search hasn't started yet.
    MAX_FAILURES_BEFORE_RUNNING = 10   # ~20 seconds of tolerance during startup
    MAX_FAILURES_AFTER_RUNNING = 3     # ~6 seconds — server died mid-search
    loop = asyncio.get_running_loop()
    poll_start = loop.time()
    try:
        while True:
            await asyncio.sleep(poll_interval)

            # Safety: abort polling if we've exceeded the time cap
            if (loop.time() - poll_start) > max_poll_seconds:
                logger.warning("Progress poller: max poll time (%.0fs) exceeded, stopping", max_poll_seconds)
                break

            progress = await get_search_progress()
            # Java sends state in lowercase: "idle", "running", "completed", "failed"
            state = progress.get("state", "unknown")

            if state == "unknown":
                # Poll failed — server may be unreachable
                consecutive_failures += 1
                threshold = MAX_FAILURES_AFTER_RUNNING if seen_running else MAX_FAILURES_BEFORE_RUNNING
                if consecutive_failures >= threshold:
                    logger.error(
                        "Progress poller: JADX plugin unreachable after %d consecutive poll failures "
                        "(seen_running=%s). Stopping progress updates. "
                        "The main search request will report its own error when it times out.",
                        consecutive_failures, seen_running,
                    )
                    break
                continue

            # Successful poll — reset failure counter
            consecutive_failures = 0

            if state == "running":
                seen_running = True
                scanned = progress.get("scanned", 0)
                total = progress.get("total", 0)
                if total > 0 and scanned != last_scanned:
                    last_scanned = scanned
                    try:
                        await report_progress(scanned, total)
                    except Exception:
                        pass  # Client may not support progress

            elif seen_running and state in ("completed", "failed"):
                # Current search finished — send final progress and stop
                scanned = progress.get("scanned", 0)
                total = progress.get("total", 0)
                if total > 0:
                    try:
                        await report_progress(scanned, total)
                    except Exception:
                        pass
                break
            # If not seen_running yet: state might be "idle", "completed", or
            # "failed" from a PREVIOUS search — keep polling until the current
            # search sets state to "running".
    except asyncio.CancelledError:
        pass


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


async def search_method_by_name(method_name: str, report_progress=None) -> dict:
    """
    Search for a method name across all classes.
    Now uses metadata-based search (no decompilation) on the Java side,
    and reports progress if a report_progress callback is provided.

    Args:
        method_name: Method name to search for (partial matching supported)
        report_progress: Optional async callable(progress, total) from FastMCP Context

    Returns:
        dict: List of all classes containing methods with matching names
    """
    # Fire search request and progress poller concurrently
    progress_task = asyncio.create_task(_poll_progress(report_progress))
    try:
        result = await get_from_jadx("search-method", {"method_name": method_name})
    finally:
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass
    return result


async def search_classes_by_keyword(
    search_term: str,
    package: str = "",
    search_in: str = "code",
    offset: int = 0,
    count: int = 20,
    report_progress=None,
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
        report_progress: Optional async callable(progress, total) from FastMCP Context

    Returns:
        dict: Paginated list of classes containing the search term, with metadata about matches
    """
    # Fire search request and progress poller concurrently
    progress_task = asyncio.create_task(_poll_progress(report_progress))
    try:
        result = await PaginationUtils.get_paginated_data(
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
    finally:
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass
    return result
