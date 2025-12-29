"""
JADX MCP Server - Configuration Module

This module manages server configuration, HTTP client setup, and communication
with the JADX Java plugin. Handles connection management, error handling,
and request/response processing.

Author: Jafar Pathan (zinja-coder@github)
License: See LICENSE file
"""

import logging
import httpx
import json
import sys
from typing import Union, Dict, Any

# Default Configuration
JADX_PORT = 8650
JADX_HTTP_BASE = f"http://127.0.0.1:{JADX_PORT}"

# Logging Setup
logger = logging.getLogger("jadx-mcp-server")
logger.setLevel(logging.ERROR)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def set_jadx_port(port: int):
    """
    Updates the JADX plugin port.

    Args:
        port: TCP port number where JADX AI MCP plugin is listening

    Side Effects:
        Updates global JADX_PORT and JADX_HTTP_BASE configuration
    """
    global JADX_PORT, JADX_HTTP_BASE
    JADX_PORT = port
    JADX_HTTP_BASE = f"http://127.0.0.1:{JADX_PORT}"


def health_ping() -> Union[str, Dict[str, Any]]:
    """
    Checks if the JADX Java plugin is reachable.

    Returns:
        Union[str, Dict[str, Any]]: Success message or error dictionary

    Note:
        Performs synchronous HTTP health check with 60-second timeout
    """
    print(f"Attempting to connect to {JADX_HTTP_BASE}/health")
    try:
        with httpx.Client() as client:
            resp = client.get(f"{JADX_HTTP_BASE}/health", timeout=60)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"error": str(e)}


async def get_from_jadx(endpoint: str, params: Dict[str, Any] = {}) -> Union[str, Dict[str, Any]]:
    """
    Generic async helper to request data from the JADX plugin.

    Args:
        endpoint: API endpoint path (e.g., "class-source", "manifest")
        params: Query parameters dictionary for the request

    Returns:
        Union[str, Dict[str, Any]]: Parsed JSON response or error dictionary

    Raises:
        Returns error dict on HTTP failures or connection issues

    Note:
        Automatically handles JSON parsing with fallback to text response
    """
    url = f"{JADX_HTTP_BASE}/{endpoint.lstrip('/')}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=60)
            resp.raise_for_status()

            # Try to parse JSON, fallback to text if not valid JSON
            try:
                return resp.json()
            except json.JSONDecodeError:
                return {"response": resp.text}

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
        logger.error(error_msg)
        return {"error": error_msg}

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
