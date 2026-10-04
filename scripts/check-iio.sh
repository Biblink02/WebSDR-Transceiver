#!/usr/bin/env bash
# No host GNU Radio/Python dependencies, hardware connection or exposed TCP port.
set -euo pipefail
TASK_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$TASK_ROOT"
TEST_DATA=$(mktemp -d)
EMULATOR_ID=
cleanup() {
    if [ -n "$EMULATOR_ID" ]; then docker rm -f "$EMULATOR_ID" >/dev/null; fi
    rm -rf "$TEST_DATA"
}
trap cleanup EXIT
docker build -f sdr-server/Dockerfile -t websdr-transceiver/sdr-server:wasm-test .
docker build -f tests/Dockerfile.synthetic -t websdr-transceiver/synthetic-iq:iio-test .
docker build -f tools/iio-emulator/Dockerfile -t websdr-transceiver/iio-emulator:iio-test .
docker run --rm --user "$(id -u):$(id -g)" -v "$TEST_DATA:/data" \
    websdr-transceiver/synthetic-iq:iio-test python3 /app/iio_profile.py --output /data --seconds 2
# The server runs unprivileged; mktemp's parent is otherwise private to its owner.
chmod 755 "$TEST_DATA"
EMULATOR_ID=$(docker run -d -v "$TEST_DATA:/data:ro" websdr-transceiver/iio-emulator:iio-test)
docker run --rm --network "container:$EMULATOR_ID" -v "$TASK_ROOT:/workspace:ro" \
    -v "$TASK_ROOT/config/config.yaml:/app/config.yaml:ro" -v "$TEST_DATA:/data:ro" \
    -e PYTHONPATH=/workspace/shared:/workspace/sdr-server \
    websdr-transceiver/sdr-server:wasm-test python3 /workspace/tests/iio_flowgraph_check.py \
    --uri ip:127.0.0.1 --replay /data/cf-ad9361-lpc_buf0.bin
