#!/usr/bin/env bash

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

export PATH="/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

echo "🛑 Stopping all NotifAI Enterprise containers..."
docker compose down --remove-orphans
pkill -f "broker_nodejs/\.wwebjs_auth" 2>/dev/null || true
echo "✅ All services stopped successfully."

