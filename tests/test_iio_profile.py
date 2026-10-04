"""Check the generated model/replay before the real GNU Radio integration test."""
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from iio_profile import generate
from signal_scenarios import Scenario


def test_iio_profile_and_replay_have_correct_channel_order_scale_and_size(tmp_path):
    generate(tmp_path, 520834, 739700000, 'clean', 1)
    tree = ET.parse(tmp_path/'pluto.xml')
    adc = tree.find("./device[@name='cf-ad9361-lpc']")
    channels = adc.findall('channel')
    assert [channel.attrib['id'] for channel in channels] == ['voltage0', 'voltage1']
    assert all(channel.find('scan-element').attrib['format'] == 'le:S12/16>>0' for channel in channels)
    data = np.fromfile(tmp_path/'cf-ad9361-lpc_buf0.bin', '<i2').reshape(-1, 2)
    assert data.shape == (520834, 2) and data.min() >= -2048 and data.max() <= 2047
    expected = Scenario('clean').render(0, 65536)
    values = np.column_stack([expected.real, expected.imag])
    assert np.array_equal(data[:65536], np.round(np.clip(values, -1, 2047/2048)*2048).astype('<i2'))
    with pytest.raises(ValueError, match='Stall scenarios'):
        generate(tmp_path/'invalid', 520834, 739700000, 'recovery', 1)
