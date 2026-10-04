"""Execute in the production GNU Radio image against the separate official IIO emulator."""
import argparse
import threading
import time
from pathlib import Path

import iio
import numpy as np
import yaml

from capture_control import PlutoPower
from iq_protocol import validate_frame
from iq_publisher import Packetizer
from sdr_server import ReceiverSource


class Capture:
    def __init__(self):
        self.frames = []
        self.done = threading.Event()

    def configure(self, packetizer):
        self.packetizer = packetizer

    def push(self, samples):
        if len(self.frames) < 64:
            self.frames.extend(self.packetizer.push(samples))
            if len(self.frames) >= 64:
                self.done.set()


def receive(config):
    capture = Capture()
    graph = ReceiverSource(config, capture)
    try:
        graph.start()
        assert capture.done.wait(15), 'GNU Radio did not read sufficient emulator samples'
    finally:
        graph.close()
    return capture.frames[:64]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uri', required=True)
    parser.add_argument('--replay', type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load(Path('/app/config.yaml').read_text())
    config.update(iio_uri=args.uri, iq_frame_samples=8192)
    deadline = time.monotonic()+10
    while True:
        try:
            context = iio.Context(args.uri)
            del context
            break
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.1)
    power = PlutoPower(args.uri)
    power.sleep()
    assert power.state == 'sleep'
    power.wake()
    first, second = receive(config), receive(config)
    info = validate_frame(first[0])
    assert info.sample_rate == config['samp_rate'] == 520834
    assert info.center_freq == config['lo_freq'] == 739700000
    assert validate_frame(second[0]).epoch != info.epoch
    data = np.fromfile(args.replay, dtype='<i2', count=64*8192*2).reshape(-1, 2)
    samples = (data[:, 0]+1j*data[:, 1]).astype(np.complex64)/2048
    golden = Packetizer(info.sample_rate, info.center_freq, 8192, epoch=info.epoch)
    expected = b''.join(frame[32:] for frame in golden.push(samples))
    assert b''.join(frame[32:] for frame in first) == expected, 'IIO channel order/scale/sample continuity changed'
    assert b''.join(frame[32:] for frame in second) == expected, 'Reopening the IIO capture changed replay samples'
    context = iio.Context(args.uri)
    phy = context.find_device('ad9361-phy')
    rx = phy.find_channel('voltage0', False)
    assert rx.attrs['rf_bandwidth'].value == '250000'
    assert rx.attrs['gain_control_mode'].value == 'slow_attack'
    assert all(rx.attrs[name].value == '1' for name in
               ('quadrature_tracking_en', 'rf_dc_offset_tracking_en', 'bb_dc_offset_tracking_en'))
    assert phy.attrs['in_out_voltage_filter_fir_en'].value == '1'
    del context
    power.sleep()
    power.wake()
    print('PASS: production GNU Radio IIO source, 520834 Hz/739700000 Hz readback, '
          'SSB/CW replay byte equality, FIR configuration, RF bandwidth/AGC/tracking, '
          'capture reopen with a fresh epoch and ENSM sleep/wake attributes')


if __name__ == '__main__':
    main()
