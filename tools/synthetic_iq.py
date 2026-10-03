"""Demand-driven deterministic I/Q source; uses the production capture lifecycle."""
import argparse
import signal
import threading
import time
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
    def __init__(self, publisher, rate, center, frame_samples=8192, stall_file=None):
        self.publisher, self.rate, self.frame_samples = publisher, rate, frame_samples
        self.stall_file = stall_file
        self.stopped = threading.Event()
        publisher.configure(Packetizer(rate, center, frame_samples))
        self.thread = threading.Thread(target=self.run, name='synthetic-capture', daemon=True)

    def start(self):
        self.thread.start()

    def run(self):
        position = 0
        deadline = time.monotonic()
        while not self.stopped.is_set():
            if self.stall_file is not None and self.stall_file.exists():
                self.stopped.wait(.05)
                deadline = time.monotonic()
                continue
            sample_time = np.arange(position, position+self.frame_samples)/self.rate
            samples = (0.30*np.exp(2j*np.pi*1000*sample_time) +
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
    args = parser.parse_args()
    health = StreamHealth()
    publisher = Publisher(args.address, health)
    controller = CaptureController(lambda: SyntheticCapture(publisher, args.rate, args.center,
                                     stall_file=args.stall_file), SyntheticPower(), publisher,
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
        controller.close()
        health.close()
        publisher.close()


if __name__ == '__main__':
    main()
