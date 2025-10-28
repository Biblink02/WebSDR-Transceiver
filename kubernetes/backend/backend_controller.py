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

# --- Configuration (from Environment Variables) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Web server config
LISTEN_IP = "0.0.0.0"
WEB_PORT = int(os.environ.get("PORT", 8080))  # Port for web/Socket.IO (from Ingress)

# Worker Pool config (must match StatefulSet YAML)
POOL_SIZE = int(os.environ.get("POOL_SIZE", 3))
WORKER_HEADLESS_SERVICE = os.environ.get("WORKER_HEADLESS_SERVICE", "audio-workers-headless.default.svc.cluster.local")
WORKER_CONTROL_PORT = int(os.environ.get("WORKER_CONTROL_PORT", 5001))

# Data port config (must match YAML)
GRAPHICS_LISTEN_PORT = int(os.environ.get("GRAPHICS_PORT", 9001))  # UDP
AUDIO_LISTEN_PORT = int(os.environ.get("AUDIO_PORT", 9002))  # UDP

# --- Application State ---
# Group state into a single dictionary for easier sharing
app_state = {
    # Tracks the state of each worker
    "worker_pool": {f"audio-worker-{i}": "idle" for i in range(POOL_SIZE)},

    # Maps a client 'sid' to their assigned worker
    "client_to_worker_map": {},

    # Maps a worker name back to a client 'sid' for fast audio routing
    "worker_to_client_map": {}
}

# --- ZMQ Worker Control ---

# Global ZMQ context for asyncio
zmq_context = zmq.asyncio.Context()
# Cache for ZMQ sockets to each worker (ZMQ PUSH pattern)
zmq_sockets = {}


async def send_control_command(worker_name: str, command: dict):
    """Sends a JSON command (tune, idle) to a specific worker via ZMQ."""
    try:
        if worker_name not in zmq_sockets:
            # Create and cache a new socket for this worker
            logging.info(f"Creating ZMQ PUSH socket for {worker_name}...")
            socket = zmq_context.socket(zmq.PUSH)
            # Use the worker's stable Kubernetes DNS name
            worker_address = f"tcp://{worker_name}.{WORKER_HEADLESS_SERVICE}:{WORKER_CONTROL_PORT}"
            socket.connect(worker_address)
            zmq_sockets[worker_name] = socket
            await asyncio.sleep(0.5)  # Give ZMQ time to connect

        socket = zmq_sockets[worker_name]
        logging.info(f"Sending command to {worker_name}: {command}")
        await socket.send_json(command)

    except Exception as e:
        logging.error(f"Failed to send command to {worker_name}: {e}")
        # If send fails, remove socket from cache; it will be recreated
        if worker_name in zmq_sockets:
            zmq_sockets.pop(worker_name).close()


# --- UDP Data Handlers (Receiving Audio & Graphics) ---

class GraphicsUdpProtocol(asyncio.DatagramProtocol):
    """Receives graphics data and broadcasts it to ALL clients."""

    def __init__(self, sio_server: socketio.AsyncServer):
        self.sio_server = sio_server
        self.loop = asyncio.get_running_loop()
        super().__init__()

    def datagram_received(self, data: bytes, addr: tuple):
        # Broadcast graphics data to everyone
        self.loop.create_task(self.sio_server.emit('graphics_data', data))

    def error_received(self, exc: Exception):
        logging.error(f"Graphics UDP error: {exc}")


class AudioUdpProtocol(asyncio.DatagramProtocol):
    """Receives audio data and routes it to a SPECIFIC client."""

    def __init__(self, sio_server: socketio.AsyncServer, state: dict):
        self.sio_server = sio_server
        # Get the shared map from the application state
        self.worker_to_client_map = state['worker_to_client_map']
        self.loop = asyncio.get_running_loop()
        super().__init__()

    # TODO depends on gnuradio actual config for the audio
    def datagram_received(self, data: bytes, addr: tuple):
        """
        Here we assume data format: b'worker-name:audio-payload'
        e.g., b'audio-worker-5:....[raw audio]....'
        """
        try:
            # Parse the message
            worker_name_bytes, audio_data = data.split(b':', 1)
            worker_name = worker_name_bytes.decode('utf-8')

            # Find the client (sid) mapped to this worker
            sid = self.worker_to_client_map.get(worker_name)

            # If a client is mapped, send them the audio
            if sid:
                # Send to the client's private room
                self.loop.create_task(self.sio_server.emit('audio_data', audio_data, room=sid))

        except ValueError:
            logging.warning("Received malformed audio UDP packet.")
        except Exception as e:
            logging.error(f"Audio routing error: {e}")

    def error_received(self, exc: Exception):
        logging.error(f"Audio UDP error: {exc}")


# --- FastAPI & Socket.IO Setup ---

# Create the Socket.IO server first
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')


# This "lifespan" manager starts the UDP servers when FastAPI starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Application starting up...")
    loop = asyncio.get_running_loop()

    # Start Graphics UDP Listener (broadcast)
    await loop.create_datagram_endpoint(
        lambda: GraphicsUdpProtocol(sio_server=sio),
        local_addr=(LISTEN_IP, GRAPHICS_LISTEN_PORT)
    )
    logging.info(f"Graphics UDP server listening on udp://{LISTEN_IP}:{GRAPHICS_LISTEN_PORT}")

    # Start Audio UDP Listener (private routing)
    await loop.create_datagram_endpoint(
        # Pass the shared app_state to the protocol
        lambda: AudioUdpProtocol(sio_server=sio, state=app_state),
        local_addr=(LISTEN_IP, AUDIO_LISTEN_PORT)
    )
    logging.info(f"Audio UDP server listening on udp://{LISTEN_IP}:{AUDIO_LISTEN_PORT}")

    # --- Instantiate and Register Socket.IO Handlers ---
    handlers = SocketHandlers(
        sio=sio,
        pool_state=app_state,
        send_control_cmd_func=send_control_command
    )
    await handlers.register_events()

    yield  # The application is now running

    # --- Shutdown ---
    logging.info("Application shutting down...")
    zmq_context.term()


# Create the FastAPI app with the lifespan manager
app = FastAPI(lifespan=lifespan)

# Mount the Socket.IO server onto the FastAPI app
app.mount("/socket.io", socketio.ASGIApp(sio))

# --- Static File Server ---
# Serve your index.html, JS, and CSS files #TODO
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# --- Main Runner ---
if __name__ == "__main__":
    logging.info(f"Starting server on http://{LISTEN_IP}:{WEB_PORT}")
    uvicorn.run(app, host=LISTEN_IP, port=WEB_PORT)