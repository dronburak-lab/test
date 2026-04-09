# MCP Integration Plan

The current implementation keeps MCP support as a backend abstraction:

- `ToolsProvider` protocol defines `run(command, cwd)`.
- `LocalToolsProvider` is production-ready now.
- `MCPToolsProvider` is a placeholder adapter for future MCP server calls.

To enable MCP later:

1. Set `tools_provider.backend: mcp`.
2. Configure `tools_provider.mcp.server` and timeout.
3. Implement request/response mapping in `MCPToolsProvider.run`.
4. Keep `PolicyGuard` checks before any provider call.
