# Security Policy
---
### Runtime Hardening

The MCP bridge is local-first by default:

- Stdio mode is preferred for local MCP clients.
- HTTP mode requires bearer authentication. Use `JADX_MCP_SERVER_TOKEN` or `--http-token`; otherwise a temporary token is generated and printed to stderr.
- `--host` may not bind outside loopback unless `--allow-remote-http` is set.
- `--jadx-host` may not target a non-loopback host unless `--allow-remote-jadx` is set. Prefer SSH tunnels to reach a remote JADX plugin.
- The bridge forwards `Authorization: Bearer <token>` to the Java plugin when `JADX_AI_MCP_TOKEN` or `--jadx-token` is configured.
- Refactor tools are disabled unless `JADX_MCP_ENABLE_REFACTOR=true` or `--enable-refactor` is set.
- Debug tools are disabled unless `JADX_MCP_ENABLE_DEBUG=true` or `--enable-debug` is set.
- Tool output derived from APK code, resources, or debugger state is labeled as untrusted artifact data for prompt-injection resistance.

### Reporting a Vulnerability

To report a security issue, please open a new [security advisory](https://github.com/zinja-coder/jadx-mcp-server/security/advisories). Please fill the steps you took to create the issue, affected versions, and, if known, mitigations for the issue. We will check and respond within 3 working days. If the issue is confirmed as a vulnerability, we will apply required mitigations at the next release.
