"""Demand-driven deterministic I/Q source; uses the production capture lifecycle."""
import argparse
import signal
import threading
import time
from contextlib import ExitStack
from pathlib import Path
import numpy as np
from iq_publisher import Packetizer, Publisher
from stream_health import StreamHealth
from capture_control import CaptureController


class SyntheticPower:
    state = 'simulated-sleep'

    def sleep(self):
        self.state = 'simulated-sleep'

    def wake(self):
        self.state = 'simulated-awake'


class SyntheticCapture:
    def __init__(self, publisher, rate, center, frame_samples=8192, stall_file=None, drift=0, mute_primary_file=None,
                 scenario=None, scenario_config=None):
        self.publisher, self.rate, self.frame_samples = publisher, rate, frame_samples
        self.stall_file = stall_file
        self.drift = drift
        self.mute_primary_file = mute_primary_file
        self.scenario = None
        if scenario and scenario != 'tones':
            from signal_scenarios import Scenario
            self.scenario = Scenario(scenario, rate, scenario_config)
        self.stopped = threading.Event()
        publisher.configure(Packetizer(rate, center, frame_samples))
        self.thread = threading.Thread(target=self.run, name='synthetic-capture', daemon=True)

    def start(self):
        self.thread.start()

    def run(self):
        position = 0
        deadline = time.monotonic()
        started = deadline
        while not self.stopped.is_set():
            if ((self.stall_file is not None and self.stall_file.exists()) or
                    (self.scenario is not None and self.scenario.stalled(time.monotonic()-started))):
                self.stopped.wait(.05)
                deadline = time.monotonic()
                if self.scenario is not None:
                    position = max(position, int((deadline-started)*self.rate)//self.frame_samples*self.frame_samples)
                continue
            if self.scenario is not None:
                samples = self.scenario.render(position, self.frame_samples)
            else:
                # Calibration tones keep frequency/rejection regression checks precise.
                sample_time = np.arange(position, position+self.frame_samples)/self.rate
                primary = 0 if self.mute_primary_file is not None and self.mute_primary_file.exists() else .30
                samples = (primary*np.exp(2j*np.pi*(1000*sample_time + .5*self.drift*sample_time**2)) +
                           0.20*np.exp(2j*np.pi*31000*sample_time) +
                           0.15*np.exp(-2j*np.pi*21000*sample_time)).astype(np.complex64)
            self.publisher.push(samples)
            position += self.frame_samples
            deadline += self.frame_samples/self.rate
            self.stopped.wait(max(0, deadline-time.monotonic()))

    def close(self):
        self.stopped.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2)
        if self.thread.is_alive():
            raise RuntimeError('Synthetic capture did not stop')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--address', default='tcp://127.0.0.1:5000')
    parser.add_argument('--rate', type=int, default=520834)
    parser.add_argument('--center', type=float, default=739700000)
    parser.add_argument('--health-port', type=int)
    parser.add_argument('--idle-seconds', type=float, default=10)
    parser.add_argument('--stall-file', type=Path)
    parser.add_argument('--drift-hz-per-second', type=float, default=0)
    parser.add_argument('--mute-primary-file', type=Path)
    parser.add_argument('--scenario', default='tones', help='tones, clean, automatic, fading, drift, squelch, qrm or recovery')
    parser.add_argument('--scenario-config', type=Path, help='Custom JSON station/scenario catalog')
    args = parser.parse_args()
    health = StreamHealth()
    publisher = Publisher(args.address, health)
    controller = CaptureController(lambda: SyntheticCapture(publisher, args.rate, args.center,
                                     stall_file=args.stall_file, drift=args.drift_hz_per_second,
                                     mute_primary_file=args.mute_primary_file, scenario=args.scenario,
                                     scenario_config=args.scenario_config), SyntheticPower(), publisher,
                                     health, args.idle_seconds)
    if args.health_port is not None:
        health.serve(args.health_port)
    stopped = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stopped.set())
    try:
        while not stopped.is_set():
            publisher.service()
            controller.tick()
            stopped.wait(.005 if controller.capture is not None else .1)
    finally:
        with ExitStack() as cleanup:
            cleanup.callback(publisher.close)
            cleanup.callback(health.close)
            cleanup.callback(controller.close)


if __name__ == '__main__':
    main()
