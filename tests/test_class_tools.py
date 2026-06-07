import unittest
from unittest.mock import AsyncMock, patch

from src.server import config
from src.server.tools import class_tools


class ClassToolsHeadlessTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        config.set_jadx_mode("gui")

    async def test_fetch_current_class_rejected_in_headless_mode(self):
        config.set_jadx_mode("headless")
        with patch.object(class_tools, "get_from_jadx", new=AsyncMock()) as mocked:
            result = await class_tools.fetch_current_class()
        self.assertIn("headless mode", result["error"])
        mocked.assert_not_called()

    async def test_selected_text_rejected_in_headless_mode(self):
        config.set_jadx_mode("headless")
        with patch.object(class_tools, "get_from_jadx", new=AsyncMock()) as mocked:
            result = await class_tools.get_selected_text()
        self.assertIn("headless mode", result["error"])
        mocked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
