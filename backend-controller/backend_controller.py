import asyncio
import logging
import socketio
import uvicorn
import zmq
import zmq.asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from socket_handlers import SocketHandlers

# Import configuration from the dedicated module
from config import (
    WEB_PORT, LISTEN_IP, POOL_SIZE, WORKER_HEADLESS_SERVICE,
    WORKER_CONTROL_PORT, SDR_CONTROL_PORT,
    GRAPHICS_LISTEN_PORT, AUDIO_LISTEN_PORT, SDR_HOST,
    WS_GRAPHICS_EVENT, WS_AUDIO_EVENT
)

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
            await asyncio.sleep(0.1)  # Wait for handshake

        socket = zmq_sockets[target_id]
        await socket.send_json(command)

    except Exception as e:
        logging.error(f"ZMQ Error sending to {target_id}: {e}")
        if target_id in zmq_sockets:
            zmq_sockets.pop(target_id).close()


# --- Public Control API ---

async def send_audio_command(worker_id: str, command: dict):
    """
    Routes commands to a specific Audio Worker within the StatefulSet.
    """
    address = f"tcp://{worker_id}.{WORKER_HEADLESS_SERVICE}:{WORKER_CONTROL_PORT}"
    await _send_zmq_packet(worker_id, address, command)


async def send_sdr_command(command: dict):
    """
    Routes commands to the central SDR Server control port (5001).
    """
    address = f"tcp://{SDR_HOST}:{SDR_CONTROL_PORT}"
    await _send_zmq_packet("sdr-server", address, command)


# --- UDP Data Handlers ---

class GraphicsUdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, sio_server: socketio.AsyncServer):
        self.sio_server = sio_server
        self.loop = asyncio.get_running_loop()
        super().__init__()

    def datagram_received(self, data: bytes, addr: tuple):
        self.loop.create_task(self.sio_server.emit(WS_GRAPHICS_EVENT, data))

    def error_received(self, exc: Exception):
        logging.error(f"Graphics UDP error: {exc}")


class AudioUdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, sio_server: socketio.AsyncServer, state: dict):
        self.sio_server = sio_server
        self.worker_to_client_map = state['worker_to_client_map']
        self.loop = asyncio.get_running_loop()
        super().__init__()

    def datagram_received(self, data: bytes, addr: tuple):
        try:
            mv = memoryview(data)
            sep = data.find(b':')

            if sep < 0:
                return

            worker_name = mv[:sep].tobytes().decode('utf-8')

            sid = self.worker_to_client_map.get(worker_name)
            if not sid:
                return

            audio_data = mv[sep + 1:].tobytes()

            self.loop.create_task(self.sio_server.emit(WS_AUDIO_EVENT, audio_data, room=sid))

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

    # 2. Init Logic Handlers
    handlers = SocketHandlers(
        sio=sio,
        pool_state=app_state,
        send_audio_func=send_audio_command,
        send_sdr_func=send_sdr_command
    )
    await handlers.register_events()

    yield

    logging.info("Application shutting down...")
    zmq_context.term()


app = FastAPI(lifespan=lifespan)
combined_app = socketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == "__main__":
    logging.info(f"Starting server on http://{LISTEN_IP}:{WEB_PORT}")
    uvicorn.run(combined_app, host=LISTEN_IP, port=WEB_PORT)