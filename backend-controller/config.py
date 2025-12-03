import os
import yaml
import logging

# Configure logging early
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_PATH = "/app/config.yaml"
CONFIG = {}

try:
    with open(CONFIG_PATH, "r") as f:
        CONFIG = yaml.safe_load(f)
        logging.info(f"Loaded configuration from {CONFIG_PATH}")
except Exception as e:
    logging.error(f"Could not load {CONFIG_PATH}: {e}. Using environment variables/defaults.")

# --- Extract Constants with Fallbacks ---

# Web Server
WEB_PORT = int(CONFIG.get("PORT", 80))
LISTEN_IP = "0.0.0.0"

# Pool Config
POOL_SIZE = int(CONFIG.get("POOL_SIZE", 3))
WORKER_HEADLESS_SERVICE = CONFIG.get("WORKER_HEADLESS_SERVICE", "audio-workers-headless.default.svc.cluster.local")

# ZMQ Control Ports
WORKER_CONTROL_PORT = int(CONFIG.get("WORKER_CONTROL_PORT", 5001))
SDR_CONTROL_PORT = int(CONFIG.get("SDR_CONTROL_PORT", 5001))

# Data Ports
GRAPHICS_LISTEN_PORT = int(CONFIG.get("GRAPHICS_UDP_PORT", 9001))
AUDIO_LISTEN_PORT = int(CONFIG.get("AUDIO_UDP_PORT", 9002))

# Hosts
SDR_HOST = CONFIG.get("SDR_HOST", "sdr-server")
GRAPHICS_WORKER_HOST = "graphics-worker"

# Hardware / DSP Defaults
SDR_CENTER_FREQ = float(CONFIG.get("lo_freq", 2450000000))
SDR_SAMPLE_RATE = int(CONFIG.get("sample_rate", 2000000))

# --- Socket.IO Events ---
WS_GRAPHICS_EVENT = CONFIG.get("WS_GRAPHICS_EVENT", "graphics_data")
WS_AUDIO_EVENT = CONFIG.get("WS_AUDIO_EVENT", "audio_data")
WS_CORRECTION_EVENT = CONFIG.get("WS_CORRECTION_EVENT", "correction_applied")


# Validation
MAX_BW_LIMIT = int(CONFIG.get("MAX_BW_LIMIT", 200000))
# Maximum frequency offset allowed from the SDR_CENTER_FREQ (should be half the sample rate)
MAX_OFFSET_LIMIT = SDR_SAMPLE_RATE / 2