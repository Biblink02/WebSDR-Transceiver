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
if not 1 <= IQ_CLIENT_QUEUE_SIZE <= 64 or not 0.1 <= IQ_SEND_TIMEOUT <= 10:
    raise ValueError('Invalid I/Q queue size or send timeout')
if not 1 <= WEB_PORT <= 65535 or not 1 <= SDR_IQ_PORT <= 65535 or not 0.1 <= IQ_STALL_SECONDS <= 60:
    raise ValueError('Invalid port or I/Q stall timeout')
