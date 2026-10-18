"""
End-to-end tests for the slim flag: MCP client -> registered tool -> slimming.

`get_class_source(with_line_numbers=True)` prints the line numbers that the
plugin's add_comment(line=N) resolves against the same decompiled string, split
on newlines. A slimming pass that moved a line would silently retarget comments,
so the numbering is asserted here through the real tool call path.
"""

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastmcp import Client

import jadx_mcp_server
from src.server.tools import class_tools, search_tools

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "jadx_kotlin_class_real.java"
DECLARATION = "public final /* data */ class Pair<A, B>"


def _line_of(text: str, needle: str) -> int:
    for number, line in enumerate(text.split("\n"), start=1):
        if needle in line:
            return number
    raise AssertionError(f"{needle!r} not found")


def _line_number_from_numbered(numbered: str, needle: str) -> int:
    """Read the 1-based number printed in front of the line holding `needle`."""
    for line in numbered.split("\n"):
        prefix, separator, body = line.partition("| ")
        if separator and needle in body:
            return int(prefix.strip())
    raise AssertionError(f"{needle!r} not found in numbered source")


def _text(result) -> str:
    parts = [getattr(block, "text", "") for block in result.content]
    return "\n".join(part for part in parts if part)


class NumberingContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.raw = FIXTURE.read_text(encoding="utf-8")
        self.assertTrue(any("class Pair<A, B>" in line for line in self.raw.split("\n")))

    async def test_slimmed_numbered_source_keeps_the_plugin_line_numbers(self):
        with patch.object(class_tools, "get_from_jadx", AsyncMock(return_value={"response": self.raw})):
            result = await class_tools.get_class_source("kotlin.Pair", with_line_numbers=True)

        numbered = result["response"]
        self.assertNotIn("@Metadata(", numbered)
        self.assertEqual(
            _line_number_from_numbered(numbered, DECLARATION),
            _line_of(self.raw, DECLARATION),
        )
        self.assertEqual(numbered.count("\n"), self.raw.count("\n"))

    async def test_slim_false_returns_the_raw_dump(self):
        with patch.object(class_tools, "get_from_jadx", AsyncMock(return_value={"response": self.raw})):
            result = await class_tools.get_class_source("kotlin.Pair", slim=False)

        self.assertEqual(result["response"], self.raw)
        self.assertIn("@Metadata(", result["response"])

    async def test_method_source_is_slimmed(self):
        payload = {"class_name": "kotlin.Pair", "method_name": "toString", "code": self.raw}
        with patch.object(search_tools, "get_from_jadx", AsyncMock(return_value=payload)):
            result = await search_tools.get_method_by_name("kotlin.Pair", "toString")

        self.assertNotIn("@Metadata(", result["code"])
        self.assertEqual(result["method_name"], "toString")
        self.assertEqual(result["code"].count("\n"), self.raw.count("\n"))


class McpWiringTests(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_text(encoding="utf-8")

    def _call(self, name, arguments):
        async def run():
            with patch.object(class_tools, "get_from_jadx", AsyncMock(return_value={"response": self.raw})):
                async with Client(jadx_mcp_server.mcp) as client:
                    return await client.call_tool(name, arguments)

        with patch.object(sys, "argv", ["jadx_mcp_server.py"]):
            return asyncio.run(run())

    def test_slim_defaults_on_through_the_registered_tool(self):
        text = _text(self._call("get_class_source", {"class_name": "kotlin.Pair"}))
        self.assertNotIn("@Metadata(", text)
        self.assertIn("class Pair", text)

    def test_slim_false_is_forwarded_through_the_registered_tool(self):
        text = _text(self._call("get_class_source", {"class_name": "kotlin.Pair", "slim": False}))
        self.assertIn("@Metadata(", text)

    def test_schema_advertises_slim_defaulting_to_true(self):
        async def schemas():
            async with Client(jadx_mcp_server.mcp) as client:
                return {tool.name: getattr(tool, "input_schema", None) or tool.inputSchema
                        for tool in await client.list_tools()}

        with patch.object(sys, "argv", ["jadx_mcp_server.py"]):
            listed = asyncio.run(schemas())

        for name in (
            "get_class_source",
            "get_method_by_name",
            "fetch_current_class",
            "get_main_activity_class",
            "get_main_application_classes_code",
        ):
            prop = listed[name].get("properties", {}).get("slim")
            self.assertIsNotNone(prop, f"{name} does not expose slim")
            self.assertIs(prop.get("default"), True, f"{name}.slim default is not True")


if __name__ == "__main__":
    unittest.main()
