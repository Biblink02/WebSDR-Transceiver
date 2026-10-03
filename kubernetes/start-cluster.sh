#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CLUSTER_NAME=${CLUSTER_NAME:-kind}
CONTEXT="kind-$CLUSTER_NAME"
if ! kind get clusters | rg -qx "$CLUSTER_NAME"; then
    kind create cluster --name "$CLUSTER_NAME" --config kind-config.yaml
fi
kubectl --context "$CONTEXT" label nodes "$CLUSTER_NAME-control-plane" hardware=sdr-true --overwrite
for image in frontend backend-controller sdr-server; do
    kind load docker-image --name "$CLUSTER_NAME" "websdr-transceiver/$image:latest"
done
kubectl --context "$CONTEXT" create configmap sdr-config \
    --from-file=config.yaml=../config/config.yaml --dry-run=client -o yaml | kubectl --context "$CONTEXT" apply -f -
kubectl --context "$CONTEXT" create configmap frontend-config \
    --from-file=Caddyfile=../config/Caddyfile --dry-run=client -o yaml | kubectl --context "$CONTEXT" apply -f -
# This script is an explicit deployment: retire workloads removed from the architecture.
kubectl --context "$CONTEXT" delete deployment graphics-worker sdr-watchdog redis nginx-proxy-manager frontend-nginx --ignore-not-found --wait=true
kubectl --context "$CONTEXT" delete statefulset audio-worker --ignore-not-found
kubectl --context "$CONTEXT" delete service audio-workers-headless redis frontend-nginx --ignore-not-found
kubectl --context "$CONTEXT" delete serviceaccount sdr-watchdog --ignore-not-found
kubectl --context "$CONTEXT" delete role,rolebinding sdr-watchdog --ignore-not-found
kubectl --context "$CONTEXT" delete configmap sdr-watchdog-script --ignore-not-found
kubectl --context "$CONTEXT" delete ingress sdr-ingress --ignore-not-found
for manifest in backend-controller sdr-server frontend; do
    kubectl --context "$CONTEXT" apply -f "$manifest.yaml"
done
for deployment in backend-controller sdr-server frontend; do
    kubectl --context "$CONTEXT" rollout restart "deployment/$deployment"
    kubectl --context "$CONTEXT" rollout status "deployment/$deployment" --timeout=180s
done
echo "Receiver deployment ready. Public HTTPS is managed by config/Caddyfile."
