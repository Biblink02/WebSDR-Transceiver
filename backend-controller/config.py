"""Validated receiver/distributor settings. Environment overrides YAML."""
import logging
import os
from pathlib import Path
import yaml

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
CONFIG_PATH = Path(os.getenv('CONFIG_PATH', '/app/config.yaml'))
with CONFIG_PATH.open() as config_file:
    CONFIG = yaml.safe_load(config_file)
if not isinstance(CONFIG, dict):
    raise ValueError('Configuration must be a YAML mapping')


def get_cfg(key, default):
    return os.getenv(key.upper(), CONFIG.get(key, default))


WEB_PORT = int(get_cfg('port', 80))
LISTEN_IP = get_cfg('listen_ip', '0.0.0.0')
SDR_HOST = get_cfg('sdr_host', 'sdr-server')
SDR_IQ_PORT = int(get_cfg('sdr_iq_port', 5000))
IQ_CLIENT_QUEUE_SIZE = int(get_cfg('iq_client_queue_size', 4))
IQ_SEND_TIMEOUT = float(get_cfg('iq_send_timeout', 2))
IQ_STALL_SECONDS = float(get_cfg('iq_stall_seconds', 3))
IQ_SUBBAND_RATE = int(get_cfg('iq_subband_rate', 128000))
full_band_limit = get_cfg('iq_full_band_max_clients', 4)
try:
    if isinstance(full_band_limit, bool) or not isinstance(full_band_limit, (int, str)):
        raise ValueError
    IQ_FULL_BAND_MAX_CLIENTS = int(full_band_limit)
    if IQ_FULL_BAND_MAX_CLIENTS < 0:
        raise ValueError
except ValueError as error:
    raise ValueError('iq_full_band_max_clients must be a nonnegative integer') from error
IQ_INPUT_RATE = int(get_cfg('samp_rate', 520834))
IQ_CENTER = float(get_cfg('lo_freq', 739700000))
IQ_VIEW_LOW = float(get_cfg('view_limit_min', 10489500000)) - float(get_cfg('lnb_lo_freq', 9750000000))
IQ_VIEW_HIGH = float(get_cfg('view_limit_max', 10489900000)) - float(get_cfg('lnb_lo_freq', 9750000000))
if not 1 <= IQ_CLIENT_QUEUE_SIZE <= 64 or not 0.1 <= IQ_SEND_TIMEOUT <= 10:
    raise ValueError('Invalid I/Q queue size or send timeout')
if not 1 <= WEB_PORT <= 65535 or not 1 <= SDR_IQ_PORT <= 65535 or not 0.1 <= IQ_STALL_SECONDS <= 60:
    raise ValueError('Invalid port or I/Q stall timeout')
