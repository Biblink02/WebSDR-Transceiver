"""Bounded packetization and source-side signed 8-bit I/Q quantization."""
import math
import secrets
from queue import Empty, Full, Queue
from collections import Counter
import numpy as np
import zmq
from iq_protocol import FrameInfo, MAX_SAMPLES, make_header


class Packetizer:
    def __init__(self, sample_rate, center_freq, frame_samples=8192, scale=1.0, epoch=None):
        if (not 256 <= frame_samples <= MAX_SAMPLES or not math.isfinite(scale) or scale <= 0):
            raise ValueError('Invalid I/Q frame size or quantization scale')
        self.rate, self.center, self.scale = sample_rate, center_freq, scale
        self.epoch = secrets.randbits(32) if epoch is None else epoch
        self.sequence, self.used = 0, 0
        self.buffer = np.empty(frame_samples, dtype=np.complex64)
        self.counters = Counter()
        make_header(FrameInfo(0, sample_rate, center_freq, frame_samples, self.epoch))

    def push(self, samples):
        # A generator yields one bounded frame at a time, without a growing frame list.
        offset = 0
        while offset < len(samples):
            count = min(len(samples)-offset, len(self.buffer)-self.used)
            self.buffer[self.used:self.used+count] = samples[offset:offset+count]
            self.used += count
            offset += count
            self.counters['samples'] += count
            if self.used == len(self.buffer):
                iq = self.buffer.view(np.float32)
                invalid = ~np.isfinite(iq)
                self.counters['malformed_samples'] += int(np.count_nonzero(invalid))
                if invalid.any():
                    iq[invalid] = 0
                scaled = iq*self.scale
                self.counters['saturated_components'] += int(np.count_nonzero(np.abs(scaled)>1))
                payload = np.rint(np.clip(scaled, -1, 1)*127).astype(np.int8).tobytes()
                info = FrameInfo(self.sequence, self.rate, self.center, self.used, self.epoch)
                self.sequence = (self.sequence+1) & 0xffffffff
                self.used = 0
                yield make_header(info)+payload


class Publisher:
    """One socket owner; the GNU Radio scheduler only enqueues bounded frames."""
    def __init__(self, address, health):
        self.packetizer, self.health = None, health
        self.pending = Queue(maxsize=4)
        self.subscribers = 0
        self.counters = Counter(published=0, dropped=0)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.XPUB)
        self.socket.setsockopt(zmq.XPUB_VERBOSER, 1)
        self.socket.setsockopt(zmq.SNDHWM, 4)
        self.socket.setsockopt(zmq.RCVHWM, 64)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.HEARTBEAT_IVL, 1000)
        self.socket.setsockopt(zmq.HEARTBEAT_TIMEOUT, 5000)
        self.socket.setsockopt(zmq.HEARTBEAT_TTL, 5000)
        self.socket.bind(address)

    def configure(self, packetizer):
        self.discard_pending()
        self.packetizer = packetizer

    def discard_pending(self):
        while True:
            try:
                self.pending.get_nowait()
            except Empty:
                return

    def push(self, samples):
        if len(samples):
            self.health.source_progress()
        for frame in self.packetizer.push(samples):
            try:
                self.pending.put_nowait(frame)
            except Full:
                try:
                    self.pending.get_nowait()
                except Empty:
                    pass
                self.counters['dropped'] += 1
                self.pending.put_nowait(frame)

    def service(self):
        # Called by the control thread, never by the GNU Radio scheduler.
        while self.socket.poll(0, zmq.POLLIN):
            event = self.socket.recv(flags=zmq.NOBLOCK)
            if event == b'\x01':
                self.subscribers += 1
            elif event == b'\x00':
                self.subscribers = max(0, self.subscribers-1)
        for _ in range(4):
            try:
                frame = self.pending.get_nowait()
            except Empty:
                break
            try:
                self.socket.send(frame, flags=zmq.NOBLOCK)
                self.health.published()
                self.counters['published'] += 1
            except zmq.Again:
                self.counters['dropped'] += 1
        return self.subscribers

    def close(self):
        self.socket.close(linger=0)
        self.context.term()
