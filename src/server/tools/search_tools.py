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


async def _poll_progress(
    report_progress,
    poll_interval: float = 2.0,
    budget_seconds: float = 600.0,
    absolute_max_seconds: float = 3600.0,
    extension_threshold: float = 0.90,
    cancel_search_event: Optional[asyncio.Event] = None,
):
    """
    Continuously poll /search-progress and report via MCP progress notifications.
    Runs as a concurrent task alongside the actual search request.

    Implements a **dynamic timeout**: starts with an initial budget (default 600s).
    When the elapsed time reaches extension_threshold (90%) of the current budget
    AND the search is still running, the poller asks the plugin for its state.
    If the plugin confirms it is still searching, the budget is extended by the
    original amount (e.g. +600s).  Extensions repeat until the search finishes
    or the absolute_max_seconds ceiling is reached.

    If cancel_search_event is provided and gets set, the poller will signal that
    the main HTTP request should be abandoned (the caller should cancel the task).

    Args:
        report_progress: Callable(progress, total) from FastMCP Context,
                         or None if no progress reporting is available.
        poll_interval: Seconds between progress polls.
        budget_seconds: Initial time budget for the search.  When ~90% consumed,
                        the poller checks status and may extend.
        absolute_max_seconds: Hard ceiling — never extend beyond this total.
        extension_threshold: Fraction (0-1) of budget at which to evaluate extension.
        cancel_search_event: If set, the poller will set() this event to signal
                             the caller to cancel the HTTP request.
    """
    if report_progress is None:
        return

    last_scanned = -1
    seen_running = False
    consecutive_failures = 0
    original_budget = budget_seconds
    current_deadline = budget_seconds
    extensions_granted = 0
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

            elapsed = loop.time() - poll_start

            # hard ceiling, no more extensions possible
            if elapsed > absolute_max_seconds:
                logger.warning(
                    "Progress poller: absolute max time (%.0fs) reached after %d extensions. Stopping.",
                    absolute_max_seconds, extensions_granted,
                )
                if cancel_search_event:
                    cancel_search_event.set()
                break

            # dynamic timeout check: approaching the current deadline?
            if elapsed >= current_deadline * extension_threshold and seen_running:
                # Ask the plugin: "Are you still searching?"
                check = await get_search_progress()
                check_state = check.get("state", "unknown")
                if check_state == "running":
                    # plugin confirms it's still working => grant extension
                    new_deadline = current_deadline + original_budget
                    if new_deadline > absolute_max_seconds:
                        new_deadline = absolute_max_seconds
                    extensions_granted += 1
                    logger.info(
                        "Progress poller: search still running at %.0fs (%.0f%% of budget). "
                        "Extending deadline by %.0fs → new deadline %.0fs (extension #%d).",
                        elapsed, (elapsed / current_deadline) * 100,
                        original_budget, new_deadline, extensions_granted,
                    )
                    try:
                        # inform the MCP client about the extension
                        scanned = check.get("scanned", 0)
                        total = check.get("total", 0)
                        if total > 0:
                            await report_progress(scanned, total)
                    except Exception:
                        pass
                    current_deadline = new_deadline
                elif check_state in ("completed", "failed"):
                    # Search ended while we were checking ,will be caught below
                    pass
                else:
                    # plugin unreachable near deadline , not safe to extend
                    logger.warning(
                        "Progress poller: budget nearly exhausted at %.0fs and plugin state "
                        "is '%s'. Not extending.",
                        elapsed, check_state,
                    )

            # Past the current deadline (after extension opportunities), give up
            if elapsed > current_deadline:
                logger.warning(
                    "Progress poller: deadline (%.0fs) exceeded with %d extensions granted. Stopping.",
                    current_deadline, extensions_granted,
                )
                if cancel_search_event:
                    cancel_search_event.set()
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
