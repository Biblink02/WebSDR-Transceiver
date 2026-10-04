"""Shared C++ I/Q subbands; listener demodulation runs in the browser."""
import asyncio
from contextlib import asynccontextmanager, suppress
import uvicorn
import zmq.asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from config import (WEB_PORT, LISTEN_IP, SDR_HOST, SDR_IQ_PORT,
                    IQ_CLIENT_QUEUE_SIZE, IQ_SEND_TIMEOUT, IQ_STALL_SECONDS,
                    IQ_SUBBAND_RATE, IQ_INPUT_RATE, IQ_CENTER, IQ_VIEW_LOW, IQ_VIEW_HIGH)
from iq import IQDistributor
from subbands import FULL_BAND, native_library


@asynccontextmanager
async def lifespan(app):
    native_library()  # Required: fail startup rather than serving an unfiltered stream.
    context = zmq.asyncio.Context()
    distributor = IQDistributor(context, f'tcp://{SDR_HOST}:{SDR_IQ_PORT}', IQ_CLIENT_QUEUE_SIZE,
                                input_rate=IQ_INPUT_RATE, center=IQ_CENTER, view_low=IQ_VIEW_LOW,
                                view_high=IQ_VIEW_HIGH, subband_rate=IQ_SUBBAND_RATE)
    app.state.iq = distributor
    task = asyncio.create_task(distributor.run(), name='iq-subscriber')
    app.state.subscriber = task
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        context.term()


app = FastAPI(lifespan=lifespan)


@app.get('/health')
async def health():
    # A source stall makes this replica unready but must not restart healthy backends.
    if app.state.subscriber.done():
        return JSONResponse({'status': 'subscriber failed'}, status_code=503)
    return {'status': 'ok'}


@app.get('/ready')
async def ready():
    if not app.state.iq.clients and not app.state.subscriber.done():
        # Idle replicas must accept the first viewer so they can wake the source.
        return {'status': 'idle'}
    age = app.state.iq.diagnostics()['packet_age_seconds']
    if age is None or age > IQ_STALL_SECONDS or app.state.subscriber.done():
        return JSONResponse({'status': 'waiting for I/Q'}, status_code=503)
    return {'status': 'ok'}


@app.get('/stream-info')
async def stream_info():
    return app.state.iq.diagnostics()


@app.get('/bands')
async def bands():
    return app.state.iq.plan.json()


@app.websocket('/iq')
async def iq_socket(websocket: WebSocket):
    distributor = app.state.iq
    try:
        selection = websocket.query_params.get('band', str(distributor.plan.default))
        band = FULL_BAND if selection == FULL_BAND else int(selection)
        distributor.plan.get_band(band)
    except ValueError:
        await websocket.close(code=1008, reason='Unknown I/Q receive band')
        return
    await websocket.accept()
    queue = distributor.subscribe(band)

    async def receive():
        while True:
            message = await websocket.receive()
            if message['type'] == 'websocket.disconnect':
                return
            # The route is receive-only; tuning and playback controls remain local.
            await websocket.close(code=1003, reason='I/Q stream is receive-only')
            return

    async def transmit():
        while True:
            frame = await queue.get()
            await asyncio.wait_for(websocket.send_bytes(frame), IQ_SEND_TIMEOUT)

    tasks = [asyncio.create_task(receive()), asyncio.create_task(transmit())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
        pass
    finally:
        distributor.unsubscribe(queue)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        with suppress(Exception):
            await websocket.close()


if __name__ == '__main__':
    uvicorn.run(app, host=LISTEN_IP, port=WEB_PORT, ws_max_size=1024, ws_max_queue=1)
