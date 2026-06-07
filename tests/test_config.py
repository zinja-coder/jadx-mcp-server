import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.server import config


class ConfigHttpTest(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        config.set_jadx_token(None, None)

    async def test_get_from_jadx_forwards_bearer_and_marks_json(self):
        response = MagicMock()
        response.json.return_value = {"content": "apk data"}
        response.raise_for_status.return_value = None

        client = AsyncMock()
        client.get.return_value = response
        client.__aenter__.return_value = client

        config.set_jadx_token("plugin-token", "test")
        with patch("httpx.AsyncClient", return_value=client):
            result = await config.get_from_jadx("class-source", {"class_name": "a.b.C"})

        client.get.assert_awaited_once()
        _, kwargs = client.get.call_args
        self.assertEqual({"Authorization": "Bearer plugin-token"}, kwargs["headers"])
        self.assertTrue(result["untrusted_artifact"])
        self.assertEqual("apk data", result["content"])

    async def test_post_to_jadx_forwards_bearer_and_marks_text(self):
        response = MagicMock()
        response.json.side_effect = ValueError("not json")
        response.text = "renamed"
        response.raise_for_status.return_value = None

        client = AsyncMock()
        client.post.return_value = response
        client.__aenter__.return_value = client

        config.set_jadx_token("plugin-token", "test")
        with patch("httpx.AsyncClient", return_value=client):
            result = await config.post_to_jadx("rename-class", {"new_name": "GoodName"})

        client.post.assert_awaited_once()
        _, kwargs = client.post.call_args
        self.assertEqual({"Authorization": "Bearer plugin-token"}, kwargs["headers"])
        self.assertTrue(result["untrusted_artifact"])
        self.assertIn("UNTRUSTED APK ARTIFACT DATA", result["response"])


if __name__ == "__main__":
    unittest.main()
