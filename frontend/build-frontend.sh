#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker build --file frontend/Dockerfile --target frontend-export --output type=local,dest=frontend/dist .
echo "C++ WebAssembly and frontend built successfully."
