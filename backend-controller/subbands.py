"""Bounded subband catalog and the native liquid-dsp channelizer binding."""
import ctypes
import math
import os
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Literal
from iq_protocol import HEADER, MAX_SAMPLES, FrameInfo, make_header

FULL_BAND = 'full'


@dataclass(frozen=True)
class Band:
    id: int | Literal['full']
    center_freq: float
    sample_rate: int
    low: float
    high: float

    def json(self):
        return {**asdict(self), 'bits_per_second': self.sample_rate * 16}


class BandPlan:
    def __init__(self, input_rate, center, view_low, view_high, output_rate=128000):
        if (not 48000 <= input_rate <= 4000000 or not 48000 <= output_rate <= 4000000 or
                not all(math.isfinite(v) for v in (center, view_low, view_high)) or center <= 0 or view_low >= view_high):
            raise ValueError('Invalid subband configuration')
        rate = min(int(output_rate), int(input_rate))
        # Overlapping usable spans exclude the library resampler's transition band.
        # At least 16 kHz overlap also accommodates the maximum 15 kHz SSB passband.
        half, step = rate * .4, min(rate * .625, rate * .8 - 16000)
        edge = (input_rate - rate) / 2
        low = max(view_low, center - edge - half)
        high = min(view_high, center + edge + half)
        if high <= low:
            raise ValueError('Configured view does not overlap usable I/Q')
        first = min(0, math.ceil((low - center + half) / step))
        last = max(0, math.floor((high - center - half) / step))
        if center + last * step + half < high: last += 1
        if center + first * step - half > low: first -= 1
        if last - first + 1 > 16:
            raise ValueError('Subband plan exceeds 16 bands; increase iq_subband_rate or narrow the view')
        bands = {}
        used = set()
        for index in range(first, last + 1):
            offset = max(-edge, min(edge, index * step))
            band_low, band_high = max(low, center + offset - half), min(high, center + offset + half)
            if offset in used or band_low >= band_high: continue
            used.add(offset)
            bands[index] = Band(index, center + offset, rate, band_low, band_high)
        self.bands = bands
        self.default = min(bands, key=lambda key: abs(bands[key].center_freq - center))
        self.input_rate, self.center = input_rate, center
        self.full_band = Band(FULL_BAND, center, input_rate,
                              max(view_low, center-input_rate/2), min(view_high, center+input_rate/2))

    def get_band(self, selection):
        if selection == FULL_BAND:
            return self.full_band
        try:
            return self.bands[selection]
        except KeyError as error:
            raise ValueError('Unknown I/Q receive band') from error

    def json(self):
        return {'default': self.default, 'input_sample_rate': self.input_rate,
                'input_center_freq': self.center, 'full_band': self.full_band.json(),
                'bands': [band.json() for band in self.bands.values()]}


@lru_cache(maxsize=1)
def native_library():
    library = ctypes.CDLL(os.getenv('SUBBAND_LIBRARY', '/app/libwebsdr_channelizer.so'))
    library.channelizer_new.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_double]
    library.channelizer_new.restype = ctypes.c_void_p
    for name in ('channelizer_input', 'channelizer_output'):
        getattr(library, name).argtypes = [ctypes.c_void_p]
        getattr(library, name).restype = ctypes.c_void_p
    library.channelizer_free.argtypes = [ctypes.c_void_p]
    library.channelizer_free.restype = None
    library.channelizer_process.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    library.channelizer_process.restype = ctypes.c_int
    return library


class NativeChannelizer:
    """Owned by IQDistributor's event loop; process/close must stay on that thread."""
    def __init__(self, input_rate, input_center, band):
        self.library, self.band = native_library(), band
        self.handle = self.library.channelizer_new(input_rate, band.sample_rate, band.center_freq - input_center)
        if not self.handle:
            raise ValueError('Native channelizer could not create this band')
        self.input = self.library.channelizer_input(self.handle)
        self.output = self.library.channelizer_output(self.handle)

    def process(self, data, info):
        if not self.handle: raise RuntimeError('Channelizer is closed')
        if not 1 <= info.count <= MAX_SAMPLES or len(data) != HEADER.size + info.count * 2:
            raise ValueError('Invalid native input size')
        ctypes.memmove(self.input, data[HEADER.size:], info.count * 2)
        count = self.library.channelizer_process(self.handle, info.count)
        if count < 0 or count > MAX_SAMPLES: raise RuntimeError('Native channelizer rejected I/Q')
        if not count: return None
        return make_header(FrameInfo(info.sequence, self.band.sample_rate, self.band.center_freq, count, info.epoch)) + ctypes.string_at(self.output, count * 2)

    def close(self):
        if self.handle:
            handle = self.handle
            self.handle = None
            self.library.channelizer_free(handle)
