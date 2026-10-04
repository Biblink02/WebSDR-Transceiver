"""Generate a minimal Pluto IIO model and signed 12-bit replay for official iiod-emu."""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from signal_scenarios import Scenario

IIO_DTD = '''<!ELEMENT context (device | context-attribute)*>
<!ELEMENT context-attribute EMPTY>
<!ATTLIST context name CDATA #REQUIRED description CDATA #IMPLIED>
<!ATTLIST context-attribute name CDATA #REQUIRED value CDATA #REQUIRED>
<!ELEMENT device (channel | buffer | attribute | debug-attribute)*>
<!ATTLIST device id CDATA #REQUIRED name CDATA #IMPLIED>
<!ELEMENT channel (scan-element?, attribute*)>
<!ATTLIST channel id CDATA #REQUIRED type (input|output) #REQUIRED name CDATA #IMPLIED>
<!ELEMENT buffer (channel | attribute)*>
<!ATTLIST buffer index CDATA #REQUIRED direction (in|out) #IMPLIED>
<!ELEMENT scan-element EMPTY>
<!ATTLIST scan-element index CDATA #REQUIRED format CDATA #REQUIRED>
<!ELEMENT attribute EMPTY>
<!ATTLIST attribute name CDATA #REQUIRED value CDATA #REQUIRED filename CDATA #IMPLIED>
<!ELEMENT debug-attribute EMPTY>
<!ATTLIST debug-attribute name CDATA #REQUIRED value CDATA #REQUIRED>'''


def profile(rate, center):
    root = ET.Element('context', name='emu', description='WebSDR test-only Pluto IIO model')
    ET.SubElement(root, 'context-attribute', name='hw_model', value='PlutoSDR emulator')
    phy = ET.SubElement(root, 'device', id='iio:device0', name='ad9361-phy')
    def attribute(parent, name, value, filename=None):
        values = {'name': name, 'value': str(value)}
        if filename:
            values['filename'] = filename
        ET.SubElement(parent, 'attribute', **values)
    for name, value in {'ensm_mode': 'fdd', 'ensm_mode_available': 'sleep wait alert fdd pinctrl',
                        'in_out_voltage_filter_fir_en': '0',
                        'in_voltage_filter_fir_en': '0', 'out_voltage_filter_fir_en': '0',
                        'filter_fir_config': '',
                        'rx_path_rates': 'BBPLL:983040000 ADC:122880000 R2:61440000 R1:30720000 RF:15360000 RXSAMP:7680000',
                        'tx_path_rates': 'BBPLL:983040000 DAC:122880000 T2:61440000 T1:30720000 TF:15360000 TXSAMP:7680000'}.items():
        attribute(phy, name, value)
    for direction in ('input', 'output'):
        prefix = 'in' if direction == 'input' else 'out'
        channel = ET.SubElement(phy, 'channel', id='voltage0', type=direction)
        for name, value in {'sampling_frequency': rate, 'rf_bandwidth': 250000,
                            'gain_control_mode': 'slow_attack', 'hardwaregain': 30,
                            'quadrature_tracking_en': 1, 'rf_dc_offset_tracking_en': 1,
                            'bb_dc_offset_tracking_en': 1, 'rf_port_select': 'A_BALANCED',
                            'filter_fir_en': 0}.items():
            number = '0' if name in ('gain_control_mode', 'hardwaregain', 'filter_fir_en') else ''
            attribute(channel, name, value, f'{prefix}_voltage{number}_{name}')
    for index in (0, 1):
        lo = ET.SubElement(phy, 'channel', id=f'altvoltage{index}', type='output', name='RX_LO' if index == 0 else 'TX_LO')
        label = 'RX_LO' if index == 0 else 'TX_LO'
        attribute(lo, 'frequency', center, f'out_altvoltage{index}_{label}_frequency')
    adc = ET.SubElement(root, 'device', id='iio:device1', name='cf-ad9361-lpc')
    for index in (0, 1):
        channel = ET.SubElement(adc, 'channel', id=f'voltage{index}', type='input')
        ET.SubElement(channel, 'scan-element', index=str(index), format='le:S12/16>>0')
        attribute(channel, 'sampling_frequency', rate, 'in_voltage_sampling_frequency')
        attribute(channel, 'sampling_frequency_available', f'{rate}', 'in_voltage_sampling_frequency_available')
        attribute(channel, 'calibscale', '1.0', f'in_voltage{index}_calibscale')
        attribute(channel, 'calibphase', '0.0', f'in_voltage{index}_calibphase')
    buffer = ET.SubElement(adc, 'buffer', index='0', direction='in')
    for index in (0, 1):
        ET.SubElement(buffer, 'channel', id=f'voltage{index}', type='input')
    ET.SubElement(adc, 'debug-attribute', name='direct_reg_access', value='0')
    ET.indent(root)
    return ET.ElementTree(root)


def generate(directory, rate, center, scenario, seconds):
    if not 1 <= seconds <= 120:
        raise ValueError('Replay duration must be in [1, 120] seconds')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    engine = Scenario(scenario, rate)
    if any(event['action'] == 'stall' for event in engine.events):
        raise ValueError('Stall scenarios require live synthetic capture; use clean/fading/drift/squelch/qrm for IIO replay')
    xml = ET.tostring(profile(rate, center).getroot(), encoding='unicode')
    (directory/'pluto.xml').write_text(f'<?xml version="1.0"?>\n<!DOCTYPE context [\n{IIO_DTD}\n]>\n{xml}\n')
    with (directory/'cf-ad9361-lpc_buf0.bin').open('wb') as output:
        total = round(seconds*rate)
        for position in range(0, total, 65536):
            count = min(65536, total-position)
            samples = engine.render(position, count)
            data = np.column_stack([samples.real, samples.imag])
            output.write(np.round(np.clip(data, -1, 2047/2048)*2048).astype('<i2').tobytes())
    (directory/'replay.json').write_text(json.dumps({'sample_rate': rate, 'center_hz': center,
        'scenario': scenario, 'seconds': seconds, 'format': 'interleaved little-endian signed 12-bit in 16-bit words'}, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rate', type=int, default=520834)
    parser.add_argument('--center', type=int, default=739700000)
    parser.add_argument('--scenario', default='clean')
    parser.add_argument('--seconds', type=float, default=40)
    args = parser.parse_args()
    generate(args.output, args.rate, args.center, args.scenario, args.seconds)


if __name__ == '__main__':
    main()
