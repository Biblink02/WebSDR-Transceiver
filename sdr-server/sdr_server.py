"""Maintained GNU Radio PlutoSDR flowgraph; all listener DSP lives in WASM."""
import logging
import os
import signal
import threading
from contextlib import ExitStack
from pathlib import Path
import numpy as np
import yaml
from gnuradio import gr, iio, filter as gr_filter
from gnuradio.filter import firdes
from gnuradio.fft import window
from iq_publisher import Packetizer, Publisher
from stream_health import StreamHealth
from capture_control import CaptureController, PlutoPower


def decimation_for(source_rate, target_rate):
    if not 48000 <= target_rate <= source_rate <= 4000000:
        raise ValueError('Rates must satisfy 48000 <= target <= source <= 4000000')
    factor = max(1, round(source_rate/target_rate))
    while factor > 1 and source_rate % factor:
        factor -= 1
    return factor


def antialias_taps(source_rate, factor):
    output_rate = source_rate/factor
    return firdes.low_pass(1.0, source_rate, output_rate*0.4, output_rate*0.1,
                          window.WIN_BLACKMAN_HARRIS)


class IqSink(gr.sync_block):
    def __init__(self, publisher):
        super().__init__(name='Packed I/Q publisher', in_sig=[np.complex64], out_sig=None)
        self.publisher = publisher

    def work(self, input_items, output_items):
        self.publisher.push(input_items[0])
        return len(input_items[0])


class ReceiverSource(gr.top_block):
    def __init__(self, cfg, publisher):
        super().__init__('WebSDR I/Q source', catch_exceptions=True)
        rate = int(cfg['samp_rate'])
        factor = decimation_for(rate, int(cfg.get('iq_target_rate', 500000)))
        center = float(cfg['lo_freq'])
        self.source = iio.fmcomms2_source_fc32(str(cfg['iio_uri']), [True, True], int(cfg['buffer_size']))
        self.source.set_frequency(int(center))
        self.source.set_samplerate(rate)
        self.source.set_gain_mode(0, 'slow_attack')
        self.source.set_quadrature(True)
        self.source.set_rfdc(True)
        self.source.set_bbdc(True)
        self.source.set_filter_params('Auto', '', 0, 0)
        # GNU Radio's IIO source has no RF-bandwidth setter. Use libiio's existing
        # Python API, and read back hardware-rounded rate/frequency for metadata.
        import iio as libiio
        context = libiio.Context(str(cfg['iio_uri']))
        phy = context.find_device('ad9361-phy')
        if phy is None:
            raise RuntimeError('Pluto AD9361 PHY device is unavailable')
        rx = phy.find_channel('voltage0', False)
        rx.attrs['rf_bandwidth'].value = str(int(cfg['rf_bandwidth']))
        # Read the streaming ADC rate: GNU Radio may enable FPGA decimation,
        # in which case the PHY sampling frequency is higher than the I/Q rate.
        adc = context.find_device('cf-ad9361-lpc')
        if adc is None:
            raise RuntimeError('Pluto streaming ADC device is unavailable')
        rate = int(adc.find_channel('voltage0', False).attrs['sampling_frequency'].value)
        center = float(phy.find_channel('altvoltage0', True).attrs['frequency'].value)
        del context
        factor = decimation_for(rate, int(cfg.get('iq_target_rate', 500000)))
        output_rate = rate//factor
        self.publisher = publisher
        self.publisher.configure(Packetizer(output_rate, center, int(cfg.get('iq_frame_samples', 8192)),
                                             float(cfg.get('iq_scale', 1))))
        self.sink = IqSink(self.publisher)
        if factor > 1:
            self.decimator = gr_filter.fir_filter_ccf(factor, antialias_taps(rate, factor))
            self.connect(self.source, self.decimator, self.sink)
        else:
            self.connect(self.source, self.sink)
        logging.info('Publishing %s samples/s, decimation %s, %.3f Mbit/s payload per listener',
                     output_rate, factor, output_rate*16/1e6)

    def close(self):
        self.stop()
        self.wait()
        self.disconnect_all()
        # Release native IIO handles and buffers before requesting ENSM sleep.
        self.source = None
        self.sink = None
        self.decimator = None


def main():
    logging.basicConfig(level=logging.INFO)
    with Path(os.getenv('CONFIG_PATH', '/app/config.yaml')).open() as config_file:
        cfg = yaml.safe_load(config_file)
    if not isinstance(cfg, dict):
        raise ValueError('Configuration must be a YAML mapping')
    health = StreamHealth(float(cfg.get('sdr_stall_seconds', 2)))
    publisher = Publisher(f'tcp://0.0.0.0:{int(cfg.get("sdr_iq_port", 5000))}', health)
    controller = CaptureController(lambda: ReceiverSource(cfg, publisher),
        PlutoPower(str(cfg['iio_uri'])), publisher, health,
        float(cfg.get('sdr_idle_seconds', 10)))
    health.serve(int(cfg.get('sdr_health_port', 8081)))
    stopped = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stopped.set())
    try:
        while not stopped.is_set():
            publisher.service()
            controller.tick()
            stopped.wait(0.005 if controller.capture is not None else 0.2)
    finally:
        with ExitStack() as cleanup:
            cleanup.callback(publisher.close)
            cleanup.callback(health.close)
            cleanup.callback(controller.close)


if __name__ == '__main__':
    main()
