# WhatsApp MCP Server

A Model Context Protocol (MCP) server for WhatsApp that lets Claude search and read your personal WhatsApp messages (including images, videos, documents, and audio messages), search contacts, and send messages or media files to individuals or groups.

It connects to your **personal WhatsApp account** directly via the WhatsApp Web multidevice API (using the [whatsmeow](https://github.com/tulir/whatsmeow) library). All messages are stored locally in a SQLite database and only sent to Claude when you explicitly access them through tools.

![WhatsApp MCP](./example-use.png)

> *Caution:* as with many MCP servers, the WhatsApp MCP is subject to [the lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). Prompt injection could lead to private data exfiltration.

---

## Installation

There are two ways to install: as a **Claude Desktop Extension** (easiest) or **manually** (for development or Cursor).

---

### Option A — Claude Desktop Extension (recommended)

The extension bundles the Go bridge and Python MCP server into a single file that Claude Desktop installs with one double-click.

#### Prerequisites

- [Claude Desktop](https://claude.ai/download)
- [Go](https://go.dev/dl/) with a C compiler (for CGO)
  - macOS: `xcode-select --install`
  - Linux: `sudo apt install gcc`
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

#### Build and install

```bash
git clone https://github.com/KaiserWu/whatsapp-mcp.git
cd whatsapp-mcp
./build-dxt.sh
```

This produces `whatsapp-mcp.dxt`. **Double-click it** while Claude Desktop is running — the extension installs automatically.

#### First-time authentication

The Go bridge needs to link with your WhatsApp account once. There are two ways:

**QR code** (default):
1. Ask Claude: *"Get setup instructions for WhatsApp"*
2. Follow the instructions to run the bridge binary once in a terminal
3. Scan the QR code with your WhatsApp app (Settings → Linked Devices → Link a Device)
4. Close the terminal — Claude Desktop restarts the bridge automatically from now on

**Phone number** (headless / no QR code):
```bash
WA_PHONE=+491234567890 ~/.whatsapp-mcp/whatsapp-bridge-darwin-arm64
```
Enter the displayed 8-digit code in WhatsApp → Linked Devices → Link with phone number.

> The symlink at `~/.whatsapp-mcp/` is created automatically the first time Claude Desktop starts the extension.

All data is stored in `~/.whatsapp-mcp/store/`. Bridge logs are at `~/.whatsapp-mcp/bridge.log`.

---

### Option B — Manual setup (development / Cursor)

#### Prerequisites

- [Go](https://go.dev/dl/)
- [Python](https://www.python.org/) 3.11–3.13
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [FFmpeg](https://ffmpeg.org/) *(optional)* — only needed to send voice messages in non-OGG formats

#### Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/KaiserWu/whatsapp-mcp.git
   cd whatsapp-mcp
   ```

2. **Start the WhatsApp bridge**

   ```bash
   cd whatsapp-bridge
   go run main.go
   ```

   On first run, scan the QR code with your WhatsApp app. The session persists in `whatsapp-bridge/store/` — you won't need to scan again unless you log out.

   **Alternative — phone number pairing** (no QR code):
   ```bash
   WA_PHONE=+491234567890 go run main.go
   ```
   Enter the 8-digit code shown in WhatsApp → Linked Devices → Link with phone number.

3. **Configure the MCP client**

   **Claude Desktop** — add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

   ```json
   {
     "mcpServers": {
       "whatsapp": {
         "command": "/path/to/uv",
         "args": [
           "--directory",
           "/path/to/whatsapp-mcp/whatsapp-mcp-server",
           "run",
           "main.py"
         ]
       }
     }
   }
   ```

   **Cursor** — add to `~/.cursor/mcp.json` with the same structure.

   Run `which uv` and `pwd` (inside the repo) to get the correct paths.

4. **Restart Claude Desktop / Cursor**

#### Windows compatibility

`go-sqlite3` requires CGO. Install [MSYS2](https://www.msys2.org/), add `ucrt64\bin` to your PATH ([guide](https://code.visualstudio.com/docs/cpp/config-mingw)), then:

```bash
cd whatsapp-bridge
go env -w CGO_ENABLED=1
go run main.go
```

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_contacts` | Search contacts by name or phone number |
| `list_chats` | List chats with optional filters |
| `list_messages` | Retrieve messages with filters and context |
| `get_chat` | Get metadata for a specific chat |
| `get_direct_chat_by_contact` | Find a direct chat by phone number |
| `get_contact_chats` | All chats involving a contact |
| `get_last_interaction` | Most recent message with a contact |
| `get_message_context` | Surrounding messages around a specific message |
| `send_message` | Send a text message |
| `send_file` | Send an image, video, document, or audio file |
| `send_audio_message` | Send an audio file as a WhatsApp voice message |
| `download_media` | Download media from a message to a local file |
| `get_setup_instructions` | First-time authentication instructions (DXT only) |

### Sending media

- **Images, videos, documents** (PDF, DOCX, XLSX, PPTX, …): use `send_file`
- **Voice messages**: use `send_audio_message` — files are automatically converted to OGG Opus if FFmpeg is installed; without FFmpeg, use `send_file` instead (file won't appear as a playable voice message)

### Downloading media

Media content is not stored locally by default — only metadata. Use `download_media` with the `message_id` and `chat_jid` shown in message listings to download the actual file.

---

## Architecture

Two processes work together:

```
Claude Desktop ──► Python MCP Server ──► SQLite DB (read)
                                    └──► Go Bridge REST API (send / download)
                                              │
                                         WhatsApp Web API
```

- **Go bridge** (`whatsapp-bridge/`) — connects to WhatsApp, syncs messages into `messages.db`, exposes `POST /api/send` and `POST /api/download` on `127.0.0.1:8080`
- **Python MCP server** (`whatsapp-mcp-server/`) — reads directly from SQLite, sends/downloads via the bridge REST API

When installed as a DXT extension, the Python server starts the Go bridge automatically as a subprocess.

---

## Troubleshooting

**Bridge won't connect / "Client outdated"** — the session or binary is stale. Delete `store/whatsapp.db` (or `~/.whatsapp-mcp/store/whatsapp.db` for DXT) and re-authenticate.

**No messages loading** — after first authentication it can take several minutes for history to sync, especially with many chats.

**Device limit reached** — WhatsApp allows max 4 linked devices. Remove one in WhatsApp → Settings → Linked Devices.

**Messages out of sync** — delete both database files and re-authenticate:
```bash
rm whatsapp-bridge/store/messages.db whatsapp-bridge/store/whatsapp.db
cd whatsapp-bridge && go run main.go
```
For DXT: `rm -rf ~/.whatsapp-mcp/store && restart Claude Desktop`

**Bridge log (DXT)**: `~/.whatsapp-mcp/bridge.log`

For Claude Desktop MCP troubleshooting see the [MCP documentation](https://modelcontextprotocol.io/quickstart/server#claude-for-desktop-integration-issues).
