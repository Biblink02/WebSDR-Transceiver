import asyncio
import logging
import socketio
from aiohttp import web
from functools import partial
from typing import Coroutine, Callable

# --- Configuration ---
CONFIG = {
    "DATA_PORT": 8000,
    "WEB_PORT": 8001,
    "LISTEN_IP": "0.0.0.0",
}

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 1. Create an instance of the Socket.IO asynchronous server.
#    CORS (Cross-Origin Resource Sharing) is allowed from all origins ('*').
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')

# 2. Create an aiohttp web application.
app = web.Application()

# 3. Attach the Socket.IO server to the web application.
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


# --- TCP Data Source Handler ---

async def tcp_data_handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        sio_server: socketio.AsyncServer
):
    """
    Handles the connection from the data source and forwards the data
    to all connected clients via Socket.IO.
    """
    peername = writer.get_extra_info('peername')
    logging.info(f"Data source connected from {peername}")

    try:
        while True:
            # Read a chunk of data from the TCP socket.
            data = await reader.read(1024)
            if not data:
                # An empty bytes object means the connection was closed by the peer.
                break

            # 4. Broadcast the received data to ALL connected Socket.IO clients.
            #    'data_update' is the custom event name the client will listen for.
            await sio_server.emit('data_update', data)

    except Exception:
        logging.exception(f"An error occurred with the data source {peername}")
    finally:
        logging.info(f"Data source {peername} disconnected.")
        writer.close()
        await writer.wait_closed()


# --- Main Application Runner ---

async def main():
    """Starts the TCP server and the web server with Socket.IO."""

    # Create a partial function to pass the 'sio' instance to the handler.
    handler: Callable[..., Coroutine] = partial(tcp_data_handler, sio_server=sio)

    # Start the TCP server to listen for the data source.
    tcp_server = await asyncio.start_server(handler, CONFIG["LISTEN_IP"], CONFIG["DATA_PORT"])
    logging.info(f"TCP server listening on tcp://{CONFIG['LISTEN_IP']}:{CONFIG['DATA_PORT']}")

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