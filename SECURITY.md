# Security Policy
---
### Runtime Hardening

The MCP bridge is local-first by default:

- Stdio mode is preferred for local MCP clients.
- Omit `--http` to run the MCP server over stdio. This keeps MCP traffic on the parent process stdin/stdout pipes and avoids opening a listening socket.
- HTTP mode requires bearer authentication. Use `JADX_MCP_SERVER_TOKEN` or `--http-token`; otherwise a temporary token is generated and printed to stderr.
- `--host` may not bind outside loopback unless `--allow-remote-http` is set.
- `--jadx-host` may not target a non-loopback host unless `--allow-remote-jadx` is set. Prefer SSH tunnels to reach a remote JADX plugin.
- The bridge always forwards `Authorization: Bearer <token>` to the Java plugin. It uses `--jadx-token`, then `JADX_AI_MCP_TOKEN`, then a secure random per-run token.
- If the Java plugin enforces bearer auth, configure both the bridge and plugin with the same stable token.
- Use `--jadx-mode headless` or `JADX_MCP_JADX_MODE=headless` when connecting to the Java headless server. This keeps GUI-only current-selection tools, refactor tools, and debug tools unavailable from the MCP layer.
- Refactor tools are disabled unless `JADX_MCP_ENABLE_REFACTOR=true` or `--enable-refactor` is set.
- Debug tools are disabled unless `JADX_MCP_ENABLE_DEBUG=true` or `--enable-debug` is set.
- Tool output derived from APK code, resources, or debugger state is labeled as untrusted artifact data for prompt-injection resistance.

### Reporting a Vulnerability

To report a security issue, please open a new [security advisory](https://github.com/zinja-coder/jadx-mcp-server/security/advisories). Please fill the steps you took to create the issue, affected versions, and, if known, mitigations for the issue. We will check and respond within 3 working days. If the issue is confirmed as a vulnerability, we will apply required mitigations at the next release.
