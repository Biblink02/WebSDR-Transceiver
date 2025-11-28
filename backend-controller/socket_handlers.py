import logging
from config import SDR_CENTER_FREQ, SDR_SAMPLE_RATE


class SocketHandlers:
    def __init__(self, sio, pool_state, send_audio_func, send_sdr_func):
        self.sio = sio
        self.worker_pool = pool_state['worker_pool']
        self.client_to_worker_map = pool_state['client_to_worker_map']
        self.worker_to_client_map = pool_state['worker_to_client_map']

        # Injected functions to decouple logic from transport details
        self.send_audio = send_audio_func
        # SDR control function (sends commands to sdr-server:5001)
        self.send_sdr = send_sdr_func

        # Hardware configuration needed to calculate offsets
        self.sdr_center_freq = SDR_CENTER_FREQ
        self.sdr_sample_rate = SDR_SAMPLE_RATE

        # Track active users to enable/disable the SDR I/Q stream
        self.connected_users_count = 0

        logging.info(f"SocketHandlers initialized. SDR Center Freq: {self.sdr_center_freq} Hz")

    async def register_events(self):
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('request_audio_worker', self.on_request_audio_worker)
        self.sio.on('release_audio_worker', self.on_release_audio_worker)
        self.sio.on('tune', self.on_tune)

    async def on_connect(self, sid: str, environ: dict):
        self.connected_users_count += 1
        logging.info(f"Client connected {sid}. Users: {self.connected_users_count}")

        # If this is the first user, wake up the central SDR I/Q stream
        if self.connected_users_count == 1:
            logging.info("First user connected: Activating SDR I/Q Stream.")
            # Send command to sdr-server:5001
            await self.send_sdr({"cmd": "start"})

    async def on_disconnect(self, sid: str):
        # Cleanup audio worker assignment if the user had one
        worker_name = self.client_to_worker_map.pop(sid, None)
        if worker_name:
            logging.warning(f"Cleaning up {worker_name} for disconnected client {sid}.")
            await self.send_audio(worker_name, {"cmd": "idle"})
            self.worker_pool[worker_name] = "idle"
            self.worker_to_client_map.pop(worker_name, None)
            # We don't need to manually update connected_users_count here
            # as it will be decremented below.

        # Ensure we only decrement if the count is > 0
        if self.connected_users_count > 0:
            self.connected_users_count -= 1

        logging.info(f"Client disconnected: {sid}. Total users: {self.connected_users_count}")

        # If no users are left, put the central SDR I/Q stream to sleep
        if self.connected_users_count <= 0:
            self.connected_users_count = 0
            logging.info("No users left: Idling SDR I/Q Stream.")
            # Send command to sdr-server:5001
            await self.send_sdr({"cmd": "stop"})

    async def on_request_audio_worker(self, sid: str, data: dict):
        logging.info(f"Client {sid} is requesting an audio worker.")

        if sid in self.client_to_worker_map:
            return

        # Simple First-Available allocation strategy
        assigned_worker = None
        for w, s in self.worker_pool.items():
            if s == 'idle':
                assigned_worker = w
                break

        if not assigned_worker:
            logging.warning(f"No worker available for {sid}.")
            await self.sio.emit("server_full", room=sid)
            return

        # Lock resources
        self.worker_pool[assigned_worker] = sid
        self.client_to_worker_map[sid] = assigned_worker
        self.worker_to_client_map[assigned_worker] = sid

        await self.sio.enter_room(sid, sid)

        # Calculate Offset: The worker operates in baseband, relative to the SDR center
        target_freq = float(data.get("freq", 100.0e6))
        offset = target_freq - self.sdr_center_freq

        await self.send_audio(assigned_worker, {
            "cmd": "tune",
            "freq_offset": offset,
            "bw": float(data.get("bw", 150e3))
        })

        logging.info(f"Assigned {assigned_worker} to {sid}. Offset: {offset}")
        await self.sio.emit("worker_assigned", {"worker": assigned_worker, "freq": target_freq}, room=sid)

    async def on_release_audio_worker(self, sid: str):
        logging.info(f"Client {sid} is releasing its worker.")
        worker_name = self.client_to_worker_map.pop(sid, None)

        if worker_name:
            await self.send_audio(worker_name, {"cmd": "idle"})
            self.worker_pool[worker_name] = "idle"
            self.worker_to_client_map.pop(worker_name, None)
            logging.info(f"Returned {worker_name} to the pool.")
            await self.sio.emit("worker_released", room=sid)

    async def on_tune(self, sid: str, data: dict):
        worker_name = self.client_to_worker_map.get(sid)
        if not worker_name:
            return

        target_freq = float(data.get("freq", 0))
        offset = target_freq - self.sdr_center_freq

        logging.info(f"Client {sid} tuning {worker_name} to {target_freq} (Offset: {offset})")

        await self.send_audio(worker_name, {
            "cmd": "tune",
            "freq_offset": offset,
            "bw": data.get("bw")
        })
