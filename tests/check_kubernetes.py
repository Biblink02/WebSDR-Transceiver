"""Roll out production manifests in a dedicated cluster with synthetic I/Q."""
import asyncio
import json
import os
import ssl
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


async def wait_json(http, url, predicate, timeout=15):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            response = await http.get(url)
            last = response.json()
            if predicate(last): return last
        except httpx.HTTPError: pass
        await asyncio.sleep(.1)
    raise AssertionError(f'{url}: {last}')


async def main():
    if not os.getenv('KUBECONFIG'):
        raise RuntimeError('Set KUBECONFIG to the dedicated test cluster kubeconfig')
    config = yaml.safe_load((ROOT / 'config/config.yaml').read_text())
    config['ws_url'] = '/'
    documents = [{'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'sdr-config'},
                  'data': {'config.yaml': yaml.safe_dump(config)}},
                 {'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'frontend-config'},
                  'data': {'Caddyfile': (ROOT/'config/Caddyfile').read_text()}}]
    for component in ['sdr-server', 'backend-controller', 'frontend']:
        for document in yaml.safe_load_all((ROOT / 'kubernetes' / f'{component}.yaml').read_text()):
            if document['kind'] == 'Deployment':
                spec = document['spec']['template']['spec']
                container = spec['containers'][0]
                container['image'] = container['image'].replace(':latest', ':wasm-test')
                if component == 'sdr-server':
                    container['image'] = 'websdr-transceiver/synthetic-iq:wasm-test'
                    spec.pop('hostNetwork'); spec.pop('dnsPolicy'); spec.pop('affinity')
                elif component == 'backend-controller':
                    document['spec']['replicas'] = 2
                elif component == 'frontend':
                    spec.pop('hostNetwork'); spec.pop('dnsPolicy')
                    # Automatic local CA, with no public ACME requests or production DNS.
                    container['env'] = [{'name': 'PUBLIC_SITE', 'value': 'localhost'}]
            documents.append(document)
    print(kubectl('apply', '-f', '-', payload=yaml.safe_dump_all(documents)), flush=True)
    for name in ['sdr-server', 'backend-controller', 'frontend']:
        print(kubectl('rollout', 'status', f'deployment/{name}', '--timeout=120s'), flush=True)

    http_port, tls_port, source_port = free_port(), free_port(), free_port()
    work = Path(os.environ['KUBECONFIG']).parent
    with (work/'port-forward.log').open('w') as log:
        forwards = [subprocess.Popen(['kubectl', '--context', CONTEXT, 'port-forward', 'service/frontend',
                        f'{http_port}:80', f'{tls_port}:443'], stdout=log, stderr=log),
                    subprocess.Popen(['kubectl', '--context', CONTEXT, 'port-forward', 'service/sdr-server',
                        f'{source_port}:8081'], stdout=log, stderr=log)]
        try:
            frontend = next(pod['metadata']['name'] for pod in pods() if pod['metadata']['labels']['app'] == 'frontend')
            source = next(pod['metadata']['name'] for pod in pods() if pod['metadata']['labels']['app'] == 'sdr-server')
            ca = work/'caddy-root.crt'
            ca.write_text(kubectl('exec', frontend, '--', 'cat', '/data/caddy/pki/authorities/local/root.crt'))
            tls = ssl.create_default_context(cafile=str(ca))
            base = f'https://localhost:{tls_port}'
            health_url = f'http://127.0.0.1:{source_port}/health'
            async with httpx.AsyncClient(verify=tls) as http:
                await wait_json(http, health_url, lambda s: s['mode'] == 'idle')
                for _ in range(100):
                    try:
                        if (await http.get(base+'/health')).status_code == 200: break
                    except httpx.HTTPError: pass
                    await asyncio.sleep(.1)
                else: raise AssertionError((work/'port-forward.log').read_text())
                redirect = await http.get(f'http://localhost:{http_port}/sdr')
                assert redirect.status_code == 308 and redirect.headers['location'].startswith('https://localhost/')
                assert (await http.get(base+'/sdr?freq=10489700300&bw=1800')).status_code == 200
                response = await http.get(base+'/dsp.wasm')
                assert response.status_code == 200 and response.headers['content-type'] == 'application/wasm'
                assert response.content.startswith(b'\0asm')
                for name in ['liquid-dsp', 'd3-scale-chromatic', 'd3-color', 'd3-interpolate']:
                    assert (await http.get(base+f'/licenses/{name}.txt')).status_code == 200
                cfg = await http.get(base+'/config.yaml')
                assert yaml.safe_load(cfg.text)['ws_url'] == '/' and cfg.headers['cache-control'] == 'no-store'
                initial = restarts()
                assert len(initial) == 4 and all(count == 0 for count in initial.values())
                idle = (await http.get(health_url)).json()
                assert idle['capture_starts'] == 0 and idle['subscribers'] == 0
                for command in ['validate', 'reload']:
                    await asyncio.to_thread(kubectl, 'exec', '-i', frontend, '--', 'caddy', command,
                        '--config', '-', '--adapter', 'caddyfile', payload=(ROOT/'config/Caddyfile').read_text())
                assert (await http.get(base+'/health')).status_code == 200

                async with connect(base.replace('https', 'wss')+'/iq', ssl=tls, max_queue=4) as first, \
                        connect(base.replace('https', 'wss')+'/iq', ssl=tls, max_queue=4) as second:
                    metadata = [validate_frame(frame) for frame in await asyncio.gather(first.recv(), second.recv())]
                    assert all(info.sample_rate == 520834 for info in metadata)
                    assert metadata[0].epoch == metadata[1].epoch
                    await asyncio.to_thread(kubectl, 'exec', source, '--', 'touch', '/tmp/iq-stall')
                    deadline = time.monotonic() + 60
                    while time.monotonic() < deadline:
                        info = validate_frame(await asyncio.wait_for(first.recv(), 45))
                        if info.epoch != metadata[0].epoch: break
                    else: raise AssertionError('Source did not recover after liveness restart')
                    while time.monotonic() < deadline:
                        info = validate_frame(await asyncio.wait_for(second.recv(), 15))
                        if info.epoch != metadata[1].epoch: break
                    else: raise AssertionError('Second listener did not resume')
                    # Exercise a long-lived WSS stream past the one-minute regression boundary.
                    end = time.monotonic() + 65
                    while time.monotonic() < end:
                        await asyncio.wait_for(first.recv(), 5)
                        await asyncio.wait_for(second.recv(), 5)

                idle = await wait_json(http, health_url, lambda s: s['mode'] == 'idle')
                assert idle['subscribers'] == 0 and not idle['capture_active']
                published = idle['counters']['published']
                await asyncio.sleep(3)
                assert (await http.get(health_url)).json()['counters']['published'] == published
                async with connect(base.replace('https', 'wss')+'/iq', ssl=tls) as resumed:
                    assert validate_frame(await asyncio.wait_for(resumed.recv(), 5)).epoch != info.epoch
                after = restarts()
                assert set(after) == set(initial), 'Unexpected pod replacement'
                assert after[source] == 1, after
                assert all(count == 0 for name, count in after.items() if name != source), after
                # Replace the frontend pod and keep trusting the original persisted CA.
                await asyncio.to_thread(kubectl, 'rollout', 'restart', 'deployment/frontend')
                await asyncio.to_thread(kubectl, 'rollout', 'status', 'deployment/frontend', '--timeout=60s')
                forwards[0].terminate(); forwards[0].wait(timeout=5)
                forwards[0] = subprocess.Popen(['kubectl', '--context', CONTEXT, 'port-forward', 'service/frontend',
                    f'{http_port}:80', f'{tls_port}:443'], stdout=log, stderr=log)
                for _ in range(100):
                    try:
                        if (await http.get(base+'/health')).status_code == 200: break
                    except httpx.HTTPError: pass
                    await asyncio.sleep(.1)
                else: raise AssertionError('Caddy did not resume with persisted TLS data')
                replacement = next(p['metadata']['name'] for p in pods() if p['metadata']['labels']['app'] == 'frontend')
                assert replacement != frontend
                assert kubectl('exec', replacement, '--', 'cat', '/data/caddy/pki/authorities/local/root.crt') == ca.read_text()
                async with connect(base.replace('https', 'wss')+'/iq', ssl=tls) as resumed:
                    assert validate_frame(await asyncio.wait_for(resumed.recv(), 5)).sample_rate == 520834
                print('PASS: Caddy HTTPS redirect, trusted local TLS/WSS, WASM/config/licenses, '
                      'two backend replicas, two listeners beyond 65 seconds, idle/wake, '
                      'source-only liveness restart; downstream restarts stayed zero. '
                      'Caddy stdin validation/reload and persisted TLS after frontend replacement passed.', flush=True)
        finally:
            for forward in forwards:
                forward.terminate(); forward.wait(timeout=10)


if __name__ == '__main__':
    asyncio.run(main())
