"""Deterministic test signals. SciPy implements analytic SSB and rate conversion."""
import json
import math
import wave
from pathlib import Path

import numpy as np
from scipy import signal

ASSETS = Path(__file__).resolve().parent/'simulation'
MORSE = dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
    '.- -... -.-. -.. . ..-. --. .... .. .--- -.- .-.. -- -. --- .--. --.- .-. ... - ..- ...- .-- -..- -.-- --.. '
    '----- .---- ..--- ...-- ....- ..... -.... --... ---.. ----.'.split()))


def morse_envelope(message, wpm, rate=12000):
    if not 5 <= wpm <= 60 or not 1 <= len(message) <= 80:
        raise ValueError('CW requires 5–60 WPM and 1–80 characters')
    unit = 1.2/wpm
    pieces = []
    for word_index, word in enumerate(message.upper().split()):
        if word_index:
            pieces.append(np.zeros(round(4*unit*rate)))  # previous letter already left 3 units
        for letter in word:
            if letter not in MORSE:
                raise ValueError(f'Unsupported Morse character: {letter}')
            for symbol in MORSE[letter]:
                length = round(unit*(3 if symbol == '-' else 1)*rate)
                pieces.append(signal.windows.tukey(length, min(1, .01*rate/length)))
                pieces.append(np.zeros(round(unit*rate)))
            pieces.append(np.zeros(round(2*unit*rate)))
    if not pieces:
        raise ValueError('CW message must contain letters or digits')
    pieces.append(np.zeros(round(4*unit*rate)))
    return np.concatenate(pieces).astype(np.float32)


class Scenario:
    def __init__(self, name='clean', rate=520834, config_path=None, voice_path=None):
        if not 48000 <= rate <= 4000000:
            raise ValueError('Sample rate must be in [48000, 4000000]')
        self.rate = rate
        config = json.loads(Path(config_path or ASSETS/'scenarios.json').read_text())
        self.period = float(config['period_seconds'])
        if not math.isfinite(self.period) or not 1 <= self.period <= 120:
            raise ValueError('Scenario period must be in [1, 120] seconds')
        self.noise = float(config['noise_dbfs'])
        if not math.isfinite(self.noise) or not -120 <= self.noise <= -6:
            raise ValueError('Noise must be in [-120, -6] dBFS')
        if name not in config['scenarios']:
            raise ValueError(f'Unknown scenario: {name}')
        self.name = name
        self.events = config['scenarios'][name]
        self.stations = config['stations']
        if not 1 <= len(self.stations) <= 16 or len(self.events) > 32:
            raise ValueError('Scenario supports 1–16 stations and at most 32 events')
        ids = {station['id'] for station in self.stations}
        if len(ids) != len(self.stations):
            raise ValueError('Station IDs must be unique')
        self.rng = np.random.default_rng(int(config['seed']))
        self.waveforms = {}
        voice = None
        for station in self.stations:
            mode = station['mode']
            offset, amplitude = float(station['offset_hz']), float(station['amplitude'])
            if (not math.isfinite(offset) or abs(offset)+3000 >= rate*.48 or
                    not math.isfinite(amplitude) or not 0 <= amplitude <= .8):
                raise ValueError('Station frequency/amplitude is outside the supported range')
            if mode in ('usb', 'lsb'):
                if voice is None:
                    with wave.open(str(voice_path or ASSETS/'audio/speech.wav')) as source:
                        if source.getnchannels() != 1 or source.getsampwidth() != 2:
                            raise ValueError('Speech fixture must be mono PCM16')
                        audio_rate = source.getframerate()
                        if not 8000 <= audio_rate <= 48000 or not 0 < source.getnframes() <= audio_rate*30:
                            raise ValueError('Speech fixture must be at most 30 seconds')
                        if source.getnframes()*rate/audio_rate > 16000000:
                            raise ValueError('Resampled speech must fit in 16 million samples')
                        audio = np.frombuffer(source.readframes(source.getnframes()), '<i2').astype(np.float32)/32768
                    # Both operations use existing DSP implementations; no hand-written Hilbert/FIR.
                    voice = signal.resample(signal.hilbert(audio), round(len(audio)*rate/audio_rate)).astype(np.complex64)
                self.waveforms[station['id']] = (voice, rate)
            elif mode == 'cw':
                self.waveforms[station['id']] = (morse_envelope(station['message'], station['wpm']), 12000)
            elif mode != 'tone':
                raise ValueError(f'Unsupported mode: {mode}')
        for event in self.events:
            start, duration = float(event['start']), float(event['duration'])
            if not all(math.isfinite(value) for value in (start, duration)) or not 0 <= start < start+duration <= self.period:
                raise ValueError('Events must fit inside the scenario period')
            action = event['action']
            if action not in ('mute', 'gain', 'fade', 'drift', 'noise', 'stall'):
                raise ValueError(f'Unsupported scenario action: {action}')
            required = {'gain': ['amplitude'], 'fade': ['depth', 'hz'],
                        'drift': ['hz_per_second'], 'noise': ['dbfs']}.get(action, [])
            if any(key not in event for key in required):
                raise ValueError(f'Missing parameters for {action}')
            if action not in ('noise', 'stall') and event['station'] not in ids | {'*'}:
                raise ValueError('Event refers to an unknown station')
            for key, low, high in [('amplitude', 0, .8), ('depth', 0, 1), ('hz', .01, 10),
                                   ('hz_per_second', -100, 100), ('dbfs', -120, -6)]:
                if key in event and (not math.isfinite(float(event[key])) or not low <= float(event[key]) <= high):
                    raise ValueError(f'Invalid event {key}')

    def stalled(self, elapsed):
        phase = elapsed % self.period
        return any(event['action'] == 'stall' and event['start'] <= phase < event['start']+event['duration']
                   for event in self.events)

    def render(self, position, count):
        if position < 0 or not 1 <= count <= 262144:
            raise ValueError('Invalid signal block')
        indices = np.arange(position, position+count, dtype=np.int64)
        times = indices/self.rate
        phase_time = times % self.period
        output = np.zeros(count, np.complex128)
        noise_db = np.full(count, self.noise)
        for station in self.stations:
            amplitude = np.full(count, station['amplitude'], dtype=np.float64)
            phase = station['offset_hz']*times
            for event in self.events:
                active = (phase_time >= event['start']) & (phase_time < event['start']+event['duration'])
                if event['action'] == 'noise':
                    continue
                if event.get('station') not in (station['id'], '*'):
                    continue
                if event['action'] == 'mute':
                    amplitude[active] = 0
                elif event['action'] == 'gain':
                    amplitude[active] = event['amplitude']
                elif event['action'] == 'fade':
                    amplitude[active] *= 1-event['depth']*.5*(1-np.cos(2*np.pi*event['hz']*(phase_time[active]-event['start'])))
                elif event['action'] == 'drift':
                    # Integrate a continuous triangular CFO excursion, returning to zero at the end.
                    local = np.clip(phase_time-event['start'], 0, event['duration'])
                    half = event['duration']/2
                    integral = np.where(local <= half, .5*local**2,
                                        half**2-.5*(event['duration']-local)**2)
                    phase += event['hz_per_second']*(integral+np.floor(times/self.period)*half**2)
            waveform = 1
            if station['id'] in self.waveforms:
                samples, waveform_rate = self.waveforms[station['id']]
                waveform_indices = (indices*waveform_rate//self.rate) % len(samples)
                waveform = samples[waveform_indices]
                if station['mode'] == 'lsb':
                    waveform = waveform.conj()
            output += amplitude*waveform*np.exp(2j*np.pi*phase)
        for event in self.events:
            if event['action'] == 'noise':
                active = (phase_time >= event['start']) & (phase_time < event['start']+event['duration'])
                noise_db[active] = event['dbfs']
        noise = self.rng.standard_normal((count, 2))
        output += (noise[:, 0]+1j*noise[:, 1])*10**(noise_db/20)/np.sqrt(2)
        return output.astype(np.complex64)
