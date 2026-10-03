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
        self.demand = asyncio.Event()
        self.idle = asyncio.Event()
        self.idle.set()

    def subscribe(self):
        queue = asyncio.Queue(maxsize=self.queue_size)
        self.clients.add(queue)
        self.idle.clear()
        self.demand.set()
        return queue

    def unsubscribe(self, queue):
        self.clients.discard(queue)
        if not self.clients:
            self.demand.clear()
            self.idle.set()

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
        while True:
            await self.demand.wait()
            if not self.clients:
                continue
            self.socket = self.context.socket(zmq.SUB)
            for option, value in [(zmq.RCVHWM, 4), (zmq.MAXMSGSIZE, MAX_FRAME_BYTES),
                                  (zmq.LINGER, 0), (zmq.RECONNECT_IVL, 250),
                                  (zmq.RECONNECT_IVL_MAX, 2000), (zmq.HEARTBEAT_IVL, 1000),
                                  (zmq.HEARTBEAT_TIMEOUT, 5000), (zmq.HEARTBEAT_TTL, 5000)]:
                self.socket.setsockopt(option, value)
            self.socket.setsockopt(zmq.SUBSCRIBE, b'')
            self.socket.connect(self.address)
            idle = asyncio.create_task(self.idle.wait())
            receive = None
            try:
                while self.clients:
                    receive = asyncio.ensure_future(self.socket.recv())
                    done, _ = await asyncio.wait((receive, idle), return_when=asyncio.FIRST_COMPLETED)
                    if idle in done:
                        break
                    self.ingest(receive.result())
            finally:
                for task in (receive, idle):
                    if task is not None:
                        task.cancel()
                await asyncio.gather(*(t for t in (receive, idle) if t is not None), return_exceptions=True)
                self.socket.close(linger=0)
                self.socket = None
                self.last_packet = None

    def diagnostics(self):
        return {'clients': len(self.clients), 'receiving': self.socket is not None,
                'sample_rate': self.info.sample_rate if self.info else None,
                'center_freq': self.info.center_freq if self.info else None,
                'epoch': self.info.epoch if self.info else None, 'format': 'signed-iq8', 'version': 1,
                'packet_age_seconds': time.monotonic() - self.last_packet if self.last_packet else None,
                'counters': dict(self.counters)}
