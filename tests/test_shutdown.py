import sys
import unittest
from unittest.mock import patch

import jadx_mcp_server


class ShutdownTests(unittest.TestCase):
    def test_main_exits_cleanly_when_fastmcp_is_interrupted(self):
        with (
            patch.object(sys, "argv", ["jadx_mcp_server.py"]),
            patch.object(jadx_mcp_server.config, "health_ping", return_value="ok"),
            patch.object(
                jadx_mcp_server.mcp, "run", side_effect=KeyboardInterrupt
            ),
            self.assertLogs("jadx-mcp-server.bootstrap", level="INFO") as logs,
        ):
            try:
                jadx_mcp_server.main()
            except KeyboardInterrupt:
                self.fail("main() propagated KeyboardInterrupt")

        self.assertIn(
            "JADX MCP server interrupted; exiting cleanly", logs.output[-1]
        )


if __name__ == "__main__":
    unittest.main()
