"""Admission under concurrent handshakes, cancellation, and real WebSocket load."""
import asyncio
import os
import subprocess
import sys

import httpx
import pytest
import yaml
import zmq.asyncio
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from iq import FULL_BAND_CAPACITY_CLOSE_CODE, FullBandLimitReached, IQDistributor
from iq_protocol import validate_frame
from subbands import FULL_BAND
from tests.test_backend import ROOT, backend, free_port
from tests.test_stream import frame


def test_full_quota_releases_exactly_once_and_zero_preserves_idle_and_subbands():
    distributor = IQDistributor(None, 'unused', full_band_max_clients=1)
    first = distributor.subscribe(FULL_BAND)
    with pytest.raises(FullBandLimitReached): distributor.subscribe(FULL_BAND)
    assert len(distributor.clients) == 1
    subband = distributor.subscribe(0)
    distributor.unsubscribe(first)
    second = distributor.subscribe(FULL_BAND)
    distributor.unsubscribe(first)  # Repeated cleanup must not release second's slot.
    with pytest.raises(FullBandLimitReached): distributor.subscribe(FULL_BAND)
    assert distributor.diagnostics()['full_band_clients'] == 1
    distributor.unsubscribe(second)
    distributor.unsubscribe(subband)
    disabled = IQDistributor(None, 'unused', full_band_max_clients=0)
    with pytest.raises(FullBandLimitReached): disabled.subscribe(FULL_BAND)
    assert not disabled.clients and not disabled.demand.is_set() and disabled.idle.is_set()
    queue = disabled.subscribe(0)
    disabled.ingest(frame())
    assert validate_frame(queue.get_nowait()).sample_rate == 128000
    disabled.unsubscribe(queue)
    for invalid in [-1, 1.5, True, '2', None]:
        with pytest.raises(ValueError): IQDistributor(None, 'unused', full_band_max_clients=invalid)


def test_limit_config_validates_yaml_and_environment_override(tmp_path):
    config = tmp_path/'limit.yaml'
    env = {**os.environ, 'CONFIG_PATH': str(config), 'PYTHONPATH': str(ROOT/'backend-controller')}
    env.pop('IQ_FULL_BAND_MAX_CLIENTS', None)
    command = [sys.executable, '-c', 'import config; print(config.IQ_FULL_BAND_MAX_CLIENTS)']
    for value in [0, 1, 12]:
        config.write_text(yaml.safe_dump({'iq_full_band_max_clients': value}))
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        assert result.returncode == 0 and result.stdout.strip() == str(value), result.stderr
    for value in [-1, 1.5, True, None, 'unlimited']:
        config.write_text(yaml.safe_dump({'iq_full_band_max_clients': value}))
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        assert result.returncode != 0 and 'must be a nonnegative integer' in result.stderr
    config.write_text('iq_full_band_max_clients: 1\n')
    result = subprocess.run(command, env={**env, 'IQ_FULL_BAND_MAX_CLIENTS': '3'}, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout.strip() == '3'


@pytest.mark.asyncio
async def test_pending_handshake_reserves_capacity_and_cancellation_or_failure_releases_it(monkeypatch):
    import backend_controller
    distributor = IQDistributor(None, 'unused', full_band_max_clients=1)
    monkeypatch.setattr(backend_controller.app.state, 'iq', distributor, raising=False)
    class Socket:
        query_params = {'band': FULL_BAND}
        def __init__(self, pending=False, failing=False):
            self.pending, self.failing = pending, failing
            self.entered, self.release = asyncio.Event(), asyncio.Event()
            self.closed = None
        async def accept(self):
            self.entered.set()
            if self.failing: raise RuntimeError('Handshake failed')
            if self.pending: await self.release.wait()
        async def close(self, code=1000, **kwargs): self.closed = code
    first, second = Socket(pending=True), Socket()
    task = asyncio.create_task(backend_controller.iq_socket(first))
    try:
        await asyncio.wait_for(first.entered.wait(), 1)
        await backend_controller.iq_socket(second)
        assert second.closed == FULL_BAND_CAPACITY_CLOSE_CODE
        assert distributor.diagnostics()['full_band_clients'] == 1
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert not distributor.clients and not distributor.demand.is_set()
    await backend_controller.iq_socket(Socket(failing=True))
    assert not distributor.clients and distributor.idle.is_set()


@pytest.mark.asyncio
async def test_concurrent_websocket_admission_is_per_replica_and_slots_are_reusable(tmp_path):
    context = zmq.asyncio.Context()
    publisher = context.socket(zmq.XPUB)
    publisher.setsockopt(zmq.LINGER, 0)
    publisher.setsockopt(zmq.XPUB_VERBOSER, 1)
    iq_port = publisher.bind_to_random_port('tcp://127.0.0.1')
    sockets = []
    try:
        async with (backend(free_port(), iq_port, tmp_path, env_overrides={'IQ_FULL_BAND_MAX_CLIENTS': '1'}) as first,
                    backend(free_port(), iq_port, tmp_path, env_overrides={'IQ_FULL_BAND_MAX_CLIENTS': '1'}) as second,
                    httpx.AsyncClient() as http):
            url = first.replace('http', 'ws')+'/iq?band=full'
            sockets = await asyncio.gather(*(connect(url) for _ in range(12)))
            assert await asyncio.wait_for(publisher.recv(), 2) == b'\x01'
            packet = frame()
            await publisher.send(packet)
            results = await asyncio.gather(*(asyncio.wait_for(ws.recv(), 2) for ws in sockets), return_exceptions=True)
            assert results.count(packet) == 1
            rejected = [result for result in results if isinstance(result, ConnectionClosed)]
            assert len(rejected) == 11 and all(result.rcvd.code == FULL_BAND_CAPACITY_CLOSE_CODE for result in rejected)
            state = (await http.get(first+'/stream-info')).json()
            assert state['full_band_max_clients'] == state['full_band_clients'] == state['clients'] == 1
            assert state['counters']['full_band_rejected'] == 11
            # A saturated replica must not consume another replica's allowance.
            async with connect(second.replace('http', 'ws')+'/iq?band=full') as other:
                assert await asyncio.wait_for(publisher.recv(), 2) == b'\x01'
                async with connect(first.replace('http', 'ws')+'/iq?band=0') as subband:
                    packet = frame(sequence=1)
                    await publisher.send(packet)
                    assert await asyncio.wait_for(other.recv(), 2) == packet
                    assert validate_frame(await asyncio.wait_for(subband.recv(), 2)).sample_rate == 128000
                await asyncio.gather(*(ws.close() for ws in sockets))
                assert await asyncio.wait_for(publisher.recv(), 2) == b'\x00'
                for _ in range(100):
                    state = (await http.get(first+'/stream-info')).json()
                    if not state['receiving']: break
                    await asyncio.sleep(.02)
                assert state['clients'] == state['full_band_clients'] == 0
                async with connect(url) as replacement:
                    assert await asyncio.wait_for(publisher.recv(), 2) == b'\x01'
                    packet = frame(sequence=2)
                    await publisher.send(packet)
                    assert await asyncio.wait_for(replacement.recv(), 2) == packet
    finally:
        await asyncio.gather(*(ws.close() for ws in sockets), return_exceptions=True)
        publisher.close(linger=0)
        context.term()


@pytest.mark.asyncio
async def test_disabled_full_spectrum_rejects_without_waking_source(tmp_path):
    context = zmq.asyncio.Context()
    publisher = context.socket(zmq.XPUB)
    publisher.setsockopt(zmq.LINGER, 0)
    iq_port = publisher.bind_to_random_port('tcp://127.0.0.1')
    try:
        async with backend(free_port(), iq_port, tmp_path, env_overrides={'IQ_FULL_BAND_MAX_CLIENTS': '0'}) as receiver:
            async with connect(receiver.replace('http', 'ws')+'/iq?band=full') as ws:
                with pytest.raises(ConnectionClosed) as error: await ws.recv()
                assert error.value.rcvd.code == FULL_BAND_CAPACITY_CLOSE_CODE
            async with httpx.AsyncClient() as http:
                state = (await http.get(receiver+'/stream-info')).json()
                assert state['clients'] == state['full_band_clients'] == state['full_band_max_clients'] == 0
                assert not state['receiving'] and (await http.get(receiver+'/ready')).status_code == 200
            assert not await publisher.poll(100)
    finally:
        publisher.close(linger=0)
        context.term()
