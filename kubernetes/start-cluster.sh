#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/4] Checking Kind cluster..."

if ! kind get clusters | grep -q "^kind$"; then
    echo "Creating Kind cluster..."
    kind create cluster --config kind-config.yaml

    echo "Installing NGINX Ingress Controller..."
    kubectl apply -f \
      https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

    echo "Waiting for Ingress Controller to be ready..."
    kubectl wait --namespace ingress-nginx \
      --for=condition=ready pod \
      --selector=app.kubernetes.io/component=controller \
      --timeout=180s
    # -----------------------------------------
else
    echo "Kind cluster already exists."
fi

echo "Applying SDR hardware label..."
kubectl label nodes kind-control-plane hardware=sdr-true --overwrite


echo "[2/4] Loading container images into Kind..."
kind load docker-image websdr-transceiver/frontend-nginx:latest
kind load docker-image websdr-transceiver/backend-controller:latest
kind load docker-image websdr-transceiver/sdr-server:latest
kind load docker-image websdr-transceiver/audio-worker:latest
kind load docker-image websdr-transceiver/graphics-worker:latest


echo "[3/4] Cleaning old pods to force update..."
kubectl delete pod -l app=backend-controller --ignore-not-found
kubectl delete pod -l app=sdr-server --ignore-not-found
kubectl delete pod -l app=audio-worker --ignore-not-found
kubectl delete pod -l app=graphics-worker --ignore-not-found
kubectl delete pod -l app=frontend-nginx --ignore-not-found


echo "[4/4] Applying Kubernetes manifests..."

kubectl create configmap sdr-config \
    --from-file=config.yaml=../config/config.yaml \
    --dry-run=client -o yaml | kubectl apply -f -


kubectl apply -f backend-controller.yaml
kubectl apply -f sdr-server.yaml
kubectl apply -f audio-workers.yaml
kubectl apply -f graphics-worker.yaml
kubectl apply -f frontend.yaml
kubectl apply -f ingress.yaml

echo "Waiting for all application pods to be ready..."
kubectl wait --for=condition=ready pod --all --timeout=300s
# -----------------------------------------

echo "------------------------------------------------"
echo "Cluster ready."
echo "Frontend available at: http://localhost"
echo "------------------------------------------------"