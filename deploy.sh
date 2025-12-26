#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/3] Compiling GRC files locally..."

compile_grc() {
    local dir="$1"
    local file="$2"
    echo "Compiling $dir/$file..."
    rm -f "$dir"/*.py
    grcc -o "$dir" "$dir/$file"
}

compile_grc "sdr-server" "sdr_server.grc"
compile_grc "audio-worker" "audio_worker.grc"
compile_grc "graphics-worker" "graphics_worker.grc"

echo "[2/3] Building Docker images..."
bash frontend/build-frontend.sh
docker build -t websdr-transceiver/frontend-nginx:latest ./frontend
docker build -t websdr-transceiver/backend-controller:latest ./backend-controller
docker build -t websdr-transceiver/sdr-server:latest ./sdr-server
docker build -t websdr-transceiver/audio-worker:latest ./audio-worker
docker build -t websdr-transceiver/graphics-worker:latest ./graphics-worker

echo "[3/3] Starting / updating cluster..."
bash kubernetes/start-cluster.sh

echo "Deployment complete."
