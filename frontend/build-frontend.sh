#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

FRONTEND_DIR="dev/src"
DIST_DIR="dist"

# --- Build frontend using Node inside a container ---
docker run --rm \
    -v "$(pwd)/$FRONTEND_DIR:/app" \
    -w /app \
    node:20 \
    bash -c "npm ci || npm install && npm run build"

# --- Copy build output to repository root ---
rm -rf "$DIST_DIR"
cp -r "$FRONTEND_DIR/$DIST_DIR" .

echo "Frontend build completed using containerized Node."
