"""Run the actual Pluto flowgraph with GNU Radio pacing for a file-backed IIO clock."""
import logging
import os
import signal
import threading
from pathlib import Path

import yaml
from gnuradio import blocks, gr

from capture_control import CaptureController, PlutoPower
from iq_publisher import Publisher
from sdr_server import ReceiverSource, decimation_for
from stream_health import StreamHealth


class PacedReceiver(ReceiverSource):
    def __init__(self, config, publisher):
        super().__init__(config, publisher)
        rate = publisher.packetizer.rate
        factor = decimation_for(int(config['samp_rate']), int(config.get('iq_target_rate', 500000)))
        target = self.decimator if factor > 1 else self.sink
        self.disconnect(self.source, target)
        self.clock = blocks.throttle(gr.sizeof_gr_complex, rate*factor, True)
        self.connect(self.source, self.clock, target)


def main():
    logging.basicConfig(level=logging.INFO)
    config = yaml.safe_load(Path(os.getenv('CONFIG_PATH', '/app/config.yaml')).read_text())
    if not str(config['iio_uri']).startswith('ip:iio-emulator'):
        raise ValueError('The demo reader requires the local iio-emulator service')
    health = StreamHealth(float(config.get('sdr_stall_seconds', 2)))
    publisher = Publisher(f'tcp://0.0.0.0:{int(config.get("sdr_iq_port", 5000))}', health)
    controller = CaptureController(lambda: PacedReceiver(config, publisher),
        PlutoPower(str(config['iio_uri'])), publisher, health, float(config.get('sdr_idle_seconds', .5)))
    health.serve(int(config.get('sdr_health_port', 8081)))
    stopped = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stopped.set())
    try:
        while not stopped.is_set():
            publisher.service()
            controller.tick()
            stopped.wait(.005 if controller.capture is not None else .1)
    finally:
        controller.close()
        health.close()
        publisher.close()


if __name__ == '__main__':
    main()
