#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/4] Checking Kind cluster..."

if ! kind get clusters | grep -q "^kind$"; then
    echo "Creating Kind cluster..."
    kind create cluster --config kind-config.yaml

    echo "Installing NGINX Ingress Controller..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.1/deploy/static/provider/kind/deploy.yaml

    echo "Removing admission webhook (avoids startup deadlock)..."
    sleep 5
    kubectl delete -A ValidatingWebhookConfiguration ingress-nginx-admission --ignore-not-found || true

    echo "Waiting for ingress controller pod to appear..."
    for i in {1..60}; do
        COUNT=$(kubectl -n ingress-nginx get pods -l app.kubernetes.io/component=controller --no-headers 2>/dev/null | wc -l)
        if [ "$COUNT" -gt 0 ]; then
            echo "Ingress controller pod detected."
            break
        fi
        sleep 2
    done

    echo "Waiting for ingress controller to become ready..."
    kubectl wait \
        --namespace ingress-nginx \
        --for=condition=ready pod \
        -l app.kubernetes.io/component=controller \
        --timeout=300s

else
    echo "Kind cluster already exists."
fi

echo "Applying SDR hardware label..."
kubectl label nodes kind-control-plane hardware=sdr-true --overwrite 2>/dev/null || true

echo "[2/4] Loading container images into Kind..."
kind load docker-image websdr-transceiver/frontend-nginx:latest
kind load docker-image websdr-transceiver/backend-controller:latest
kind load docker-image websdr-transceiver/sdr-server:latest
kind load docker-image websdr-transceiver/audio-worker:latest
kind load docker-image websdr-transceiver/graphics-worker:latest

echo "[3/4] Cleaning old pods..."
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

echo "Waiting for application pods..."
kubectl wait --for=condition=ready pod -l app --timeout=300s

echo "------------------------------------------------"
echo "Cluster ready."
echo "Frontend available at: http://localhost"
echo "------------------------------------------------"
