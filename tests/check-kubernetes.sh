#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
CLUSTER=websdr-wasm-check
if kind get clusters | rg -qx "$CLUSTER"; then
    printf 'The dedicated test cluster %s already exists.\n' "$CLUSTER" >&2
    exit 1
fi
for component in backend-controller sdr-server; do
    docker build -f "$component/Dockerfile" -t "websdr-transceiver/$component:wasm-test" .
done
docker build -f frontend/Dockerfile -t websdr-transceiver/frontend:wasm-test .
docker build -f tests/Dockerfile.synthetic -t websdr-transceiver/synthetic-iq:wasm-test .
TEST_DIR=$(mktemp -d)
export KUBECONFIG="$TEST_DIR/kubeconfig"
cleanup() {
    kind delete cluster --name "$CLUSTER" --kubeconfig "$KUBECONFIG"
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT
kind create cluster --name "$CLUSTER" --image kindest/node:v1.34.0 --kubeconfig "$KUBECONFIG" --wait 120s
kind load docker-image --name "$CLUSTER" \
    websdr-transceiver/backend-controller:wasm-test websdr-transceiver/sdr-server:wasm-test \
    websdr-transceiver/frontend:wasm-test websdr-transceiver/synthetic-iq:wasm-test
PYTHONPATH=.:shared:backend-controller:sdr-server "${PYTHON_BIN:-python3}" tests/check_kubernetes.py
