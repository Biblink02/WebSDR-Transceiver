#!/bin/bash

set -euo pipefail
cd "$(dirname "$0")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting WebSDR deployment procedure...${NC}"

# --- 1. CLUSTER AND HARDWARE SETUP ---
echo -e "${YELLOW}[1/5] Setting up cluster and hardware...${NC}"

if ! kind get clusters | grep -q "^kind$"; then
    echo "Kind cluster not found. Creating a new cluster..."
    kind create cluster --config kind-config.yaml

    echo "Installing NGINX Ingress Controller..."
    kubectl apply -f \
      https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
else
    echo "Kind cluster is already running."
fi

echo "Applying hardware label to node..."
kubectl label nodes kind-control-plane hardware=sdr-true --overwrite

# --- 2. BUILD AND LOAD IMAGES ---
echo -e "${YELLOW}[2/5] Building and loading Docker images...${NC}"

build_and_load() {
    local image_name="$1"
    local context_dir="$2"

    echo "Building image: $image_name"
    docker build -t "$image_name" "$context_dir"

    echo "Loading image into Kind: $image_name"
    kind load docker-image "$image_name"
}

build_and_load "websdr-transceiver/backend-controller:latest" "../backend-controller"
build_and_load "websdr-transceiver/sdr-server:latest" "../sdr-server"
build_and_load "websdr-transceiver/audio-worker:latest" "../audio-worker"
build_and_load "websdr-transceiver/graphics-worker:latest" "../graphics-worker"

# --- 3. CLEAN OLD PODS ---
echo -e "${YELLOW}[3/5] Restarting pods...${NC}"

kubectl delete pod -l app=backend-controller --ignore-not-found
kubectl delete pod -l app=sdr-server --ignore-not-found
kubectl delete pod -l app=audio-worker --ignore-not-found
kubectl delete pod -l app=graphics-worker --ignore-not-found

# --- 4. APPLY MANIFESTS ---
echo -e "${YELLOW}[4/5] Applying Kubernetes manifests...${NC}"

kubectl create configmap sdr-config --from-file=config.yaml=../config/config.yaml --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f ingress.yaml
kubectl apply -f backend-controller.yaml
kubectl apply -f sdr-server.yaml
kubectl apply -f audio-workers.yaml
kubectl apply -f graphics-worker.yaml

# --- 5. FINAL STATUS ---
echo -e "${GREEN}Deployment complete.${NC}"
echo "Wait a few seconds for pods to enter Running state."
echo "Monitor with: kubectl get pods -w"
echo "Frontend available at: http://localhost" #TODO
