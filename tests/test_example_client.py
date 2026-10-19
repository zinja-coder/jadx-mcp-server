"""
Tests for examples/openai_compatible_client.py.

The example is loaded by path because it lives outside the package, and importing
it must not require the OpenAI SDK - only running it against a model does. That
keeps the conversion contract (MCP tool -> OpenAI function tool) covered by CI,
where the SDK is deliberately not installed.
"""

import importlib.util
import unittest
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "openai_compatible_client.py"


def _load_example():
    spec = importlib.util.spec_from_file_location("openai_compatible_client", EXAMPLE)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {EXAMPLE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeTool:
    def __init__(self, name, description=None, schema=None):
        self.name = name
        self.description = description
        self.input_schema = schema


class _FakeBlock:
    def __init__(self, text):
        self.text = text


class _FakeResult:
    def __init__(self, blocks):
        self.content = blocks


class ExampleClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example = _load_example()

    def test_importing_the_example_does_not_need_the_openai_sdk(self):
        self.assertTrue(callable(self.example.as_openai_tools))
        self.assertTrue(callable(self.example.tool_schema))

    def test_mcp_tool_becomes_an_openai_function_tool(self):
        schema = {
            "type": "object",
            "properties": {"class_name": {"type": "string"}},
            "required": ["class_name"],
        }
        converted = self.example.as_openai_tools(
            [_FakeTool("get_class_source", "Fetch the source of a class", schema)]
        )

        self.assertEqual(converted, [{
            "type": "function",
            "function": {
                "name": "get_class_source",
                "description": "Fetch the source of a class",
                "parameters": schema,
            },
        }])

    def test_tool_list_is_converted_wholesale(self):
        tools = [_FakeTool(f"tool_{i}") for i in range(3)]
        converted = self.example.as_openai_tools(tools)
        self.assertEqual([entry["function"]["name"] for entry in converted],
                         ["tool_0", "tool_1", "tool_2"])

    def test_missing_description_and_schema_get_safe_defaults(self):
        function = self.example.as_openai_tools([_FakeTool("no_docs", None, None)])[0]["function"]

        self.assertIn("no_docs", function["description"])
        self.assertEqual(function["parameters"], {"type": "object", "properties": {}})

    def test_schema_is_read_from_either_fastmcp_attribute(self):
        class OldStyleTool:  # older fastmcp exposed inputSchema
            name = "old_style"
            description = "old style tool"
            inputSchema = {"type": "object", "properties": {"a": {"type": "string"}}}

        self.assertEqual(self.example.tool_schema(OldStyleTool()), OldStyleTool.inputSchema)

    def test_tool_result_blocks_are_flattened_to_text(self):
        result = _FakeResult([_FakeBlock("first"), _FakeBlock("second")])
        self.assertEqual(self.example.result_to_text(result), "first\nsecond")

    def test_tool_result_without_text_blocks_still_returns_something(self):
        self.assertTrue(self.example.result_to_text(_FakeResult([])))

    def test_env_variables_feed_the_defaults(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"OPENAI_BASE_URL": "http://x/v1", "OPENAI_MODEL": "m"}, clear=False):
            args = self.example.parse_args(["--api-key", "k"])
        self.assertEqual(args.base_url, "http://x/v1")
        self.assertEqual(args.model, "m")

    def test_list_tools_does_not_require_an_api_key(self):
        args = self.example.parse_args(["--list-tools"])
        self.assertTrue(args.list_tools)


if __name__ == "__main__":
    unittest.main()
