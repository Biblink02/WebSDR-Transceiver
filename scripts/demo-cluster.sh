#!/usr/bin/env bash
# Local, persistent preview of the current branch with synthetic or emulated I/Q.
set -euo pipefail
TASK_ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEMO_CLUSTER=websdr-iq-demo
DEMO_CONTEXT="kind-$DEMO_CLUSTER"
DEMO_STATE="${TMPDIR:-/tmp}/websdr-iq-demo"
DEMO_PORT=${DEMO_PORT:-18080}
DEMO_SOURCE=${DEMO_SOURCE:-synthetic}
case "$DEMO_SOURCE" in
    synthetic) DEMO_SCENARIO=${DEMO_SCENARIO:-automatic} ;;
    iio) DEMO_SCENARIO=${DEMO_SCENARIO:-clean} ;;
    *) printf 'DEMO_SOURCE must be synthetic or iio.\n' >&2; exit 1 ;;
esac
PYTHON_BIN=${PYTHON_BIN:-python3}
DEMO_VENV="$TASK_ROOT/.venv"
DEMO_PYTHON="$DEMO_VENV/bin/python"
export KUBECONFIG="$DEMO_STATE/kubeconfig"

prepare_python() {
    if [ ! -x "$DEMO_PYTHON" ]; then
        "$PYTHON_BIN" -m venv "$DEMO_VENV"
    fi
    if ! "$DEMO_PYTHON" -c 'import sys; raise SystemExit(sys.prefix == sys.base_prefix)'; then
        printf 'Expected a valid virtual environment at %s.\n' "$DEMO_VENV" >&2
        exit 1
    fi
    "$DEMO_PYTHON" -m pip install --disable-pip-version-check \
        -r "$TASK_ROOT/scripts/requirements-demo.txt" >&2
}

render_manifest() {
    prepare_python
    "$DEMO_PYTHON" - "$TASK_ROOT" "$DEMO_SOURCE" "$DEMO_SCENARIO" <<'PY'
import sys
import json
from pathlib import Path
import yaml

root = Path(sys.argv[1])
source_mode, scenario = sys.argv[2:4]
catalog = json.loads((root/'tools/simulation/scenarios.json').read_text())
if scenario not in catalog['scenarios'] and scenario != 'tones':
    raise ValueError(f'Unknown demo scenario: {scenario}')
if source_mode == 'iio' and (scenario == 'tones' or any(event['action'] == 'stall' for event in catalog['scenarios'][scenario])):
    raise ValueError('IIO replay supports clean/fading/drift/squelch/qrm; use synthetic capture for transport stalls')
config = yaml.safe_load((root/'config/config.yaml').read_text())
config['ws_url'] = '/'
if source_mode == 'iio':
    config['iio_uri'] = 'ip:iio-emulator'
    config['sdr_idle_seconds'] = .5
documents = [
    {'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'sdr-config'},
     'data': {'config.yaml': yaml.safe_dump(config)}},
    {'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'frontend-config'},
     'data': {'Caddyfile': (root/'config/Caddyfile').read_text()}},
]
for component in ('sdr-server', 'backend-controller', 'frontend'):
    for document in yaml.safe_load_all((root/'kubernetes'/f'{component}.yaml').read_text()):
        if document['kind'] == 'Deployment':
            spec = document['spec']['template']['spec']
            container = spec['containers'][0]
            container['image'] = f'websdr-transceiver/{component}:iq-demo'
            if component == 'sdr-server':
                container['image'] = 'websdr-transceiver/synthetic-iq:iq-demo'
                container['command'] = ['python3', '-u', '/app/synthetic_iq.py']
                container['args'] = ['--address', 'tcp://0.0.0.0:5000', '--health-port', '8081',
                                     '--idle-seconds', '0.5', '--rate', str(config['samp_rate']),
                                     '--center', str(config['lo_freq'])]
                container['args'].extend(['--scenario', scenario])
                if source_mode == 'iio':
                    container['command'] = ['python3', '-u', '/app/emulated_receiver.py']
                    container['args'] = []
                for key in ('hostNetwork', 'dnsPolicy', 'affinity'):
                    spec.pop(key, None)
            elif component == 'backend-controller':
                document['spec']['replicas'] = 2
            elif component == 'frontend':
                spec.pop('hostNetwork', None)
                spec.pop('dnsPolicy', None)
                container['env'] = [{'name': 'PUBLIC_SITE', 'value': 'http://:80'}]
        documents.append(document)
if source_mode == 'iio':
    labels = {'app': 'iio-emulator'}
    documents.extend([
        {'apiVersion': 'v1', 'kind': 'Service', 'metadata': {'name': 'iio-emulator'},
         'spec': {'selector': labels, 'ports': [{'name': 'iio', 'port': 30431, 'targetPort': 30431}]}},
        {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': {'name': 'iio-emulator'},
         'spec': {'replicas': 1, 'selector': {'matchLabels': labels}, 'template': {
             'metadata': {'labels': labels}, 'spec': {
                 'initContainers': [{'name': 'generate-replay', 'image': 'websdr-transceiver/synthetic-iq:iq-demo',
                     'command': ['python3', '/app/iio_profile.py', '--output', '/data',
                                 '--rate', str(config['samp_rate']), '--center', str(int(config['lo_freq'])),
                                 '--scenario', scenario, '--seconds', str(catalog['period_seconds'])],
                     'volumeMounts': [{'name': 'replay', 'mountPath': '/data'}]}],
                 'containers': [{'name': 'emulator', 'image': 'websdr-transceiver/iio-emulator:iq-demo',
                     'ports': [{'name': 'iio', 'containerPort': 30431}],
                     'volumeMounts': [{'name': 'replay', 'mountPath': '/data', 'readOnly': True}],
                     'readinessProbe': {'tcpSocket': {'port': 'iio'}, 'periodSeconds': 2}}],
                 'volumes': [{'name': 'replay', 'emptyDir': {'sizeLimit': '512Mi'}}]}}}}
    ])
sys.stdout.write(yaml.safe_dump_all(documents))
PY
}

serve() {
    if [[ ! "$DEMO_PORT" =~ ^[0-9]{1,5}$ ]] || ((10#$DEMO_PORT < 1024 || 10#$DEMO_PORT > 65535)); then
        printf 'DEMO_PORT must be an integer in [1024, 65535].\n' >&2
        exit 1
    fi
    printf 'Open http://localhost:%s/sdr. Ctrl+C stops forwarding; the demo cluster stays available.\n' "$DEMO_PORT"
    exec kubectl --context "$DEMO_CONTEXT" port-forward --address 127.0.0.1 service/frontend "${DEMO_PORT}:80"
}

case "${1:-start}" in
    manifest)
        render_manifest
        exit 0
        ;;
    serve)
        serve
        ;;
    stop)
        kind delete cluster --name "$DEMO_CLUSTER" --kubeconfig "$KUBECONFIG"
        rm -f "$DEMO_STATE/kubeconfig" "$DEMO_STATE/manifest.yaml"
        if [ -d "$DEMO_STATE" ]; then rmdir "$DEMO_STATE" 2>/dev/null || true; fi
        exit 0
        ;;
    start)
        ;;
    *)
        printf 'Usage: bash scripts/demo-cluster.sh [start|serve|stop|manifest]\n' >&2
        exit 1
        ;;
esac

cd "$TASK_ROOT"
for dependency in docker kind kubectl "$PYTHON_BIN"; do
    command -v "$dependency" >/dev/null || { printf 'Missing dependency: %s\n' "$dependency" >&2; exit 1; }
done
if kind get clusters | grep -qx "$DEMO_CLUSTER"; then
    printf 'The demo cluster already exists. Use serve to reopen the preview, or stop before rebuilding.\n' >&2
    exit 1
fi
mkdir -p "$DEMO_STATE"
render_manifest > "$DEMO_STATE/manifest.yaml"

docker build -f backend-controller/Dockerfile -t websdr-transceiver/backend-controller:iq-demo .
docker build -f frontend/Dockerfile -t websdr-transceiver/frontend:iq-demo .
# The existing synthetic Dockerfile derives from this test-only source image.
docker build -f sdr-server/Dockerfile -t websdr-transceiver/sdr-server:wasm-test .
docker build -f tests/Dockerfile.synthetic -t websdr-transceiver/synthetic-iq:iq-demo .
DEMO_IMAGES=(websdr-transceiver/backend-controller:iq-demo websdr-transceiver/frontend:iq-demo
             websdr-transceiver/synthetic-iq:iq-demo)
if [ "$DEMO_SOURCE" = iio ]; then
    docker build -f tools/iio-emulator/Dockerfile -t websdr-transceiver/iio-emulator:iq-demo .
    DEMO_IMAGES+=(websdr-transceiver/iio-emulator:iq-demo)
fi
kind create cluster --name "$DEMO_CLUSTER" --image kindest/node:v1.34.0 --kubeconfig "$KUBECONFIG" --wait 120s
kind load docker-image --name "$DEMO_CLUSTER" "${DEMO_IMAGES[@]}"
kubectl --context "$DEMO_CONTEXT" apply -f "$DEMO_STATE/manifest.yaml"
if [ "$DEMO_SOURCE" = iio ]; then
    kubectl --context "$DEMO_CONTEXT" rollout status deployment/iio-emulator --timeout=180s
fi
for component in sdr-server backend-controller frontend; do
    kubectl --context "$DEMO_CONTEXT" rollout status "deployment/$component" --timeout=180s
done
serve
