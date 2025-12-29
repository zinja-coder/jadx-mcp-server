"""
JADX MCP Server - Pagination Utilities

This module provides a reusable pagination framework for handling large datasets
from JADX API endpoints. Ensures consistent pagination behavior across all tools
with validation, error handling, and standardized response formatting.

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

import json
import logging
from typing import Dict, List, Any, Union, Callable

# Set up logging configuration
logger = logging.getLogger()
logger.setLevel(logging.ERROR)

# Console handler for logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)


class PaginationUtils:
    """
    Utility class for handling pagination across different MCP tools.

    Provides consistent pagination behavior with validation, error handling,
    and standardized response formatting for all JADX API endpoints.
    """

    # Configuration constants
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 10000
    MAX_OFFSET = 1000000

    @staticmethod
    def validate_pagination_params(offset: int, count: int) -> tuple[int, int]:
        """
        Validate and normalize pagination parameters.

        Args:
            offset: Requested starting offset (can be negative or excessive)
            count: Requested item count (can be negative or excessive)

        Returns:
            tuple[int, int]: Validated (offset, count) within safe bounds

        Note:
            Clamps values to [0, MAX_OFFSET] and [0, MAX_PAGE_SIZE]
        """
        offset = max(0, min(offset, PaginationUtils.MAX_OFFSET))
        count = max(0, min(count, PaginationUtils.MAX_PAGE_SIZE))
        return offset, count

    @staticmethod
    async def get_paginated_data(
        endpoint: str,
        offset: int = 0,
        count: int = 0,
        additional_params: dict = None,
        data_extractor: Callable[[Any], List[Any]] = None,
        item_transformer: Callable[[Any], Any] = None,
        fetch_function: Callable = None
    ) -> Union[Dict[str, Any], str]:
        """
        Generic pagination handler for JADX endpoints.

        Args:
            endpoint: The JADX API endpoint to call
            offset: Starting offset for pagination (default: 0)
            count: Number of items to return (default: 0 = all)
            additional_params: Additional query parameters for the endpoint
            data_extractor: Function to extract data list from API response
            item_transformer: Optional function to transform individual items
            fetch_function: Async function to fetch data (typically get_from_jadx)

        Returns:
            Union[Dict[str, Any], str]: Standardized paginated response with metadata

        Response Format:
            {
                "type": "paginated-list",
                "items": [...],
                "pagination": {
                    "total": int,
                    "offset": int,
                    "limit": int,
                    "count": int,
                    "has_more": bool
                }
            }

        Raises:
            Returns error dict on failures with descriptive error messages
        """
        # Validate parameters
        offset, count = PaginationUtils.validate_pagination_params(offset, count)

        # Build query parameters
        params = {"offset": offset}
        if count > 0:
            params["limit"] = count
        if additional_params:
            params.update(additional_params)

        try:
            # Use the passed fetch_function which is actually fetch_from_jadx
            if fetch_function is None:
                raise ValueError("fetch_function must be provided")

            response = await fetch_function(endpoint, params)

            # Parse JSON response
            try:
                # Extract data using custom extractor or default behavior
                if data_extractor:
                    items = data_extractor(response)
                else:
                    # Default extractors for common patterns
                    items = (response.get("classes") or
                            response.get("methods") or
                            response.get("fields") or
                            response.get("items", []))

                # Transform items if transformer provided
                if item_transformer and items:
                    items = [item_transformer(item) for item in items]

                # Build standardized response
                return PaginationUtils._build_standardized_response(response, items)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response from JADX: {e}")
                return {"error": f"Invalid JSON response from JADX server: {str(e)}"}

        except Exception as e:
            logger.error(f"Error in paginated request to {endpoint}: {e}")
            return {"error": f"Failed to fetch data from {endpoint}: {str(e)}"}

    @staticmethod
    def _build_standardized_response(parsed_response: dict, items: List[Any]) -> dict:
        """
        Build standardized pagination response.

        Args:
            parsed_response: Raw API response from JADX
            items: Extracted and transformed items list

        Returns:
            dict: Standardized response with pagination metadata

        Note:
            Includes navigation helpers (next_offset, prev_offset, current_page)
            if available in the API response
        """
        pagination_info = parsed_response.get("pagination", {})

        result = {
            "type": parsed_response.get("type", "paginated-list"),
            "items": items,
            "pagination": {
                "total": pagination_info.get("total", len(items)),
                "offset": pagination_info.get("offset", 0),
                "limit": pagination_info.get("limit", 0),
                "count": pagination_info.get("count", len(items)),
                "has_more": pagination_info.get("has_more", False)
            }
        }

        # Add navigation helpers if available
        if "next_offset" in pagination_info:
            result["pagination"]["next_offset"] = pagination_info["next_offset"]
        if "prev_offset" in pagination_info:
            result["pagination"]["prev_offset"] = pagination_info["prev_offset"]
        if "current_page" in pagination_info:
            result["pagination"]["current_page"] = pagination_info["current_page"]
            result["pagination"]["total_pages"] = pagination_info.get("total_pages", 1)
            result["pagination"]["page_size"] = pagination_info.get("page_size", 0)

        return result

    @staticmethod
    def create_page_based_tool(base_func: Callable) -> Callable:
        """
        Decorator to create page-based versions of offset-based functions.

        Args:
            base_func: Async function that uses offset-based pagination

        Returns:
            Callable: Wrapped function that accepts page numbers instead

        Example:
            @create_page_based_tool
            async def get_classes_by_page(page=1, page_size=100):
                # Automatically converts to offset-based call
                pass
        """
        async def page_wrapper(page: int = 1, page_size: int = PaginationUtils.DEFAULT_PAGE_SIZE, **kwargs) -> dict:
            page = max(1, page)
            page_size = max(1, min(page_size, PaginationUtils.MAX_PAGE_SIZE))
            offset = (page - 1) * page_size
            return await base_func(offset=offset, count=page_size, **kwargs)

        return page_wrapper
