#!/usr/bin/env bash
set -euo pipefail

# E2E test with kind to validate: CRD + Operator + Broker
# - Creates kind cluster
# - Applies CRD, Operator, Broker
# - Waits for readiness
# - Creates a UserSession CR (bypassing websocketd for speed)
# - Verifies namespace, quota, networkpolicy, and worker pod
# - Deletes the CR and verifies cleanup
# - Optionally deletes the cluster

CLUSTER_NAME=${CLUSTER_NAME:-usersess}
KIND_NODE_IMAGE=${KIND_NODE_IMAGE:-kindest/node:v1.30.0}
KEEP_CLUSTER=${KEEP_CLUSTER:-0}
NAMESPACE_OPERATOR=usersession-operator
NAMESPACE_BROKER=websocket-broker

log() { echo "[kind-e2e] $*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1" >&2; exit 1; }; }

need kind
need kubectl

log "Creating kind cluster ${CLUSTER_NAME} (image ${KIND_NODE_IMAGE})..."
if ! kind get clusters | grep -qx "${CLUSTER_NAME}"; then
  kind create cluster --name "${CLUSTER_NAME}" --image "${KIND_NODE_IMAGE}"
else
  log "Cluster already exists; reusing."
fi

kubectl cluster-info >/dev/null

REPO_ROOT=$(cd -- "$(dirname -- "$0")"/.. && pwd)
K8S_DIR="${REPO_ROOT}/k8s"

log "Applying CRD..."
kubectl apply -f "${K8S_DIR}/crd/usersession-crd.yaml"

log "Creating ConfigMaps from source files..."
bash "${REPO_ROOT}/scripts/create-configmaps.sh"

log "Applying Operator manifests..."
kubectl apply -f "${K8S_DIR}/operator.yaml"

log "Applying Broker manifests..."
kubectl apply -f "${K8S_DIR}/broker.yaml"

log "Waiting for Operator deployment to be ready..."
kubectl -n "${NAMESPACE_OPERATOR}" rollout status deploy/usersession-operator --timeout=180s

log "Waiting for Broker deployment to be ready..."
kubectl -n "${NAMESPACE_BROKER}" rollout status deploy/websocket-broker --timeout=180s

# Create a UserSession CR manually to trigger operator (faster than opening a websocket)
SESSION_NAME="usersess-$(date +%s)-$RANDOM"
log "Creating test UserSession ${SESSION_NAME}..."
cat <<EOF | kubectl apply -f -
apiVersion: sessions.example.com/v1alpha1
kind: UserSession
metadata:
  name: ${SESSION_NAME}
spec:
  userId: "e2e"
EOF

# Wait for namespace created
log "Waiting for namespace ${SESSION_NAME} to appear..."
for i in {1..60}; do
  if kubectl get ns "${SESSION_NAME}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
  if [ "$i" -eq 60 ]; then
    echo "Namespace ${SESSION_NAME} not created in time" >&2
    exit 1
  fi
done

# Wait for worker pod running/completed
log "Waiting for worker pod in namespace ${SESSION_NAME}..."
for i in {1..90}; do
  phase=$(kubectl -n "${SESSION_NAME}" get pod worker -o jsonpath='{.status.phase}' 2>/dev/null || true)
  if [ "${phase}" = "Running" ] || [ "${phase}" = "Succeeded" ]; then
    log "Worker pod phase: ${phase}"
    break
  fi
  sleep 2
  if [ "$i" -eq 90 ]; then
    echo "Worker pod not ready in time (phase=${phase})" >&2
    kubectl -n "${SESSION_NAME}" get pods -o wide || true
    exit 1
  fi
done

# Basic assertions: quota and networkpolicy exist
log "Checking ResourceQuota and NetworkPolicy presence..."
kubectl -n "${SESSION_NAME}" get resourcequota session-quota >/dev/null
kubectl -n "${SESSION_NAME}" get networkpolicy default-deny-all >/dev/null

log "Deleting UserSession ${SESSION_NAME} to trigger cleanup..."
kubectl delete usersessions.sessions.example.com "${SESSION_NAME}" --wait=true

log "Waiting for namespace ${SESSION_NAME} to be deleted..."
for i in {1..60}; do
  if ! kubectl get ns "${SESSION_NAME}" >/dev/null 2>&1; then
    log "Namespace deleted. Cleanup successful."
    break
  fi
  sleep 2
  if [ "$i" -eq 60 ]; then
    echo "Namespace ${SESSION_NAME} still exists after deletion window" >&2
    kubectl get ns "${SESSION_NAME}" -o yaml || true
    exit 1
  fi
done

log "E2E test completed successfully."

if [ "${KEEP_CLUSTER}" != "1" ]; then
  log "Deleting kind cluster ${CLUSTER_NAME}..."
  kind delete cluster --name "${CLUSTER_NAME}"
else
  log "Keeping cluster as requested (KEEP_CLUSTER=1)."
fi
