import unittest
from unittest.mock import AsyncMock, patch

from src.server import config
from src.server.tools import refactor_tools


class RefactorToolsTest(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        config.set_refactor_tools_enabled(False)

    async def test_refactor_disabled_by_default(self):
        result = await refactor_tools.rename_class("a.b.C", "BetterName")

        self.assertIn("disabled", result["error"])

    async def test_refactor_rejects_invalid_java_name(self):
        config.set_refactor_tools_enabled(True)

        result = await refactor_tools.rename_class("a.b.C", "bad-name")

        self.assertEqual("new_name must be a valid Java identifier", result["error"])

    async def test_refactor_uses_post_when_enabled(self):
        config.set_refactor_tools_enabled(True)
        with patch.object(refactor_tools, "post_to_jadx", new=AsyncMock(return_value={"result": "ok"})) as mocked:
            result = await refactor_tools.rename_class("a.b.C", "BetterName")

        mocked.assert_awaited_once_with(
            "rename-class",
            {"class_name": "a.b.C", "new_name": "BetterName"},
        )
        self.assertEqual({"result": "ok"}, result)


if __name__ == "__main__":
    unittest.main()
