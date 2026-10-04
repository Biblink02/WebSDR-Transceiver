"""Actual native filtering, rate/phase continuity and shared band fanout."""
import time
import numpy as np
import pytest
from iq_protocol import HEADER, FrameInfo, make_header, validate_frame
from iq import IQDistributor
from subbands import Band, BandPlan, NativeChannelizer, native_library

RATE, CENTER = 520834, 739700000


def iq_samples(frequency, count, amplitude=.65):
    wave = amplitude * np.exp(2j * np.pi * frequency * np.arange(count) / RATE)
    values = np.empty(count * 2, dtype=np.int8)
    values[::2] = np.rint(127 * wave.real).astype(np.int8)
    values[1::2] = np.rint(127 * wave.imag).astype(np.int8)
    return values.tobytes()


def channelize(payload, chunk, offset=0, output_rate=128000):
    band = Band(0, CENTER + offset, output_rate, CENTER + offset - output_rate*.4, CENTER + offset + output_rate*.4)
    channel = NativeChannelizer(RATE, CENTER, band)
    output = []
    try:
        for sequence, start in enumerate(range(0, len(payload), chunk * 2)):
            data = payload[start:start+chunk*2]
            info = FrameInfo(sequence, RATE, CENTER, len(data)//2, 17)
            packet = channel.process(make_header(info) + data, info)
            if packet:
                assert validate_frame(packet).sample_rate == output_rate
                output.append(packet[HEADER.size:])
    finally:
        channel.close()
    return np.frombuffer(b''.join(output), dtype=np.int8).astype(np.float32).reshape(-1, 2)


def test_native_filter_rate_tone_shift_alias_rejection_and_chunk_continuity():
    count = RATE
    payload = iq_samples(100000, count)
    selected = channelize(payload, 8192, offset=96000)
    assert abs(len(selected) - 128000) <= 2
    complex_samples = (selected[:,0] + 1j*selected[:,1]) / 127
    peak = np.argmax(np.abs(np.fft.fft(complex_samples[2048:2048+32768])))
    assert abs(peak * 128000 / 32768 - 4000) < 4
    assert .6 < np.sqrt(np.mean(abs(complex_samples[2048:])**2)) < .7
    rejected = channelize(payload, 65536)
    rejected_rms = np.sqrt(np.mean(rejected[2048:]**2)) / 127
    assert rejected_rms < .002, rejected_rms  # >47 dB suppression at signed-I/Q8 precision.
    # Blocks of different size yield exactly the same IQ and number of samples.
    assert np.array_equal(selected, channelize(payload, 1001, offset=96000))
    assert np.array_equal(selected, channelize(payload, 65536, offset=96000))
    assert abs(len(channelize(iq_samples(0, count), 8192, output_rate=48000)) - 48000) <= 2
    for frequency in [-50000, 50000]:
        edge = channelize(iq_samples(frequency, count//2), 8192)
        assert .4 < np.sqrt(np.mean(edge[2048:]**2)) / 127 < .5


def test_native_abi_rejects_invalid_metadata_and_oversized_blocks():
    lib = native_library()
    for input_rate, output_rate, offset in [(47000,48000,0), (520834,47000,0),
            (520834,600000,0), (4000001,48000,0), (520834,128000,200000), (520834,128000,float('nan'))]:
        assert not lib.channelizer_new(input_rate, output_rate, offset)
    channel = NativeChannelizer(RATE, CENTER, BandPlan(RATE,CENTER,CENTER-200000,CENTER+200000).bands[0])
    try:
        assert lib.channelizer_process(channel.handle, 65537) == -1
        assert lib.channelizer_process(channel.handle, 0) == -1
        for count, payload in [(65537, bytes(32+65537*2)), (256, bytes(33))]:
            with pytest.raises(ValueError):
                channel.process(payload, FrameInfo(0, RATE, CENTER, count, 1))
    finally: channel.close()
    channel.close()
    assert lib.channelizer_process(None, 256) == -1


def test_band_plan_covers_view_with_overlap_and_bounded_work():
    for rate in [48000,128000,500000,520834,1000000,4000000]:
        plan = BandPlan(rate,CENTER,CENTER-200000,CENTER+200000)
        bands = list(plan.bands.values())
        assert 1 <= len(bands) <= 16
        assert plan.default in plan.bands
        for band in bands:
            assert abs(band.center_freq - CENTER) + band.sample_rate / 2 <= rate / 2
        for before, after in zip(bands, bands[1:]): assert before.high >= after.low
        assert bands[0].low == max(CENTER-200000,CENTER-rate/2+min(128000,rate)*.1)
        assert bands[-1].high == min(CENTER+200000,CENTER+rate/2-min(128000,rate)*.1)
        for frequency in np.linspace(bands[0].low, bands[-1].high-15000, 200):
            assert any(band.low <= frequency and band.high >= frequency+15000 for band in bands)
    with pytest.raises(ValueError): BandPlan(4000000,CENTER,CENTER-2000000,CENTER+2000000)
    with pytest.raises(ValueError): BandPlan(RATE,CENTER,CENTER+1000000,CENTER+2000000)


def test_one_channelizer_per_band_and_last_listener_releases_resources():
    distributor = IQDistributor(None, 'unused')
    a, b, c = distributor.subscribe(0), distributor.subscribe(0), distributor.subscribe(1)
    info = FrameInfo(0,RATE,CENTER,8192,42)
    distributor.ingest(make_header(info)+iq_samples(100000,8192))
    assert distributor.counters['channel_frames'] == 2
    assert distributor.diagnostics()['active_bands'] == 2
    assert a.get_nowait() == b.get_nowait()
    assert validate_frame(c.get_nowait()).center_freq == CENTER+80000
    distributor.unsubscribe(a); assert len(distributor.channels) == 2
    distributor.unsubscribe(b); assert len(distributor.channels) == 1
    distributor.unsubscribe(c); assert len(distributor.channels) == 0
    assert distributor.idle.is_set() and not distributor.demand.is_set()
    with pytest.raises(ValueError): distributor.subscribe(123)


def test_five_active_bands_sustained_realtime_budget():
    distributor = IQDistributor(None, 'unused')
    queues = [distributor.subscribe(band) for band in distributor.plan.bands]
    payload = iq_samples(1000,8192)
    started = time.perf_counter()
    count = 0
    for sequence in range(128):
        info = FrameInfo(sequence,RATE,CENTER,8192,3)
        distributor.ingest(make_header(info)+payload)
        count += info.count
        for queue in queues: queue.get_nowait()
    elapsed = time.perf_counter() - started
    for queue in queues: distributor.unsubscribe(queue)
    print(f'Five active bands: {count/RATE:.3f} s I/Q in {elapsed:.3f} s, {count/RATE/elapsed:.2f}x realtime')
    assert elapsed < count/RATE
