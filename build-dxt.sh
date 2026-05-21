#!/usr/bin/env bash
# Builds the Go bridge binary for the current platform and packages a .dxt extension.
#
# Prerequisites:
#   - Go with CGO_ENABLED=1 (requires a C compiler; on macOS: Xcode Command Line Tools)
#   - uv  (https://docs.astral.sh/uv/)
#   - zip
#
# Usage:
#   ./build-dxt.sh
#
# Output: whatsapp-mcp.dxt (installable in Claude Desktop by double-clicking)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/whatsapp-mcp-server/bin"

mkdir -p "$BIN_DIR"

echo "==> Building Go bridge..."
cd "$SCRIPT_DIR/whatsapp-bridge"

GOOS=$(go env GOOS)
GOARCH=$(go env GOARCH)
EXT=""
[[ "$GOOS" == "windows" ]] && EXT=".exe"

OUTPUT="$BIN_DIR/whatsapp-bridge-${GOOS}-${GOARCH}${EXT}"

CGO_ENABLED=1 go build -o "$OUTPUT" .
echo "    Built: $OUTPUT"

cd "$SCRIPT_DIR"

echo "==> Packaging .dxt..."
rm -f whatsapp-mcp.dxt

zip -r whatsapp-mcp.dxt \
  manifest.json \
  whatsapp-mcp-server/ \
  --exclude "whatsapp-mcp-server/.venv/*" \
  --exclude "whatsapp-mcp-server/__pycache__/*" \
  --exclude "whatsapp-mcp-server/*.pyc" \
  --exclude "whatsapp-mcp-server/.gitignore" \
  --exclude "whatsapp-mcp-server/.python-version"

echo ""
echo "✓ Done: whatsapp-mcp.dxt"
echo ""
echo "Install: double-click whatsapp-mcp.dxt in Finder (Claude Desktop must be running)"
echo ""
echo "First-time setup:"
echo "  Ask Claude: 'Get setup instructions for WhatsApp'"
