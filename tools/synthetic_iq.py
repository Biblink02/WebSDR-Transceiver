"""Deterministic multi-tone source for local receiver tests, without SDR hardware."""
import argparse
import asyncio
import signal
from pathlib import Path
import numpy as np
import zmq.asyncio
from iq_publisher import Packetizer
from stream_health import StreamHealth


async def run(address, rate=520834, center=739700000, frame_samples=8192,
              health_port=None, stall_file=None):
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.PUB)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.SNDHWM, 4)
    socket.bind(address)
    packetizer = Packetizer(rate, center, frame_samples)
    health = StreamHealth()
    if health_port is not None:
        health.serve(health_port)
    position = 0
    loop = asyncio.get_running_loop()
    deadline = loop.time()
    task = asyncio.current_task()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, task.cancel)
    try:
        while True:
            if stall_file is not None and stall_file.exists():
                await asyncio.sleep(0.05)
                deadline = loop.time()
                continue
            time = np.arange(position, position+frame_samples)/rate
            samples = (0.30*np.exp(2j*np.pi*1000*time) +
                       0.20*np.exp(2j*np.pi*31000*time) +
                       0.15*np.exp(-2j*np.pi*21000*time)).astype(np.complex64)
            health.source_progress()
            for frame in packetizer.push(samples):
                await socket.send(frame, flags=zmq.DONTWAIT)
                health.published()
            position += frame_samples
            deadline += frame_samples/rate
            await asyncio.sleep(max(0, deadline-asyncio.get_running_loop().time()))
    finally:
        health.close()
        socket.close(linger=0)
        context.term()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--address', default='tcp://127.0.0.1:5000')
    parser.add_argument('--rate', type=int, default=520834)
    parser.add_argument('--center', type=float, default=739700000)
    parser.add_argument('--health-port', type=int)
    parser.add_argument('--stall-file', type=Path,
                        help='Pause capture/publication while this test file exists')
    args = parser.parse_args()
    try:
        asyncio.run(run(args.address, args.rate, args.center,
                        health_port=args.health_port, stall_file=args.stall_file))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass


if __name__ == '__main__':
    main()
