# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

Two processes must run simultaneously for the system to work:

**1. Go WhatsApp Bridge** (`whatsapp-bridge/`)
- Connects to WhatsApp via the [whatsmeow](https://github.com/tulir/whatsmeow) library (WhatsApp Web multidevice API)
- Authenticates via QR code on first run; session persists in `store/whatsapp.db`
- Syncs incoming messages and history into `store/messages.db` (SQLite)
- Exposes a REST API on `localhost:8080` with two endpoints:
  - `POST /api/send` — send a text message or media file
  - `POST /api/download` — download media from a stored message

**2. Python MCP Server** (`whatsapp-mcp-server/`)
- Implements the Model Context Protocol using `FastMCP` (from the `mcp` package)
- Exposes 12 tools to the MCP client (Claude Desktop / Cursor)
- **Reads** chats and messages by querying `../whatsapp-bridge/store/messages.db` directly via sqlite3
- **Sends/downloads** by calling the Go bridge REST API at `http://localhost:8080/api`

### Data flow

```
Claude Desktop → MCP Server (Python) → SQLite (read) / Go REST API (write/download)
                                              ↑
                                    Go Bridge ← WhatsApp Web API
```

### JID format

- Personal chats: `<phone_number>@s.whatsapp.net`
- Groups: `<id>@g.us`
- Phone numbers used in the API must include country code with no `+` or symbols (e.g. `4915123456789`)

### Media handling

- Media metadata (URL, encryption keys, type) is stored in `messages.db` at receive time; file content is only downloaded on demand via `download_media`
- Downloaded files are saved under `whatsapp-bridge/store/<chat_jid>/`
- Audio voice messages must be `.ogg` Opus format; `audio.py` handles conversion via ffmpeg subprocess
- The Go bridge parses OGG Opus files to extract duration and synthesises a 64-byte waveform for WhatsApp's voice message display

## Commands

### Go bridge

```bash
cd whatsapp-bridge
go run main.go          # run (QR code on first auth)
go build -o whatsapp-client main.go  # compile binary
```

On Windows, CGO must be enabled because `go-sqlite3` requires a C compiler:
```bash
go env -w CGO_ENABLED=1
go run main.go
```

### Python MCP server

```bash
# Run directly (requires uv)
uv --directory whatsapp-mcp-server run main.py

# Install dependencies
cd whatsapp-mcp-server && uv sync
```

Python version: 3.11 (see `.python-version`). Dependencies managed by `uv` (`pyproject.toml` + `uv.lock`).

## Resetting state

To force re-authentication with WhatsApp, delete both database files and restart the bridge:

```bash
rm whatsapp-bridge/store/messages.db whatsapp-bridge/store/whatsapp.db
cd whatsapp-bridge && go run main.go
```

## Claude Desktop Extension (.dxt)

The project can be packaged as a self-contained Claude Desktop Extension. The Python MCP server automatically starts the Go bridge as a subprocess; bridge logs go to `~/.whatsapp-mcp/bridge.log`.

### Build the extension

```bash
./build-dxt.sh
```

This compiles the Go bridge for the current platform (requires CGO/C compiler) and produces `whatsapp-mcp.dxt`.

### Install

Double-click `whatsapp-mcp.dxt` while Claude Desktop is running.

### First-time authentication

The Go bridge stores all data in `~/.whatsapp-mcp/store/`. On first run it needs QR-code authentication — ask Claude: *"Get setup instructions for WhatsApp"* to receive step-by-step instructions.

### Data directory layout

```
~/.whatsapp-mcp/
  bridge.log           ← bridge stdout/stderr
  store/
    messages.db        ← message history (SQLite)
    whatsapp.db        ← WhatsApp session
    <chat_jid>/        ← downloaded media files
```

## Manual MCP client configuration (development)

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "/path/to/uv",
      "args": ["--directory", "/path/to/whatsapp-mcp/whatsapp-mcp-server", "run", "main.py"]
    }
  }
}
```

In development mode the Python server falls back to the compiled binary at `whatsapp-bridge/whatsapp-client` if no bundled binary is found in `whatsapp-mcp-server/bin/`.
