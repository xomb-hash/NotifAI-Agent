#!/usr/bin/env bash
set -e

# Resolve project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Ensure macOS Docker environment PATH is available
export PATH="/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

echo "🚀 =================================================================="
echo "               LAUNCHING NOTIFAI ENTERPRISE                          "
echo "======================================================================"

# Check if user requested a fresh QR code / session reset
if [[ "$1" == "--reset" || "$1" == "--new-qr" || "$1" == "-r" ]]; then
    echo "🧹 Reset requested: Purging saved WhatsApp session to force fresh QR code..."
    rm -rf broker_nodejs/.wwebjs_auth 2>/dev/null || true
fi

# 0. Clean up any zombie host Chrome processes or stale lock files
pkill -f "broker_nodejs/\.wwebjs_auth" 2>/dev/null || true
rm -f broker_nodejs/.wwebjs_auth/session/Singleton* 2>/dev/null || true

# 1. Build and start containers in the background
echo "📦 Building & starting Docker containers..."
docker compose up -d --remove-orphans

# 2. Wait for QR server to be responsive
echo "⏳ Waiting for QR server on port 3000..."
for i in {1..30}; do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null | grep -q "200"; then
    echo "⚡ QR server is live!"
    break
  fi
  sleep 0.4
done

# 3. Automatically pop up the browser window with the blurred glass modal
echo "🌐 Opening glassmorphic QR pop-up on desktop..."
open "http://localhost:3000" || true

echo ""
echo "======================================================================"
echo "✅ NotifAI is live!"
echo "📱 Scan the QR code in the browser window: http://localhost:3000"
echo "📺 Streaming live logs below (Press Ctrl+C to exit logs; app stays on)"
echo "======================================================================"
echo ""

# 4. Stream real-time logs in the terminal
docker compose logs -f
