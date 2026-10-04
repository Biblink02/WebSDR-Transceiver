"""Build our own small speech fixture with eSpeak NG and SciPy, never an RF recording."""
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from scipy import signal

root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as directory:
    raw = Path(directory)/'speech.wav'
    subprocess.run(['espeak-ng', '-v', 'en', '-s', '165', '-w', str(raw),
                    '-f', str(root/'speech.txt')], check=True)
    with wave.open(str(raw)) as source:
        rate = source.getframerate()
        audio = np.frombuffer(source.readframes(source.getnframes()), '<i2').astype(np.float64)
    audio = signal.resample_poly(audio, 12000, rate)
    sos = signal.butter(6, [300, 2700], btype='bandpass', fs=12000, output='sos')
    audio = signal.sosfiltfilt(sos, audio)
    audio /= max(np.max(np.abs(signal.hilbert(audio))), 1)
    audio = np.concatenate([audio, np.zeros(6000)])
    destination = Path(sys.argv[1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(12000)
        output.writeframes(np.round(audio*30000).astype('<i2').tobytes())
