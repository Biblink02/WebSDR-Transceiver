import logging
from config import (
    SDR_CENTER_FREQ,
    SDR_SAMPLE_RATE,
    MAX_BW_LIMIT,
    MAX_OFFSET_LIMIT,
    WS_CORRECTION_EVENT
)



class SocketHandlers:
    def __init__(self, sio, pool_state, send_audio_func, send_sdr_func):
        self.sio = sio
        self.worker_pool = pool_state["worker_pool"]
        self.client_to_worker_map = pool_state["client_to_worker_map"]
        self.worker_to_client_map = pool_state["worker_to_client_map"]

        self.send_audio = send_audio_func
        self.send_sdr = send_sdr_func

        self.sdr_center_freq = SDR_CENTER_FREQ
        self.sdr_sample_rate = SDR_SAMPLE_RATE
        self.max_bw_limit = MAX_BW_LIMIT
        self.max_offset_limit = MAX_OFFSET_LIMIT

        self.connected_users_count = 0

        logging.info(f"SocketHandlers initialized. SDR Center Freq: {self.sdr_center_freq} Hz")

    async def register_events(self):
        self.sio.on("connect", self.on_connect)
        self.sio.on("disconnect", self.on_disconnect)
        self.sio.on("request_audio_worker", self.on_request_audio_worker)
        self.sio.on("release_audio_worker", self.on_release_audio_worker)
        self.sio.on("tune", self.on_tune)

    # -----------------------------
    # Validation
    # -----------------------------
    def _validate_tune(self, target_freq: float, bandwidth: float):
        """Validate and clamp frequency offset and bandwidth."""
        offset = target_freq - self.sdr_center_freq
        error = None

        if abs(offset) > self.max_offset_limit:
            error = (
                f"Requested frequency {target_freq} Hz exceeds the "
                f"sampling span (±{self.max_offset_limit} Hz)."
            )
            logging.warning(error)
            offset = self.max_offset_limit if offset > 0 else -self.max_offset_limit

        if bandwidth > self.max_bw_limit:
            error = (
                f"Requested bandwidth {bandwidth} Hz exceeds max allowed {self.max_bw_limit} Hz."
            )
            logging.warning(error)
            bandwidth = self.max_bw_limit

        if bandwidth <= 0:
            bandwidth = 10000.0

        return offset, bandwidth, error

    # -----------------------------
    # Connection Handlers
    # -----------------------------
    async def on_connect(self, sid: str, environ: dict):
        self.connected_users_count += 1
        logging.info(f"Client connected {sid}")

        if self.connected_users_count == 1:
            logging.info("Activating SDR I/Q stream")
            await self.send_sdr({"cmd": "start"})

    async def on_disconnect(self, sid: str):
        worker_name = self.client_to_worker_map.pop(sid, None)

        if worker_name:
            await self.send_audio(worker_name, {"cmd": "idle"})
            self.worker_pool[worker_name] = "idle"
            self.worker_to_client_map.pop(worker_name, None)

        if self.connected_users_count > 0:
            self.connected_users_count -= 1

        logging.info(f"Client disconnected: {sid}")

        if self.connected_users_count == 0:
            logging.info("Idling SDR I/Q stream")
            await self.send_sdr({"cmd": "stop"})

    # -----------------------------
    # Worker Allocation
    # -----------------------------
    async def on_request_audio_worker(self, sid: str, data: dict):
        if sid in self.client_to_worker_map:
            return

        assigned_worker = None
        for w, state in self.worker_pool.items():
            if state == "idle":
                assigned_worker = w
                break

        if not assigned_worker:
            await self.sio.emit("server_full", room=sid)
            return

        self.worker_pool[assigned_worker] = sid
        self.client_to_worker_map[sid] = assigned_worker
        self.worker_to_client_map[assigned_worker] = sid

        await self.sio.enter_room(sid, sid)

        target_freq = float(data.get("freq", self.sdr_center_freq))
        bw = float(data.get("bw", 150e3))

        offset, validated_bw, error = self._validate_tune(target_freq, bw)

        await self.send_audio(
            assigned_worker,
            {"cmd": "tune", "freq_offset": offset, "bw": validated_bw},
        )

        resp = {"worker": assigned_worker, "freq": target_freq}
        if error:
            resp["error"] = error

        await self.sio.emit("worker_assigned", resp, room=sid)

    # -----------------------------
    # Tune Command
    # -----------------------------
    async def on_tune(self, sid: str, data: dict):
        worker_name = self.client_to_worker_map.get(sid)
        if not worker_name:
            return

        target_freq = float(data.get("freq", self.sdr_center_freq))
        bw = float(data.get("bw", 150e3))

        offset, validated_bw, error = self._validate_tune(target_freq, bw)

        await self.send_audio(
            worker_name,
            {"cmd": "tune", "freq_offset": offset, "bw": validated_bw},
        )

        if error:
            await self.sio.emit(
                WS_CORRECTION_EVENT,
                {"message": error, "freq": target_freq, "bw": validated_bw},
                room=sid,
            )

    # -----------------------------
    # Release Worker
    # -----------------------------
    async def on_release_audio_worker(self, sid: str):
        worker_name = self.client_to_worker_map.pop(sid, None)

        if worker_name:
            await self.send_audio(worker_name, {"cmd": "idle"})
            self.worker_pool[worker_name] = "idle"
            self.worker_to_client_map.pop(worker_name, None)
            await self.sio.emit("worker_released", room=sid)
