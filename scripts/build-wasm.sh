#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
BUILD_DIR=${WASM_BUILD_DIR:-dsp-wasm/build-wasm}
emcmake cmake -S dsp-wasm -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD_DIR" --parallel "${BUILD_JOBS:-4}"
mkdir -p frontend/dev/src/public/licenses
cp "$BUILD_DIR/websdr_dsp.wasm" frontend/dev/src/public/dsp.wasm
cp "$BUILD_DIR/_deps/liquid-src/LICENSE" frontend/dev/src/public/licenses/liquid-dsp.txt
