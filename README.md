# UEFN MCP Server

Control [UEFN](https://dev.epicgames.com/documentation/en-us/fortnite/unreal-editor-for-fortnite) (Unreal Editor for Fortnite) from [OpenCode](https://github.com/opencode-ai/opencode) or [Claude Code](https://docs.anthropic.com/en/docs/claude-code) via the [Model Context Protocol](https://modelcontextprotocol.io/).

```
OpenCode/Claude  <--stdio-->  MCP Server (mcp_server.py)  <--HTTP-->  Listener (uefn_listener.py, inside UEFN)
```

- **36 tools**: actors, assets, levels, viewport, project info, Verse context, and arbitrary Python execution
- **Zero C++ compilation** — pure Python, works across UEFN versions
- **Main-thread safe** — all `unreal.*` calls dispatched via editor tick callback
- **Security hardening** — read-only mode, token auth, policy-based command filtering

## Quick Start

### 0. Install dependencies

```bash
pip install mcp
```

### 1. Enable Python in UEFN

1. Open your project in UEFN
2. Go to **Project > Project Settings**
3. Search for **Python** and check the box for **Python Editor Script Plugin**

### 2. Start the listener inside UEFN

Use **Tools > Execute Python Script** in the UEFN menu bar, then select the `uefn_listener.py` file.

A **status window** will appear showing:
- **Listener status** — green when running, red when stopped
- **MCP Server status** — green when connected (heartbeat every 10s)
- **Port** — editable when listener is stopped
- **Metrics** — uptime, request count, errors, last command, avg response time
- **Controls** — Stop / Start / Restart buttons

### 3. Configure OpenCode

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "uefn": {
      "command": "python",
      "args": ["/path/to/uefn-mcp-server/mcp_server.py"]
    }
  }
}
```

### 4. Restart OpenCode

OpenCode picks up `.mcp.json` on startup. After restart, you'll have 36 UEFN tools available.

### Try it

Ask OpenCode:
- *"Get project summary"*
- *"List all actors in the level"*
- *"Find actors with cube in the name"*
- *"What Verse files are in the project?"*
- *"Spawn a cube at position 100, 200, 300"*

## Security Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `UEFN_MCP_PORT` | `8765` | HTTP port for the listener |
| `UEFN_MCP_TOKEN` | `""` | Auth token (if set, requires `X-MCP-Token` header) |
| `UEFN_MCP_READ_ONLY` | `false` | Block all mutating commands |
| `UEFN_MCP_ENABLE_EXECUTE_PYTHON` | `false` | Enable `execute_python` (dangerous) |
| `UEFN_MCP_DEBUG` | `false` | Show full tracebacks in errors |
| `UEFN_MCP_MAX_REQUEST_BYTES` | `2000000` | Max HTTP request size accepted by the listener (DoS protection) |
| `UEFN_MCP_SPAWN_ACTOR_CLASS_DENYLIST` | `TextRenderActor` | Comma-separated actor classes blocked in `spawn_actor` |
| `UEFN_MCP_REQUEST_TIMEOUT` | `30.0` | External MCP server request timeout (seconds) |
| `UEFN_MCP_HEARTBEAT_INTERVAL` | `10.0` | External MCP server heartbeat interval (seconds) |

### Read-Only Mode

To prevent accidental modifications:

```json
{
  "mcpServers": {
    "uefn": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": { "UEFN_MCP_READ_ONLY": "1" }
    }
  }
}
```

### Token Authentication

To require an auth token:

```json
{
  "mcpServers": {
    "uefn": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": { "UEFN_MCP_TOKEN": "your-secret-token" }
    }
  }
}
```

The listener will validate the `X-MCP-Token` header on every request.

### Enable execute_python (use with caution)

```json
{
  "mcpServers": {
    "uefn": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": { "UEFN_MCP_ENABLE_EXECUTE_PYTHON": "1" }
    }
  }
}
```

## Tools

### System

| Tool | Risk Level | Description |
|------|------------|-------------|
| `ping` | safe | Check if listener is running |
| `get_log` | safe | Get recent MCP listener log entries |
| `get_editor_log` | safe | Read UE Output Log |
| `shutdown` | dangerous | Stop the listener |

### Actors

| Tool | Risk Level | Description |
|------|------------|-------------|
| `get_all_actors` | safe | List all actors in level |
| `get_selected_actors` | safe | Get currently selected actors |
| `find_actors` | safe | Search actors by name/class |
| `get_actor_details` | safe | Get comprehensive actor info |
| `get_actor_properties` | safe | Read specific properties |
| `spawn_actor` | mutating | Spawn an actor in level |
| `delete_actors` | dangerous | Delete actors |
| `set_actor_transform` | mutating | Set location/rotation/scale |
| `set_actor_properties` | mutating | Set properties on actor |
| `select_actors` | mutating | Select actors in viewport |
| `focus_selected` | mutating | Focus viewport on selection |

### Assets

| Tool | Risk Level | Description |
|------|------------|-------------|
| `list_assets` | safe | List assets in directory |
| `get_asset_info` | safe | Get asset details |
| `get_selected_assets` | safe | Get selected assets in Content Browser |
| `find_assets` | safe | Search assets by name/class |
| `does_asset_exist` | safe | Check if asset exists |
| `search_assets` | safe | Search via Asset Registry |
| `duplicate_asset` | mutating | Duplicate an asset |
| `rename_asset` | mutating | Rename or move asset |
| `save_asset` | mutating | Save modified asset |
| `delete_asset` | dangerous | Delete an asset |

### Project & Level

| Tool | Risk Level | Description |
|------|------------|-------------|
| `get_project_info` | safe | Get project name and content root |
| `get_project_summary` | safe | Get comprehensive editor snapshot |
| `get_level_info` | safe | Get current level info |
| `save_current_level` | mutating | Save the level |

### Viewport

| Tool | Risk Level | Description |
|------|------------|-------------|
| `get_viewport_camera` | safe | Get camera position/rotation |
| `set_viewport_camera` | mutating | Move the camera |

### Verse Context

| Tool | Risk Level | Description |
|------|------------|-------------|
| `list_verse_files` | safe | List all .verse files |
| `read_verse_file` | safe | Read a Verse file |
| `find_editable_bindings` | safe | Find @editable declarations |
| `scan_verse_symbols` | safe | Extract symbols heuristically |

### Python Execution

| Tool | Risk Level | Description |
|------|------------|-------------|
| `execute_python` | dangerous | Run arbitrary Python in UEFN |

**Warning**: `execute_python` is disabled by default. Enable with `UEFN_MCP_ENABLE_EXECUTE_PYTHON=1`.

## Auto-start (optional)

To start the listener automatically when UEFN opens your project:

```bash
cp uefn_listener.py  <YourUEFNProject>/Content/Python/uefn_listener.py
cp init_unreal.py     <YourUEFNProject>/Content/Python/init_unreal.py
cp config.py          <YourUEFNProject>/Content/Python/config.py
cp policy.py          <YourUEFNProject>/Content/Python/policy.py
```

UEFN automatically executes `init_unreal.py` on project open.

## Architecture

```
┌─────────────────┐     stdio     ┌──────────────┐     HTTP      ┌──────────────────┐
│   OpenCode      │ ◄───────────► │  MCP Server  │ ◄───────────► │   UEFN Listener  │
│   (AI client)   │               │              │   127.0.0.1   │                  │
└─────────────────┘               │ mcp_server.py│               │ uefn_listener.py │
                                  └──────────────┘               └──────────────────┘
```

- **MCP Server**: External Python process, connects via stdio to OpenCode
- **UEFN Listener**: Runs inside UEFN editor, handles all `unreal.*` API calls
- **Security**: Policy-based filtering, auth tokens, read-only mode

See [docs/architecture.md](docs/architecture.md) for details.

## Requirements

- UEFN editor with Python scripting enabled
- Python 3.10+ on host system
- `pip install mcp`
- OpenCode or Claude Code CLI

## License

MIT
