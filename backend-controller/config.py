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
    logging.error(f"Could not load {CONFIG_PATH}: {e}. Using defaults/env vars.")

# --- Helper to safely get values ---
def get_cfg(key, default):
    return CONFIG.get(key, os.getenv(key.upper(), default))

# ==========================================
# ===        System Configuration        ===
# ==========================================

# Web Server
WEB_PORT = int(get_cfg("port", 80)) # Env var PORT or config 'port'
LISTEN_IP = "0.0.0.0"

# Worker Pool
POOL_SIZE = int(get_cfg("pool_size", 3))
WORKER_HEADLESS_SERVICE = get_cfg("worker_headless_service", "audio-workers-headless.default.svc.cluster.local")

# ==========================================
# ===       Network / Ports              ===
# ==========================================

# Control Ports (ZMQ)
WORKER_CONTROL_PORT = int(get_cfg("worker_control_port", 5001))
SDR_CONTROL_PORT = int(get_cfg("sdr_control_port", 5001))

# Data Ports (UDP)
GRAPHICS_LISTEN_PORT = int(get_cfg("graphics_udp_port", 9001))
AUDIO_LISTEN_PORT = int(get_cfg("audio_udp_port", 9002))

# Hostnames
SDR_HOST = get_cfg("sdr_host", "sdr-server")
BACKEND_HOST = get_cfg("backend_host", "backend-controller")

# ==========================================
# ===       Hardware / DSP Physics       ===
# ==========================================

SDR_CENTER_FREQ = float(get_cfg("lo_freq", 739675000))
SDR_SAMPLE_RATE = int(get_cfg("samp_rate", 2000000))

# Frontend Constraints
MAX_BW_LIMIT = int(get_cfg("max_bw_limit", 200000))
MAX_OFFSET_LIMIT = SDR_SAMPLE_RATE / 2

# ==========================================
# ===       Socket.IO Events             ===
# ==========================================
# Mapping flattened config keys to Python Constants

WS_URL = get_cfg("ws_url", "http://localhost")

WS_GRAPHICS_EVENT = get_cfg("ws_graphics_event", "graphics_data")
WS_AUDIO_EVENT = get_cfg("ws_audio_event", "audio_data")

# Backend -> Frontend Events
WS_SERVER_FULL_EVENT = get_cfg("ws_server_full_event", "server_full")
WS_WORKER_ASSIGNED_EVENT = get_cfg("ws_worker_assigned_event", "worker_assigned")
WS_WORKER_RELEASED_EVENT = get_cfg("ws_worker_released_event", "worker_released")
WS_CORRECTION_EVENT = get_cfg("ws_correction_event", "correction_applied")

# Frontend -> Backend Events
WS_CONNECT_EVENT = get_cfg("ws_connect_event", "connect")
WS_DISCONNECT_EVENT = get_cfg("ws_disconnect_event", "disconnect")
WS_REQUEST_WORKER_EVENT = get_cfg("ws_request_worker_event", "request_audio_worker")
WS_DISMISS_WORKER_EVENT = get_cfg("ws_dismiss_worker_event", "dismiss_audio_worker")
WS_TUNE_EVENT = get_cfg("ws_tune_event", "tune")