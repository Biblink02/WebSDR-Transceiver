"""Roll out production manifests in the dedicated synthetic-I/Q test cluster."""
import asyncio
import json
import os
import subprocess
import time
from pathlib import Path

import httpx
import yaml
from websockets.asyncio.client import connect

from iq_protocol import validate_frame
from tests.test_backend import free_port

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = 'kind-websdr-wasm-check'


def kubectl(*args, payload=None):
    result = subprocess.run(['kubectl', '--context', CONTEXT, *args],
                            input=payload, text=True, capture_output=True, check=True)
    return result.stdout


def pods():
    return json.loads(kubectl('get', 'pods', '-o', 'json'))['items']


def restarts():
    return {pod['metadata']['name']: sum(status['restartCount'] for status in
            pod['status'].get('containerStatuses', [])) for pod in pods()}


async def main():
    if not os.getenv('KUBECONFIG'):
        raise RuntimeError('Set KUBECONFIG to the dedicated test cluster kubeconfig')
    config = yaml.safe_load((ROOT / 'config/config.yaml').read_text())
    config['ws_url'] = '/'
    documents = [{'apiVersion': 'v1', 'kind': 'ConfigMap',
                  'metadata': {'name': 'sdr-config'},
                  'data': {'config.yaml': yaml.safe_dump(config)}}]
    for component in ['sdr-server', 'backend-controller', 'frontend']:
        for document in yaml.safe_load_all((ROOT / 'kubernetes' / f'{component}.yaml').read_text()):
            if document['kind'] == 'Deployment':
                spec = document['spec']['template']['spec']
                container = spec['containers'][0]
                container['image'] = container['image'].replace(':latest', ':wasm-test')
                if component == 'sdr-server':
                    container['image'] = 'websdr-transceiver/synthetic-iq:wasm-test'
                    spec.pop('hostNetwork')
                    spec.pop('dnsPolicy')
                    spec.pop('affinity')
                elif component == 'backend-controller':
                    document['spec']['replicas'] = 2
            documents.append(document)
    print(kubectl('apply', '-f', '-', payload=yaml.safe_dump_all(documents)), flush=True)
    for name in ['sdr-server', 'backend-controller', 'frontend-nginx']:
        print(kubectl('rollout', 'status', f'deployment/{name}', '--timeout=120s'), flush=True)

    port = free_port()
    log_path = Path(os.environ['KUBECONFIG']).parent / 'port-forward.log'
    with log_path.open('w') as log:
        forward = subprocess.Popen(['kubectl', '--context', CONTEXT, 'port-forward',
                                    'service/frontend-nginx', f'{port}:80'], stdout=log, stderr=log)
        try:
            base = f'http://127.0.0.1:{port}'
            async with httpx.AsyncClient() as http:
                for _ in range(100):
                    try:
                        if (await http.get(base + '/health')).status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    await asyncio.sleep(.1)
                else:
                    raise AssertionError(log_path.read_text())
                response = await http.get(base + '/dsp.wasm')
                assert response.status_code == 200
                assert response.headers['content-type'] == 'application/wasm'
                assert response.content.startswith(b'\0asm')
                assert (await http.get(base + '/licenses/liquid-dsp.txt')).status_code == 200
                assert yaml.safe_load((await http.get(base + '/config.yaml')).text)['ws_url'] == '/'

                async with connect(base.replace('http', 'ws') + '/iq', max_queue=4) as first, \
                        connect(base.replace('http', 'ws') + '/iq', max_queue=4) as second:
                    frames = await asyncio.gather(first.recv(), second.recv())
                    metadata = [validate_frame(frame) for frame in frames]
                    assert all(info.sample_rate == 520834 for info in metadata)
                    assert metadata[0].epoch == metadata[1].epoch
                    initial = restarts()
                    assert len(initial) == 4 and all(count == 0 for count in initial.values())
                    source = next(pod['metadata']['name'] for pod in pods()
                                  if pod['metadata']['labels']['app'] == 'sdr-server')
                    await asyncio.to_thread(kubectl, 'exec', source, '--', 'touch', '/tmp/iq-stall')
                    deadline = time.monotonic() + 60
                    changed = False
                    while time.monotonic() < deadline:
                        info = validate_frame(await asyncio.wait_for(first.recv(), 45))
                        if info.epoch != metadata[0].epoch:
                            changed = True
                            break
                    assert changed, 'Source did not recover after liveness restart'
                    # The second listener drains its bounded WebSocket queue and resumes too.
                    while time.monotonic() < deadline:
                        info = validate_frame(await asyncio.wait_for(second.recv(), 15))
                        if info.epoch != metadata[1].epoch:
                            break
                    else:
                        raise AssertionError('Second listener did not resume')

                print(kubectl('rollout', 'status', 'deployment/sdr-server', '--timeout=60s'), flush=True)
                after = restarts()
                assert set(after) == set(initial), 'Unexpected pod replacement'
                assert after[source] == 1, after
                assert all(count == 0 for name, count in after.items() if name != source), after
                assert (await http.get(base + '/stream-info')).json()['sample_rate'] == 520834
                print('PASS: two backend replicas, nginx WebSocket upgrade, WASM MIME, '
                      'two resumed listeners; source restarted once, downstream restart counts stayed zero.',
                      flush=True)
        finally:
            forward.terminate()
            forward.wait(timeout=10)


if __name__ == '__main__':
    asyncio.run(main())
