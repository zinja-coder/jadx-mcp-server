import asyncio
import sys
import unittest
from unittest.mock import patch

from fastmcp import Client

import jadx_mcp_server


def _schema(tool):
    # fastmcp 4 renamed inputSchema to input_schema; read whichever exists.
    return getattr(tool, "input_schema", None) or tool.inputSchema


def _allows_null(schema):
    if schema.get("type") == "null":
        return True
    if isinstance(schema.get("type"), list) and "null" in schema["type"]:
        return True
    return any(_allows_null(s) for s in schema.get("anyOf", []))


class ToolSchemaTests(unittest.TestCase):
    def test_every_null_default_accepts_null(self):
        # Some agent frameworks send every optional argument, using the
        # advertised default. A parameter that defaults to null must accept it.
        async def tools():
            async with Client(jadx_mcp_server.mcp) as client:
                return await client.list_tools()

        with patch.object(sys, "argv", ["jadx_mcp_server.py"]):
            listed = asyncio.run(tools())

        bad = [
            f"{tool.name}.{name}"
            for tool in listed
            for name, prop in _schema(tool).get("properties", {}).items()
            if "default" in prop and prop["default"] is None and not _allows_null(prop)
        ]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
