"""Check five Caddy listeners, capture idle/wake and recovery on either IQ branch."""
import argparse
import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from collections import Counter

import httpx
import numpy as np
from websockets.asyncio.client import connect

from iq_protocol import validate_frame
from tests.test_backend import free_port

CONTEXT = 'kind-websdr-iq-demo'


def kubectl(*args):
    return subprocess.check_output(['kubectl', '--context', CONTEXT, *args], text=True)


def restart_counts():
    pods = json.loads(kubectl('get', 'pods', '-o', 'json'))['items']
    counts = Counter()
    for pod in pods:
        counts[pod['metadata']['labels']['app']] += sum(status['restartCount'] for status in pod['status']['containerStatuses'])
    return dict(counts)


async def status(http, url, predicate, timeout=20):
    deadline = time.monotonic()+timeout
    value = None
    while time.monotonic() < deadline:
        try:
            value = (await http.get(url)).json()
            if predicate(value): return value
        except httpx.HTTPError:
            pass
        await asyncio.sleep(.1)
    raise AssertionError(value)


async def wait_new_epochs(latest, initial, readers, timeout):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        for reader in readers:
            if reader.done():
                await reader
                raise AssertionError('Listener stopped during recovery')
        if all(value.epoch != before.epoch for value, before in zip(latest, initial)):
            return
        await asyncio.sleep(.05)
    raise AssertionError('Listeners did not resume with a fresh source epoch')


async def main(mode, origin, stream):
    if not os.getenv('KUBECONFIG') or CONTEXT not in kubectl('config', 'current-context'):
        raise RuntimeError('Set KUBECONFIG to the dedicated demo kubeconfig')
    health_port = free_port()
    with Path('/tmp/websdr-demo-health-forward.log').open('w') as log:
        forward = subprocess.Popen(['kubectl', '--context', CONTEXT, 'port-forward',
            'service/sdr-server', f'{health_port}:8081'], stdout=log, stderr=log)
        try:
            async with httpx.AsyncClient() as http:
                health_url = f'http://127.0.0.1:{health_port}/health'
                await status(http, health_url, lambda info: info['mode'] == 'idle')
                if stream == 'subbands':
                    bands = (await http.get(origin+'/bands')).json()['bands']
                    assert len(bands) == 5
                    paths = [f'/iq?band={band["id"]}' for band in bands]
                    sample_rate = 128000
                else:
                    paths = ['/iq?band=full']*5
                    sample_rate = 520834
                sockets = [await connect(origin.replace('http', 'ws')+path) for path in paths]
                readers = []
                try:
                    first = await asyncio.gather(*(asyncio.wait_for(socket.recv(), 20) for socket in sockets))
                    metadata = [validate_frame(frame) for frame in first]
                    assert all(info.sample_rate == sample_rate for info in metadata)
                    peaks = [0.0]*5
                    deadline = time.monotonic()+4
                    while time.monotonic() < deadline:
                        frames = await asyncio.gather(*(asyncio.wait_for(socket.recv(), 10) for socket in sockets))
                        for index, frame in enumerate(frames):
                            data = np.frombuffer(frame, np.int8, offset=32).reshape(-1, 2)
                            iq = data[:, 0].astype(np.float32)+1j*data[:, 1]
                            count = min(2048, len(iq))
                            power = np.abs(np.fft.fft(iq[:count]*np.hanning(count)))**2
                            peaks[index] = max(peaks[index], float(10*np.log10((power.max()+1)/(np.median(power)+1))))
                    assert min(peaks) > 15, peaks
                    print(f'Five {stream} listeners receive voice/CW, spectral contrast {[round(value, 1) for value in peaks]} dB', flush=True)
                    initial = restart_counts()
                    latest = metadata.copy()
                    async def consume(index, socket):
                        while True:
                            latest[index] = validate_frame(await socket.recv())
                    readers = [asyncio.create_task(consume(index, socket)) for index, socket in enumerate(sockets)]
                    if mode == 'synthetic':
                        # The automatic capture scenario reaches its scheduled transport stall at 34 s.
                        await wait_new_epochs(latest, metadata, readers, 60)
                        counts = restart_counts()
                        assert counts['sdr-server'] == initial['sdr-server']+1, counts
                        assert counts['frontend'] == initial['frontend'], counts
                        assert counts['backend-controller'] == initial['backend-controller'], counts
                        print('Scheduled stall restarted only the source and resumed a fresh epoch', flush=True)
                    else:
                        # Replacing only the emulator exercises actual network-IIO recovery.
                        await asyncio.to_thread(kubectl, 'rollout', 'restart', 'deployment/iio-emulator')
                        await asyncio.to_thread(kubectl, 'rollout', 'status', 'deployment/iio-emulator', '--timeout=180s')
                        await wait_new_epochs(latest, metadata, readers, 60)
                        counts = restart_counts()
                        assert counts['frontend'] == initial['frontend'], counts
                        assert counts['backend-controller'] == initial['backend-controller'], counts
                        print('Emulator replacement recovered through GNU Radio with a fresh source epoch', flush=True)
                finally:
                    for reader in readers:
                        reader.cancel()
                    await asyncio.gather(*readers, return_exceptions=True)
                    await asyncio.gather(*(socket.close() for socket in sockets))
                idle = await status(http, health_url, lambda info: info['mode'] == 'idle')
                assert not idle['capture_active'] and idle['subscribers'] == 0
                async with connect(origin.replace('http', 'ws')+paths[0]) as socket:
                    info = validate_frame(await asyncio.wait_for(socket.recv(), 20))
                    assert info.sample_rate == sample_rate
                print(f'PASS: Caddy WebSocket, {stream}, capture idle/wake and source recovery', flush=True)
        finally:
            forward.terminate()
            forward.wait(timeout=10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['synthetic', 'iio'], required=True)
    parser.add_argument('--stream', choices=['full', 'subbands'], required=True,
                        help='Receive selection to verify; subbands require feat/iq-subbands')
    parser.add_argument('--origin', default='http://127.0.0.1:18080')
    args = parser.parse_args()
    asyncio.run(main(args.mode, args.origin, args.stream))
