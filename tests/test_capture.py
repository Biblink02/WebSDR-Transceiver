import asyncio
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from websockets.asyncio.client import connect
from capture_control import CaptureController, PlutoPower
from iq_protocol import validate_frame
from stream_health import StreamHealth
from tests.test_backend import backend, free_port

ROOT = Path(__file__).resolve().parents[1]


def test_capture_stops_before_pluto_sleep_and_wakes_once_for_all_replicas():
    now = [10.0]
    events = []
    class Power:
        state = 'sleep'
        def wake(self): events.append('wake'); self.state = 'awake'
        def sleep(self): events.append('sleep'); self.state = 'sleep'
    class Capture:
        def start(self): events.append('start')
        def close(self): events.append('release')
    publisher = SimpleNamespace(subscribers=0, counters={}, discard_pending=lambda: events.append('discard'))
    health = StreamHealth(clock=lambda: now[0])
    controller = CaptureController(Capture, Power(), publisher, health, 2, clock=lambda: now[0])
    controller.tick()
    assert health.status()[0] and controller.capture is None
    publisher.subscribers = 2; controller.tick(); controller.tick()
    assert events.count('wake') == events.count('start') == 1
    health.source_progress(); health.published(); assert health.status()[0]
    publisher.subscribers = 1; now[0] += 3; controller.tick()
    assert controller.capture is not None
    publisher.subscribers = 0; controller.tick(); now[0] += 1; controller.tick()
    assert controller.capture is not None
    publisher.subscribers = 1; controller.tick()
    assert controller.starts == 1
    publisher.subscribers = 0; controller.tick(); now[0] += 2; controller.tick()
    assert controller.capture is None and controller.stops == 1
    assert events[-3:] == ['release', 'discard', 'sleep']
    assert health.status()[0]
    publisher.subscribers = 1; controller.tick()
    assert controller.starts == 2
    controller.close()


def test_pluto_ensm_sleep_and_original_mode_restore_through_libiio():
    writes = []
    class Attribute:
        current = 'rx'
        @property
        def value(self): return self.current
        @value.setter
        def value(self, value): self.current = value; writes.append(value)
    mode = Attribute()
    context = SimpleNamespace(find_device=lambda name: SimpleNamespace(attrs={'ensm_mode': mode}))
    power = PlutoPower('ip:test', lambda uri: context)
    power.sleep(); assert power.state == 'sleep'
    power.wake(); assert power.state == 'awake'
    assert writes == ['sleep', 'rx']


def test_idle_is_healthy_when_disconnected_hardware_cannot_sleep():
    class Power:
        state = 'unknown'
        def sleep(self): raise OSError('IIO unavailable')
    publisher = SimpleNamespace(subscribers=0, counters={})
    health = StreamHealth()
    controller = CaptureController(lambda: None, Power(), publisher, health)
    controller.tick()
    assert health.status()[0]
    assert controller.diagnostics()['last_error'] == 'IIO unavailable'


def test_warmup_is_bounded_and_streaming_stalls_remain_unhealthy():
    now = [0.0]
    capture = SimpleNamespace(start=lambda: None, close=lambda: None)
    power = SimpleNamespace(state='awake', wake=lambda: None, sleep=lambda: None)
    publisher = SimpleNamespace(subscribers=1, counters={}, discard_pending=lambda: None)
    health = StreamHealth(clock=lambda: now[0])
    controller = CaptureController(lambda: capture, power, publisher, health, clock=lambda: now[0])
    controller.tick(); now[0] = 20; controller.tick()
    assert health.mode == 'waking' and health.status()[0]
    now[0] = 31; controller.tick(); assert not health.status()[0]
    health.source_progress(); health.published(); controller.tick()
    assert health.mode == 'streaming' and health.status()[0]
    now[0] += 3; controller.tick(); assert not health.status()[0]
    controller.close()


def test_disconnecting_during_warmup_keeps_the_original_startup_deadline():
    now = [10.0]
    capture = SimpleNamespace(start=lambda: None, close=lambda: None)
    power = SimpleNamespace(state='awake', wake=lambda: None, sleep=lambda: None)
    publisher = SimpleNamespace(subscribers=1, counters={}, discard_pending=lambda: None)
    health = StreamHealth(clock=lambda: now[0])
    controller = CaptureController(lambda: capture, power, publisher, health, 60, clock=lambda: now[0])
    controller.tick()
    now[0] += 1
    publisher.subscribers = 0
    controller.tick()
    assert health.status()[0], 'A disconnect must not turn an unfinished startup into a stall'
    now[0] += 1
    publisher.subscribers = 1
    controller.tick()
    assert health.mode == 'waking' and health.status()[0]
    now[0] = 41
    controller.tick()
    assert not health.status()[0], 'Reconnecting must not restart the 30-second warmup allowance'
    health.source_progress(); health.published(); controller.tick()
    assert health.mode == 'streaming' and health.status()[0]
    controller.close()


def test_slow_failed_start_backs_off_after_failure_and_returns_to_sleep():
    now = [10.0]
    events = []
    class Power:
        state = 'sleep'
        def wake(self): self.state = 'awake'; events.append('wake')
        def sleep(self): self.state = 'sleep'; events.append('sleep')
    def fail():
        now[0] += 8
        raise OSError('IIO startup failed')
    publisher = SimpleNamespace(subscribers=1, counters={}, discard_pending=lambda: None)
    health = StreamHealth(clock=lambda: now[0])
    controller = CaptureController(fail, Power(), publisher, health, clock=lambda: now[0])
    controller.tick()
    assert controller.power.state == 'sleep'
    assert controller.last_error == 'IIO startup failed'
    controller.tick()
    assert events.count('wake') == 1, 'A slow startup must still have a retry cooldown'
    now[0] += 5
    controller.tick()
    assert events.count('wake') == 2


def test_temporary_sleep_failure_is_retried_without_any_viewer():
    now = [10.0]
    class Power:
        state = 'awake'
        attempts = 0
        def sleep(self):
            self.attempts += 1
            if self.attempts == 1: raise OSError('Temporary IIO failure')
            self.state = 'sleep'
    publisher = SimpleNamespace(subscribers=0, counters={})
    health = StreamHealth(clock=lambda: now[0])
    controller = CaptureController(lambda: None, Power(), publisher, health, clock=lambda: now[0])
    controller.tick(); controller.tick()
    assert controller.power.attempts == 1 and health.status()[0]
    now[0] += 5
    controller.tick()
    assert controller.power.attempts == 2 and controller.power.state == 'sleep'
    assert controller.last_error is None


@pytest.mark.parametrize('fail_start', [False, True])
def test_failed_release_never_sleeps_or_starts_a_second_native_graph(fail_start):
    now = [10.0]
    events = []
    class Capture:
        attempts = 0
        def start(self):
            events.append('start')
            if fail_start: raise OSError('Start failed after acquiring IIO buffer')
        def close(self):
            events.append('release')
            self.attempts += 1
            if self.attempts == 1: raise OSError('Native graph still running')
    capture = Capture()
    power = SimpleNamespace(state='awake', wake=lambda: events.append('wake'),
                            sleep=lambda: events.append('sleep'))
    publisher = SimpleNamespace(subscribers=1, counters={}, discard_pending=lambda: events.append('discard'))
    health = StreamHealth(clock=lambda: now[0])
    controller = CaptureController(lambda: capture, power, publisher, health, 0, clock=lambda: now[0])
    controller.tick()
    if not fail_start:
        publisher.subscribers = 0
        controller.tick()
        publisher.subscribers = 1
    assert controller.capture is capture and health.mode == 'fault'
    assert 'sleep' not in events
    controller.tick()
    assert events.count('start') == 1 and events.count('release') == 1
    now[0] += 5
    controller.tick()
    assert controller.capture is None and events.count('release') == 2
    assert controller.stops == int(not fail_start)
    assert events.count('start') == 1
    publisher.subscribers = 0
    controller.tick()
    assert events[-1] == 'sleep'


def test_shutdown_release_error_still_closes_health_and_publisher(monkeypatch):
    import synthetic_iq
    events = []
    health = SimpleNamespace(serve=lambda _: None, close=lambda: events.append('health'))
    publisher = SimpleNamespace(close=lambda: events.append('publisher'))
    def failed_close():
        events.append('capture')
        raise OSError('Release failed')
    monkeypatch.setattr(sys, 'argv', ['synthetic_iq.py'])
    monkeypatch.setattr(synthetic_iq, 'StreamHealth', lambda: health)
    monkeypatch.setattr(synthetic_iq, 'Publisher', lambda *_: publisher)
    monkeypatch.setattr(synthetic_iq, 'CaptureController', lambda *_: SimpleNamespace(close=failed_close))
    monkeypatch.setattr(synthetic_iq.signal, 'signal', lambda *_: None)
    monkeypatch.setattr(synthetic_iq.threading, 'Event', lambda: SimpleNamespace(is_set=lambda: True))
    with pytest.raises(OSError, match='Release failed'):
        synthetic_iq.main()
    assert events == ['capture', 'health', 'publisher']


@pytest.mark.asyncio
async def test_replica_crashes_release_xpub_demand_without_stopping_other_viewers(tmp_path):
    iq_port, health_port = free_port(), free_port()
    processes = []
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join(str(ROOT/p) for p in ['shared', 'sdr-server'])}
    with (tmp_path/'crash-source.log').open('w') as log:
        source = subprocess.Popen([sys.executable, str(ROOT/'tools/synthetic_iq.py'),
            '--address', f'tcp://127.0.0.1:{iq_port}', '--health-port', str(health_port),
            '--idle-seconds', '.1'], env=env, stdout=log, stderr=log)
        try:
            async with httpx.AsyncClient() as http, \
                    backend(free_port(), iq_port, tmp_path, processes) as first, \
                    backend(free_port(), iq_port, tmp_path, processes) as second:
                a = await connect(first.replace('http', 'ws')+'/iq')
                b = await connect(second.replace('http', 'ws')+'/iq')
                try:
                    await asyncio.wait_for(asyncio.gather(a.recv(), b.recv()), 5)
                    url = f'http://127.0.0.1:{health_port}/health'
                    await wait_status(http, url, lambda s: s['subscribers'] == 2)
                    processes[0].kill(); processes[0].wait(timeout=5)
                    remaining = await wait_status(http, url, lambda s: s['subscribers'] == 1)
                    assert remaining['capture_active'] and remaining['capture_starts'] == 1
                    assert validate_frame(await asyncio.wait_for(b.recv(), 2)).count > 0
                    processes[1].kill(); processes[1].wait(timeout=5)
                    idle = await wait_status(http, url, lambda s: s['mode'] == 'idle')
                    assert idle['subscribers'] == 0 and not idle['capture_active']
                finally:
                    await a.close(); await b.close()
        finally:
            source.terminate(); source.wait(timeout=10)


async def wait_status(http, url, predicate):
    data = {}
    for _ in range(150):
        try:
            response = await http.get(url)
            data = response.json()
            if predicate(data): return data
        except httpx.ConnectError: pass
        await asyncio.sleep(.05)
    raise AssertionError(f'Unexpected source state: {data}')


@pytest.mark.asyncio
async def test_real_replicas_wake_source_only_for_viewers_release_last_and_resume(tmp_path):
    iq_port, health_port = free_port(), free_port()
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join(str(ROOT/p) for p in ['shared', 'sdr-server'])}
    with (tmp_path/'source.log').open('w') as log:
        source = subprocess.Popen([sys.executable, str(ROOT/'tools/synthetic_iq.py'),
            '--address', f'tcp://127.0.0.1:{iq_port}', '--health-port', str(health_port),
            '--idle-seconds', '.1'], env=env, stdout=log, stderr=log)
        try:
            async with httpx.AsyncClient() as http, \
                    backend(free_port(), iq_port, tmp_path) as first, \
                    backend(free_port(), iq_port, tmp_path) as second:
                health_url = f'http://127.0.0.1:{health_port}/health'
                idle = await wait_status(http, health_url, lambda state: state['mode'] == 'idle')
                assert idle['capture_starts'] == 0 and idle['subscribers'] == 0
                assert (await http.get(first+'/ready')).json()['status'] == 'idle'
                a = await connect(first.replace('http','ws')+'/iq')
                b = await connect(second.replace('http','ws')+'/iq')
                try:
                    frames = await asyncio.wait_for(asyncio.gather(a.recv(), b.recv()), 5)
                    old_epoch = validate_frame(frames[0]).epoch
                    assert old_epoch == validate_frame(frames[1]).epoch
                    active = await wait_status(http, health_url, lambda state: state['subscribers'] == 2)
                    assert active['capture_starts'] == 1 and active['capture_active']
                    await a.close()
                    await wait_status(http, health_url, lambda state: state['subscribers'] == 1)
                    await asyncio.sleep(.2)
                    assert (await http.get(health_url)).json()['capture_active']
                    await b.close()
                    idle = await wait_status(http, health_url, lambda state: not state['capture_active'])
                    assert idle['subscribers'] == 0 and idle['capture_stops'] == 1
                    assert idle['power_state'] == 'simulated-sleep'
                    published = idle['counters']['published']
                    await asyncio.sleep(.2)
                    assert (await http.get(health_url)).json()['counters']['published'] == published
                    assert not (await http.get(first+'/stream-info')).json()['receiving']
                    async with connect(first.replace('http','ws')+'/iq') as resumed:
                        info = validate_frame(await asyncio.wait_for(resumed.recv(), 5))
                        assert info.epoch != old_epoch
                        active = (await http.get(health_url)).json()
                        assert active['capture_starts'] == 2
                finally:
                    await a.close(); await b.close()
        finally:
            source.terminate(); source.wait(timeout=10)
