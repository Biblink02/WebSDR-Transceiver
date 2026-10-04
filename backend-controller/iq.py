"""Shared native I/Q subbands: one upstream subscription, bounded client queues."""
import asyncio
import time
from collections import Counter
import zmq
from iq_protocol import MAX_FRAME_BYTES, validate_frame
from subbands import FULL_BAND, BandPlan, NativeChannelizer


class IQDistributor:
    def __init__(self, context, address, queue_size=4, *, input_rate=520834, center=739700000,
                 view_low=739500000, view_high=739900000, subband_rate=128000):
        if not 1 <= queue_size <= 64:
            raise ValueError('I/Q queue size must be in [1, 64]')
        self.context, self.address, self.queue_size = context, address, queue_size
        self.clients: set[asyncio.Queue] = set()
        self.client_bands = {}
        self.channels = {}
        self.plan_args = (view_low, view_high, subband_rate)
        self.plan = BandPlan(input_rate, center, *self.plan_args)
        self.last_packet = None
        self.info = None
        self.counters = Counter()
        self.socket = None
        self.demand = asyncio.Event()
        self.idle = asyncio.Event()
        self.idle.set()

    def subscribe(self, band=None):
        band = self.plan.default if band is None else band
        self.plan.get_band(band)
        queue = asyncio.Queue(maxsize=self.queue_size)
        self.clients.add(queue)
        self.client_bands[queue] = band
        self.idle.clear()
        self.demand.set()
        return queue

    def unsubscribe(self, queue):
        self.clients.discard(queue)
        band = self.client_bands.pop(queue, None)
        if band not in self.client_bands.values() and band in self.channels:
            self.channels.pop(band).close()
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
            self.close_channels()
        if info.sample_rate != self.plan.input_rate or info.center_freq != self.plan.center:
            self.plan = BandPlan(info.sample_rate, info.center_freq, *self.plan_args)
        started = time.perf_counter()
        frames = {}
        for band_id in set(self.client_bands.values()):
            if band_id == FULL_BAND:
                frames[band_id] = data
                continue
            if band_id not in self.plan.bands:
                raise RuntimeError('Source metadata invalidated an active subband')
            if band_id not in self.channels:
                self.channels[band_id] = NativeChannelizer(info.sample_rate, info.center_freq, self.plan.bands[band_id])
            frames[band_id] = self.channels[band_id].process(data, info)
            self.counters['channel_frames'] += 1
        self.counters['processing_microseconds'] += round((time.perf_counter() - started) * 1000000)
        for queue in tuple(self.clients):
            if gap:
                while not queue.empty():
                    queue.get_nowait()
                    self.counters['client_dropped'] += 1
            frame = frames[self.client_bands[queue]]
            if frame is None:
                continue
            if queue.full():
                queue.get_nowait()
                self.counters['client_dropped'] += 1
            queue.put_nowait(frame)
            self.counters['delivered_bytes'] += len(frame)
        self.info = info
        self.last_packet = time.monotonic()
        self.counters['frames'] += 1

    def close_channels(self):
        for channel in self.channels.values():
            channel.close()
        self.channels.clear()

    async def run(self):
        while True:
            await self.demand.wait()
            if not self.clients:
                continue
            self.socket = self.context.socket(zmq.SUB)
            idle = None
            receive = None
            try:
                for option, value in [(zmq.RCVHWM, 4), (zmq.MAXMSGSIZE, MAX_FRAME_BYTES),
                                      (zmq.LINGER, 0), (zmq.RECONNECT_IVL, 250),
                                      (zmq.RECONNECT_IVL_MAX, 2000), (zmq.HEARTBEAT_IVL, 1000),
                                      (zmq.HEARTBEAT_TIMEOUT, 5000), (zmq.HEARTBEAT_TTL, 5000)]:
                    self.socket.setsockopt(option, value)
                self.socket.setsockopt(zmq.SUBSCRIBE, b'')
                self.socket.connect(self.address)
                idle = asyncio.create_task(self.idle.wait())
                while self.clients:
                    if receive is None:
                        receive = asyncio.ensure_future(self.socket.recv())
                    done, _ = await asyncio.wait((receive, idle), return_when=asyncio.FIRST_COMPLETED)
                    if idle in done:
                        if not self.clients:
                            break
                        # A viewer joined after the idle notification was queued.
                        # Re-arm it without dropping the live upstream connection.
                        idle = asyncio.create_task(self.idle.wait())
                    if receive in done:
                        data = receive.result()
                        receive = None
                        self.ingest(data)
            finally:
                for task in (receive, idle):
                    if task is not None:
                        task.cancel()
                try:
                    await asyncio.gather(*(t for t in (receive, idle) if t is not None), return_exceptions=True)
                finally:
                    # Shutdown can cancel run() a second time during the await.
                    # Socket closure must still precede Context.term().
                    self.socket.close(linger=0)
                    self.socket = None
                    self.close_channels()
                    self.info = None
                    self.last_packet = None

    def diagnostics(self):
        return {'clients': len(self.clients), 'active_bands': len(self.channels),
                'full_band_clients': sum(band == FULL_BAND for band in self.client_bands.values()),
                'receiving': self.socket is not None,
                'sample_rate': self.info.sample_rate if self.info else None,
                'center_freq': self.info.center_freq if self.info else None,
                'epoch': self.info.epoch if self.info else None, 'format': 'signed-iq8', 'version': 1,
                'packet_age_seconds': time.monotonic() - self.last_packet if self.last_packet else None,
                'counters': dict(self.counters)}
