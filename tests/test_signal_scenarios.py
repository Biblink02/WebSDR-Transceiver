"""Signal quality, deterministic scheduling and the exact IIO sample representation."""
import json

import numpy as np
import pytest

from signal_scenarios import Scenario, morse_envelope


def catalog(tmp_path, stations, events=(), period=4):
    path = tmp_path/'scenario.json'
    path.write_text(json.dumps({'period_seconds': period, 'seed': 1, 'noise_dbfs': -120,
                               'stations': stations, 'scenarios': {'check': list(events)}}))
    return path


def test_speech_sidebands_and_chunk_invariance(tmp_path):
    for mode, side in [('usb', 1), ('lsb', -1)]:
        path = catalog(tmp_path, [{'id': 'voice', 'mode': mode, 'offset_hz': 4000, 'amplitude': .5}])
        engine = Scenario('check', 48000, path)
        samples = engine.render(0, 96000)
        split = Scenario('check', 48000, path)
        chunks = [split.render(0, 1001), split.render(1001, 8192), split.render(9193, 86807)]
        assert np.array_equal(samples, np.concatenate(chunks))
        spectrum = np.abs(np.fft.fft(samples))**2
        offsets = np.fft.fftfreq(len(samples), 1/48000)-4000
        wanted = spectrum[(side*offsets > 300) & (side*offsets < 2700)].sum()
        opposite = spectrum[(side*offsets < -300) & (side*offsets > -2700)].sum()
        assert 10*np.log10(wanted/opposite) > 40
        assert np.std(np.abs(samples)) > .02, 'Speech modulation was replaced by a constant carrier'


def test_cw_uses_morse_timing_and_smoothed_edges():
    envelope = morse_envelope('ET', 20, 12000)
    active = np.flatnonzero(envelope > .5)
    runs = np.split(active, np.flatnonzero(np.diff(active) > 1)+1)
    assert len(runs) == 2
    dot, dash = [len(run)/12000 for run in runs]
    assert abs(dot-.06) < .006 and abs(dash-.18) < .006
    assert envelope[0] == 0 and envelope[-1] == 0
    assert np.max(np.abs(np.diff(envelope))) < .04
    with pytest.raises(ValueError):
        morse_envelope('?!', 20)


def test_mute_noise_fading_and_cfo_return_are_automatic(tmp_path):
    station = {'id': 'tone', 'mode': 'tone', 'offset_hz': 1000, 'amplitude': .4}
    events = [
        {'action': 'mute', 'station': '*', 'start': 1, 'duration': .5},
        {'action': 'noise', 'start': 1, 'duration': .5, 'dbfs': -30},
        {'action': 'fade', 'station': 'tone', 'start': 2, 'duration': 1, 'depth': .9, 'hz': 1},
        {'action': 'drift', 'station': 'tone', 'start': 2, 'duration': 1, 'hz_per_second': 40},
        {'action': 'stall', 'start': 3, 'duration': .5}
    ]
    engine = Scenario('check', 48000, catalog(tmp_path, [station], events))
    assert .39 < np.sqrt(np.mean(np.abs(engine.render(0, 1000))**2)) < .41
    muted = engine.render(48000, 24000)
    assert abs(20*np.log10(np.sqrt(np.mean(np.abs(muted)**2)))+30) < .2
    faded = engine.render(120000, 1000)
    assert .039 < np.mean(np.abs(faded)) < .045
    shifted = engine.render(118000, 500)
    frequency = np.median(np.angle(shifted[1:]*shifted[:-1].conj()))*48000/(2*np.pi)
    assert 1017 < frequency < 1020
    recovered = engine.render(150000, 500)
    frequency = np.median(np.angle(recovered[1:]*recovered[:-1].conj()))*48000/(2*np.pi)
    assert abs(frequency-1000) < .01
    assert engine.stalled(3.1) and not engine.stalled(3.5) and engine.stalled(7.1)


def test_catalog_has_signals_in_all_receive_bands_and_rejects_invalid_events(tmp_path):
    engine = Scenario('automatic')
    assert {round(station['offset_hz']/80000) for station in engine.stations} >= {-2, -1, 0, 1, 2}
    assert np.isfinite(engine.render(0, 8192)).all()
    assert engine.stalled(35) and not engine.stalled(42)
    path = catalog(tmp_path, [{'id': 'tone', 'mode': 'tone', 'offset_hz': 1000, 'amplitude': .4}],
                   [{'action': 'mute', 'station': 'missing', 'start': 0, 'duration': 1}])
    with pytest.raises(ValueError, match='unknown station'):
        Scenario('check', 48000, path)
    with pytest.raises(ValueError, match='Unknown scenario'):
        Scenario('missing')
