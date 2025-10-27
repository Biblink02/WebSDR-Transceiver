#!/usr/bin/env bash
# Script to create ConfigMaps from source files
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)

echo "Creating operator-code ConfigMap from operator/main.py..."
kubectl create configmap operator-code \
  --from-file=main.py="${REPO_ROOT}/operator/main.py" \
  --namespace=usersession-operator \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Creating broker-script ConfigMap from broker/gestore-sessione.sh..."
kubectl create configmap broker-script \
  --from-file=gestore-sessione.sh="${REPO_ROOT}/broker/gestore-sessione.sh" \
  --namespace=websocket-broker \
  --dry-run=client -o yaml | kubectl apply -f -

echo "ConfigMaps created successfully!"

