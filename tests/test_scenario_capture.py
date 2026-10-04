"""Exercise scheduled publication stalls and recovery in the real synthetic capture thread."""
import json
import threading
import time

import numpy as np

from synthetic_iq import SyntheticCapture


def test_scheduled_stall_resumes_without_unbounded_catchup_and_closes(tmp_path):
    path = tmp_path/'scheduled.json'
    path.write_text(json.dumps({'period_seconds': 4, 'seed': 1, 'noise_dbfs': -90,
        'stations': [{'id': 'cw', 'mode': 'cw', 'offset_hz': 1000, 'amplitude': .3,
                      'message': 'ET', 'wpm': 20}],
        'scenarios': {'check': [{'start': .3, 'duration': .4, 'action': 'stall'}]}}))
    class Publisher:
        def __init__(self):
            self.times = []
            self.lock = threading.Lock()
            self.peak = 0
        def configure(self, packetizer): self.packetizer = packetizer
        def push(self, samples):
            with self.lock:
                self.times.append(time.monotonic())
                self.peak = max(self.peak, float(np.max(np.abs(samples))))
    publisher = Publisher()
    capture = SyntheticCapture(publisher, 48000, 739700000, frame_samples=2048,
                               scenario='check', scenario_config=path)
    capture.start()
    try:
        capture.stopped.wait(1.1)
    finally:
        capture.close()
    assert not capture.thread.is_alive()
    gaps = np.diff(publisher.times)
    assert gaps.max() > .35 and len(gaps) > 10
    assert publisher.times[-1]-publisher.times[0] > .9
    assert publisher.peak > .25
    assert gaps[-3:].min() > .02, 'Scheduled stall caused a rapid backlog burst'
