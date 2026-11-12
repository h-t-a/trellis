# IDE Integration Matrix

Trellis ships one zero-dependency MCP server (`python -m trellis_mcp`) and generates
editor-specific configuration from a single source of truth.

| Editor | Config key | Workspace file | Generate command |
| --- | --- | --- | --- |
| Claude Code | `mcpServers` | `.mcp.json` | `python -m trellis_mcp --emit-config claude --config-out .mcp.json` |
| Antigravity | `mcpServers` | `.agents/mcp_config.json` | `python -m trellis_mcp --sync-workspace` (already writes this file) |
| VS Code (MCP) | `servers` | `.vscode/mcp.json` | `python -m trellis_mcp --emit-config vscode --config-out .vscode/mcp.json` |
| JetBrains AI Assistant | `mcpServers` | in-IDE JSON panel | `python -m trellis_mcp --emit-config jetbrains` and paste the output |
| Cursor | `mcpServers` | `.cursor/mcp.json` | `python -m trellis_mcp --emit-config cursor --config-out .cursor/mcp.json` |
| Windsurf | `mcpServers` | `.windsurf/mcp.json` | `python -m trellis_mcp --emit-config windsurf --config-out .windsurf/mcp.json` |

## Local (stdio) mode

```powershell
python -m trellis_mcp --emit-config vscode --config-out .vscode/mcp.json
```

Generated payload:

```json
{
  "servers": {
    "trellis-mcp": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "trellis_mcp"],
      "env": {"PYTHONPATH": "."}
    }
  }
}
```

## Remote (HTTP) mode

Point any editor at a private VM running `--serve-http`. Secrets are referenced by
environment variable, never embedded in the file.

```powershell
$env:TRELLIS_API_KEY = "<member-api-key>"
python -m trellis_mcp --emit-config vscode --remote-url https://vm.example.internal:8443 --config-out .vscode/mcp.json
```

Generated payload:

```json
{
  "servers": {
    "trellis-mcp": {
      "type": "http",
      "url": "https://vm.example.internal:8443/mcp",
      "headers": {"Authorization": "Bearer ${env:TRELLIS_API_KEY}"}
    }
  }
}
```

## Notes

- VS Code uses `servers` with an explicit `type` (`stdio` or `http`); all other editors use `mcpServers`.
- JetBrains AI Assistant stores MCP configuration in its settings panel rather than a workspace file; run `--emit-config jetbrains` and paste the JSON.
- Never commit real API keys. Use environment variable references (`${env:TRELLIS_API_KEY}`) as shown above.
