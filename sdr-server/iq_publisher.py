"""Bounded packetization and source-side signed 8-bit I/Q quantization."""
import math
import secrets
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
    def __init__(self, address, packetizer, health):
        self.packetizer, self.health = packetizer, health
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.setsockopt(zmq.SNDHWM, 4)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.bind(address)

    def push(self, samples):
        if len(samples):
            self.health.source_progress()
        for frame in self.packetizer.push(samples):
            try:
                self.socket.send(frame, flags=zmq.NOBLOCK)
                self.health.published()
                self.packetizer.counters['published'] += 1
            except zmq.Again:
                self.packetizer.counters['dropped'] += 1

    def close(self):
        self.socket.close(linger=0)
        self.context.term()
