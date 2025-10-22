import asyncio
import logging
import socketio
import os
from aiohttp import web

# --- Configuration ---
CONFIG = {
    "DATA_PORT": 8000,
    "WEB_PORT": 8001,
    "LISTEN_IP": "0.0.0.0",
    "UPDATE_EVENT": os.environ.get('WEBSOCKET_UPDATE_EVENT') or 'update'
}

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')

app = web.Application()

sio.attach(app)


# --- Socket.IO Event Handlers ---

@sio.event
async def connect(sid: str, environ: dict):
    """This event is automatically called when a client connects."""
    logging.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid: str):
    """This event is automatically called when a client disconnects."""
    logging.info(f"Client disconnected: {sid}")


# --- UDP Data Source Handler (Protocol) ---

class UdpDataProtocol(asyncio.DatagramProtocol):
    """
    Handles incoming UDP datagrams and forwards the data
    to all connected clients via Socket.IO.
    """
    def __init__(self, sio_server: socketio.AsyncServer):
        self.sio_server = sio_server
        self.loop = asyncio.get_running_loop()
        super().__init__()

    def connection_made(self, transport: asyncio.DatagramTransport):
        """Called when the endpoint is set up."""
        logging.info("UDP endpoint is active.")

    def datagram_received(self, data: bytes, addr: tuple):
        """Called when a UDP datagram is received."""
        logging.info(f"UDP Data received from {addr}: {data}")

        self.loop.create_task(self.sio_server.emit(CONFIG['UPDATE_EVENT'], data))

    def error_received(self, exc: Exception):
        """Called when an error occurs."""
        logging.error(f"UDP error received: {exc}")

    def connection_lost(self, exc: Exception | None):
        """Called when the endpoint is closed (e.g., on server shutdown)."""
        logging.info("UDP endpoint closed.")


# --- Main Application Runner ---

async def main():
    """Starts the UDP server and the web server with Socket.IO."""

    loop = asyncio.get_running_loop()

    protocol_factory = lambda: UdpDataProtocol(sio_server=sio)

    await loop.create_datagram_endpoint(
        protocol_factory,
        local_addr=(CONFIG["LISTEN_IP"], CONFIG["DATA_PORT"])
    )
    logging.info(f"UDP server listening on udp://{CONFIG['LISTEN_IP']}:{CONFIG['DATA_PORT']}")

    # Set up and start the aiohttp web server that hosts Socket.IO.
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, CONFIG["LISTEN_IP"], CONFIG["WEB_PORT"])
    await site.start()
    logging.info(f"Socket.IO server listening on http://{CONFIG['LISTEN_IP']}:{CONFIG['WEB_PORT']}")

    # Keep the servers running indefinitely.
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Servers shutting down.")