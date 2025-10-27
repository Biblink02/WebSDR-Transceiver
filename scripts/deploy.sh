#!/usr/bin/env bash
# Deployment script that properly handles ConfigMaps from source files
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
K8S_DIR="${REPO_ROOT}/k8s"

echo "=== Deploying WebSDR-Transceiver ==="

# Step 1: Apply CRD
echo "Applying CRD..."
kubectl apply -f "${K8S_DIR}/crd/usersession-crd.yaml"

# Step 2: Apply namespaces, RBAC, and deployments first (to create namespaces)
echo "Applying namespaces, RBAC, and deployments..."
kubectl apply -f "${K8S_DIR}/operator.yaml"
kubectl apply -f "${K8S_DIR}/broker.yaml"

# Step 3: Create ConfigMaps from source files (after namespaces exist)
echo "Creating ConfigMaps from source files..."
bash "${REPO_ROOT}/scripts/create-configmaps.sh"

# Step 4: Wait for deployments
echo "Waiting for Operator deployment..."
kubectl -n usersession-operator rollout status deploy/usersession-operator --timeout=180s

echo "Waiting for Broker deployment..."
kubectl -n websocket-broker rollout status deploy/websocket-broker --timeout=180s

echo "=== Deployment complete ==="
kubectl get pods -n usersession-operator
kubectl get pods -n websocket-broker

