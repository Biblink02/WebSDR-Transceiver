#!/usr/bin/env bash
set -euo pipefail

# Generate a unique session name
SESSION_NAME="usersess-$(date +%s)-$(head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')"
API_VERSION="sessions.example.com/v1alpha1"
KUBECTL_BIN="${KUBECTL_BIN:-kubectl}"

# Set kubeconfig for in-cluster access
export KUBERNETES_SERVICE_HOST=${KUBERNETES_SERVICE_HOST:-}
export KUBERNETES_SERVICE_PORT=${KUBERNETES_SERVICE_PORT:-443}

cleanup() {
  # Delete the UserSession CR on exit
  ${KUBECTL_BIN} delete usersessions.sessions.example.com ${SESSION_NAME} --ignore-not-found=true || true
}
trap cleanup EXIT INT TERM

# Create the UserSession CR
cat <<EOF | ${KUBECTL_BIN} apply -f - --validate=false
apiVersion: ${API_VERSION}
kind: UserSession
metadata:
  name: ${SESSION_NAME}
spec:
  userId: "${REMOTE_ADDR:-unknown}"
EOF

echo "SESSION_CREATED ${SESSION_NAME}" >&2

# Keep the script alive while the websocket is connected.
# Echo back any input (optional) and send heartbeat to keep connection open.
while IFS= read -r line; do
  echo "echo: $line"
done

# When stdin closes, the trap will delete the CR.
