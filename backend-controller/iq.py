"""Stateless packed-I/Q fanout: one upstream subscription, bounded client queues."""
import asyncio
import time
from collections import Counter
import zmq
from iq_protocol import MAX_FRAME_BYTES, validate_frame


class IQDistributor:
    def __init__(self, context, address, queue_size=4):
        if not 1 <= queue_size <= 64:
            raise ValueError('I/Q queue size must be in [1, 64]')
        self.context, self.address, self.queue_size = context, address, queue_size
        self.clients: set[asyncio.Queue] = set()
        self.last_packet = None
        self.info = None
        self.counters = Counter()
        self.socket = None

    def subscribe(self):
        queue = asyncio.Queue(maxsize=self.queue_size)
        self.clients.add(queue)
        return queue

    def unsubscribe(self, queue):
        self.clients.discard(queue)

    def ingest(self, data):
        try:
            info = validate_frame(data)
        except ValueError:
            self.counters['malformed'] += 1
            return
        gap = (self.info is not None and
               (info.epoch != self.info.epoch or info.sample_rate != self.info.sample_rate
                or info.center_freq != self.info.center_freq
                or info.sequence != ((self.info.sequence + 1) & 0xffffffff)))
        if gap:
            self.counters['discontinuities'] += 1
        for queue in tuple(self.clients):
            if gap:
                while not queue.empty():
                    queue.get_nowait()
                    self.counters['client_dropped'] += 1
            if queue.full():
                queue.get_nowait()
                self.counters['client_dropped'] += 1
            queue.put_nowait(data)
        self.info = info
        self.last_packet = time.monotonic()
        self.counters['frames'] += 1

    async def run(self):
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt(zmq.SUBSCRIBE, b'')
        self.socket.setsockopt(zmq.RCVHWM, 4)
        self.socket.setsockopt(zmq.MAXMSGSIZE, MAX_FRAME_BYTES)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.RECONNECT_IVL, 250)
        self.socket.setsockopt(zmq.RECONNECT_IVL_MAX, 2000)
        self.socket.connect(self.address)
        try:
            while True:
                self.ingest(await self.socket.recv())
        finally:
            self.socket.close(linger=0)

    def diagnostics(self):
        return {'clients': len(self.clients), 'sample_rate': self.info.sample_rate if self.info else None,
                'center_freq': self.info.center_freq if self.info else None,
                'epoch': self.info.epoch if self.info else None, 'format': 'signed-iq8', 'version': 1,
                'packet_age_seconds': time.monotonic() - self.last_packet if self.last_packet else None,
                'counters': dict(self.counters)}
