import logging


class SocketHandlers:
    def __init__(self, sio, pool_state, send_control_cmd_func):
        """
        Initialize the handlers with the app's shared state and functions.
        """
        self.sio = sio
        self.worker_pool = pool_state['worker_pool']
        self.client_to_worker_map = pool_state['client_to_worker_map']
        self.worker_to_client_map = pool_state['worker_to_client_map']
        self.send_control_command = send_control_cmd_func
        logging.info("SocketHandlers initialized.")

    async def register_events(self):
        """Registers all event handlers with the Socket.IO server."""
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('request_audio_worker', self.on_request_audio_worker)
        self.sio.on('release_audio_worker', self.on_release_audio_worker)
        self.sio.on('tune', self.on_tune)
        logging.info("Socket.IO events registered.")

    # --- Event Handlers (Moved from backend_controller.py) ---

    async def on_connect(self, sid: str, environ: dict):
        """Client connected, ready for graphics."""
        logging.info(f"Client connected {sid}, waiting for commands.")

    async def on_disconnect(self, sid: str):
        """Client disconnected. Safety net cleanup."""
        logging.info(f"Client disconnected: {sid}")

        # Check if they had a worker and clean it up
        worker_name = self.client_to_worker_map.pop(sid, None)
        if worker_name:
            logging.warning(f"Cleaning up {worker_name} for disconnected client {sid}.")
            await self.send_control_command(worker_name, {"cmd": "idle"})
            self.worker_pool[worker_name] = "idle"
            self.worker_to_client_map.pop(worker_name, None)

    async def on_request_audio_worker(self, sid: str, data: dict):
        """Client pressed "Play". Assign a worker."""
        logging.info(f"Client {sid} is requesting an audio worker.")

        if sid in self.client_to_worker_map:
            logging.warning(f"Client {sid} already has a worker. Ignoring.")
            return

        assigned_worker = None
        for worker_name, status in self.worker_pool.items():
            if status == 'idle':
                assigned_worker = worker_name
                break

        if assigned_worker is None:
            logging.warning(f"No worker available for {sid}.")
            await self.sio.emit("server_full", room=sid)
            return

        self.worker_pool[assigned_worker] = sid
        self.client_to_worker_map[sid] = assigned_worker
        self.worker_to_client_map[assigned_worker] = sid
        await self.sio.join_room(sid, room=sid)

        client_freq = data.get("freq", 100.0e6)
        client_bw = data.get("bw", 150e3)
        await self.send_control_command(assigned_worker, {
            "cmd": "tune",
            "freq": client_freq,
            "bw": client_bw
        })

        logging.info(f"Assigned {assigned_worker} to {sid} at {client_freq} Hz")
        await self.sio.emit("worker_assigned", {"worker": assigned_worker, "freq": client_freq}, room=sid)

    async def on_release_audio_worker(self, sid: str):
        """Client pressed "Stop". Return the worker."""
        logging.info(f"Client {sid} is releasing its worker.")

        worker_name = self.client_to_worker_map.pop(sid, None)

        if worker_name:
            await self.send_control_command(worker_name, {"cmd": "idle"})
            self.worker_pool[worker_name] = "idle"
            self.worker_to_client_map.pop(worker_name, None)

            logging.info(f"Returned {worker_name} to the pool.")
            await self.sio.emit("worker_released", room=sid)
        else:
            logging.warning(f"Client {sid} tried to release a worker but had none.")

    async def on_tune(self, sid: str, data: dict):
        """Forward tune commands."""
        worker_name = self.client_to_worker_map.get(sid)
        if not worker_name:
            logging.error(f"Tune event from {sid} failed: No worker assigned.")
            return

        logging.info(f"Client {sid} tuning {worker_name} to {data}")
        await self.send_control_command(worker_name, {
            "cmd": "tune",
            "freq": data.get("freq"),
            "bw": data.get("bw")
        })