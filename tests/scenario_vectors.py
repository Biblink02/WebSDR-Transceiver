"""Prepare speech/CW for the compiled WASM receiver and check recovered speech."""
import argparse
import json
import wave
from pathlib import Path

import numpy as np
from scipy import signal
from signal_scenarios import ASSETS, Scenario


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for mode, frequency in [('usb', -12000), ('lsb', 31000), ('cw', 1000)]:
        station = {'id': mode, 'mode': mode, 'offset_hz': frequency, 'amplitude': .5,
                   'message': 'ET ET', 'wpm': 20}
        path = directory/f'{mode}.json'
        path.write_text(json.dumps({'period_seconds': 4, 'seed': 7, 'noise_dbfs': -90,
                                   'stations': [station], 'scenarios': {'check': []}}))
        engine = Scenario('check', 520834, path)
        with (directory/f'{mode}.iq8').open('wb') as output:
            total = 2*520834
            for position in range(0, total, 8192):
                samples = engine.render(position, min(8192, total-position))
                output.write(np.round(np.column_stack([samples.real, samples.imag])*127).astype(np.int8).tobytes())


def verify(directory):
    with wave.open(str(ASSETS/'audio/speech.wav')) as source:
        reference = np.frombuffer(source.readframes(source.getnframes()), '<i2').astype(np.float32)/32768
        reference = signal.resample_poly(reference, 48000, source.getframerate())[:96000]
    for mode in ('usb', 'lsb'):
        audio = np.fromfile(directory/f'{mode}.f32', '<f4')
        assert 95000 <= len(audio) <= 97000 and np.isfinite(audio).all()
        # The library's causal filters/resampler add a small delay and may invert phase.
        correlation = signal.correlate(audio, reference, mode='full', method='fft')
        lag = np.argmax(np.abs(correlation))-(len(reference)-1)
        assert abs(lag) < 2400, (mode, lag)
        start_audio, start_reference = max(0, lag), max(0, -lag)
        count = min(len(audio)-start_audio, len(reference)-start_reference)
        score = abs(np.corrcoef(audio[start_audio:start_audio+count], reference[start_reference:start_reference+count])[0, 1])
        assert score > .90, (mode, score)
        print(f'{mode.upper()} speech correlation {score:.4f}, filter delay {lag/48:.2f} ms')
    cw = np.fromfile(directory/'cw.f32', '<f4')
    freqs, times, spectrum = signal.spectrogram(cw, 48000, nperseg=4096, noverlap=2048)
    peak = freqs[np.argmax(np.sum(spectrum, axis=1))]
    assert abs(peak-700) < 20
    levels = np.sqrt(np.mean(cw[:len(cw)//480*480].reshape(-1, 480)**2, axis=1))
    assert levels.max() > .1 and np.count_nonzero(levels < .005) > 20
    print(f'CW keyed audio recovered at {peak:.2f} Hz with silent key-up intervals')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'verify'])
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    (prepare if args.action == 'prepare' else verify)(args.directory)
