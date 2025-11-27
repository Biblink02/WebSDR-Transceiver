import asyncio
import logging
import os
import socketio
import uvicorn
import zmq
import zmq.asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from socket_handlers import SocketHandlers

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LISTEN_IP = "0.0.0.0"
WEB_PORT = int(os.environ.get("PORT", 8080))

# Worker Pool config
POOL_SIZE = int(os.environ.get("POOL_SIZE", 3))
WORKER_HEADLESS_SERVICE = os.environ.get("WORKER_HEADLESS_SERVICE", "audio-workers-headless.default.svc.cluster.local")
WORKER_CONTROL_PORT = int(os.environ.get("WORKER_CONTROL_PORT", 5001))

# Graphics Worker Config (Standard Service)
GRAPHICS_WORKER_HOST = "graphics-worker"

# Data ports
GRAPHICS_LISTEN_PORT = int(os.environ.get("GRAPHICS_PORT", 9001))
AUDIO_LISTEN_PORT = int(os.environ.get("AUDIO_PORT", 9002))

# --- Application State ---
app_state = {
    "worker_pool": {f"audio-worker-{i}": "idle" for i in range(POOL_SIZE)},
    "client_to_worker_map": {},
    "worker_to_client_map": {}
}

# --- ZMQ Control Logic ---

zmq_context = zmq.asyncio.Context()
zmq_sockets = {}

async def _send_zmq_packet(target_id: str, address: str, command: dict):
    """
    Private helper: Handles the raw ZMQ connection and data sending.
    It manages the socket cache to avoid recreating connections on every command.
    """
    try:
        if target_id not in zmq_sockets:
            logging.info(f"Connecting ZMQ to {target_id} at {address}...")
            socket = zmq_context.socket(zmq.PUSH)
            socket.connect(address)
            zmq_sockets[target_id] = socket
            # Allow time for the handshake to complete before sending
            await asyncio.sleep(0.1)

        socket = zmq_sockets[target_id]
        await socket.send_json(command)

    except Exception as e:
        logging.error(f"ZMQ Error sending to {target_id}: {e}")
        # Invalid sockets must be removed to force reconnection next time
        if target_id in zmq_sockets:
            zmq_sockets.pop(target_id).close()

# --- Public Control API ---

async def send_audio_command(worker_id: str, command: dict):
    """
    Routes commands to a specific Audio Worker within the StatefulSet.
    Requires constructing the full K8s DNS name for the specific pod.
    """
    address = f"tcp://{worker_id}.{WORKER_HEADLESS_SERVICE}:{WORKER_CONTROL_PORT}"
    await _send_zmq_packet(worker_id, address, command)

async def send_graphics_command(command: dict):
    """
    Routes commands to the single Graphics Worker Service.
    """
    address = f"tcp://{GRAPHICS_WORKER_HOST}:{WORKER_CONTROL_PORT}"
    await _send_zmq_packet("graphics-worker", address, command)

# --- UDP Data Handlers ---

class GraphicsUdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, sio_server: socketio.AsyncServer):
        self.sio_server = sio_server
        self.loop = asyncio.get_running_loop()
        super().__init__()

    def datagram_received(self, data: bytes, addr: tuple):
        # Graphics data is broadcast to all connected clients
        self.loop.create_task(self.sio_server.emit('graphics_data', data))

    def error_received(self, exc: Exception):
        logging.error(f"Graphics UDP error: {exc}")

class AudioUdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, sio_server: socketio.AsyncServer, state: dict):
        self.sio_server = sio_server
        self.worker_to_client_map = state['worker_to_client_map']
        self.loop = asyncio.get_running_loop()
        super().__init__()

    def datagram_received(self, data: bytes, addr: tuple):
        """
        Expects format: b'worker-name:audio-payload'
        Routes audio only to the specific client assigned to that worker.
        """
        try:
            worker_name_bytes, audio_data = data.split(b':', 1)
            worker_name = worker_name_bytes.decode('utf-8')

            sid = self.worker_to_client_map.get(worker_name)

            if sid:
                self.loop.create_task(self.sio_server.emit('audio_data', audio_data, room=sid))

        except ValueError:
            pass
        except Exception as e:
            logging.error(f"Audio routing error: {e}")

    def error_received(self, exc: Exception):
        logging.error(f"Audio UDP error: {exc}")

# --- Setup & Lifespan ---

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Application starting up...")
    loop = asyncio.get_running_loop()

    # 1. Start UDP Listeners
    await loop.create_datagram_endpoint(
        lambda: GraphicsUdpProtocol(sio_server=sio),
        local_addr=(LISTEN_IP, GRAPHICS_LISTEN_PORT)
    )
    logging.info(f"Graphics UDP server listening on :{GRAPHICS_LISTEN_PORT}")

    await loop.create_datagram_endpoint(
        lambda: AudioUdpProtocol(sio_server=sio, state=app_state),
        local_addr=(LISTEN_IP, AUDIO_LISTEN_PORT)
    )
    logging.info(f"Audio UDP server listening on :{AUDIO_LISTEN_PORT}")

    # 2. Init Logic Handlers (Injecting the specific send functions)
    handlers = SocketHandlers(
        sio=sio,
        pool_state=app_state,
        send_audio_func=send_audio_command,
        send_graphics_func=send_graphics_command
    )
    await handlers.register_events()

    yield

    logging.info("Application shutting down...")
    zmq_context.term()

app = FastAPI(lifespan=lifespan)
app.mount("/socket.io", socketio.ASGIApp(sio))
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    logging.info(f"Starting server on http://{LISTEN_IP}:{WEB_PORT}")
    uvicorn.run(app, host=LISTEN_IP, port=WEB_PORT)