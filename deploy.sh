#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "Building SDR, distributor, and C++ WebAssembly frontend images..."
docker build -f frontend/Dockerfile -t websdr-transceiver/frontend-nginx:latest .
docker build -f backend-controller/Dockerfile -t websdr-transceiver/backend-controller:latest .
docker build -f sdr-server/Dockerfile -t websdr-transceiver/sdr-server:latest .
bash kubernetes/start-cluster.sh
