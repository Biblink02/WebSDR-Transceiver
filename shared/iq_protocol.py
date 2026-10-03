"""Shared v1 I/Q wire contract. Used by source, distributor and test fixtures."""
from dataclasses import dataclass
import math
import struct

HEADER = struct.Struct('<4sBBHIIdII')
MAGIC = b'WSIQ'
MAX_SAMPLES = 65536
MAX_FRAME_BYTES = HEADER.size + MAX_SAMPLES * 2


@dataclass(frozen=True)
class FrameInfo:
    sequence: int
    sample_rate: int
    center_freq: float
    count: int
    epoch: int


def make_header(info: FrameInfo) -> bytes:
    if (not 48000 <= info.sample_rate <= 4000000 or not math.isfinite(info.center_freq)
            or info.center_freq <= 0 or not 1 <= info.count <= MAX_SAMPLES):
        raise ValueError('Invalid I/Q metadata')
    return HEADER.pack(MAGIC, 1, 1, HEADER.size, info.sequence & 0xffffffff,
                       info.sample_rate, info.center_freq, info.count, info.epoch & 0xffffffff)


def validate_frame(data: bytes) -> FrameInfo:
    if not HEADER.size <= len(data) <= MAX_FRAME_BYTES:
        raise ValueError('Invalid I/Q frame size')
    magic, version, fmt, size, sequence, rate, center, count, epoch = HEADER.unpack_from(data)
    if magic != MAGIC or version != 1 or fmt != 1 or size != HEADER.size:
        raise ValueError('Unsupported I/Q protocol')
    if (not 48000 <= rate <= 4000000 or not math.isfinite(center) or center <= 0
            or not 1 <= count <= MAX_SAMPLES or len(data) != HEADER.size + count * 2):
        raise ValueError('Invalid I/Q metadata or payload length')
    return FrameInfo(sequence, rate, center, count, epoch)
