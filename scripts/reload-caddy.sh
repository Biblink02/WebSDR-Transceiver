#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
CONTEXT="kind-${CLUSTER_NAME:-kind}"
# Validate before updating the stored configuration or the live proxy.
kubectl --context "$CONTEXT" exec -i deployment/frontend -- \
    caddy validate --config - --adapter caddyfile < config/Caddyfile
kubectl --context "$CONTEXT" create configmap frontend-config \
    --from-file=Caddyfile=config/Caddyfile --dry-run=client -o yaml | kubectl --context "$CONTEXT" apply -f -
kubectl --context "$CONTEXT" exec -i deployment/frontend -- \
    caddy reload --config - --adapter caddyfile < config/Caddyfile
echo "Caddy configuration validated and reloaded."
