#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# UDP → Socket.IO bridge + built-in waterfall page
#
# GNU Radio path (example):
#   ... → Vector to Stream (Float, N=FFT_LEN)
#       → Stream to Tagged Stream (Float, packet_len=FFT_LEN, tag="packet_len")
#       → Tagged Stream to PDU (Float, len_tag="packet_len")
#       → Socket PDU (UDP_CLIENT, host=<bridge ip>, port=DATA_PORT)
#
# Run:  python3 udp_fft_bridge.py
# Open: http://localhost:8001/
#
import os
import asyncio
import logging
import socketio
from aiohttp import web

# ---------------- Configuration (env overrides) ----------------
LISTEN_IP   = os.getenv("LISTEN_IP", "0.0.0.0")
DATA_PORT   = int(os.getenv("DATA_PORT", "8000"))   # UDP from GNU Radio
WEB_PORT    = int(os.getenv("WEB_PORT", "8001"))    # HTTP/Socket.IO for browser
EMIT_EVERY  = int(os.getenv("EMIT_EVERY", "1"))     # forward every Nth UDP packet (UI throttle)

# Optional expected FFT length; used only for logs. If 0, accept any size.
FFT_LEN     = int(os.getenv("FFT_LEN", "1024"))
FRAME_BYTES = FFT_LEN * 4 if FFT_LEN > 0 else 0

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------- Socket.IO + aiohttp ----------------
sio = socketio.AsyncServer(async_mode="aiohttp", cors_allowed_origins="*")
app = web.Application()
sio.attach(app)

# ---------------- HTML (served at "/") ----------------
INDEX_HTML = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Live Waterfall</title>
  <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
  <style>
    :root {{ --h: 512; }}
    body {{ font-family: system-ui, sans-serif; margin: 12px; }}
    #top {{ display:flex; gap:12px; align-items:center; flex-wrap: wrap; }}
    #waterfall {{ border:1px solid #ccc; image-rendering: pixelated; width: min(95vw, 1100px); height: calc(min(95vw,1100px)*0.35); }}
    label {{ font-size: 12px; color:#444; }}
    input[type="range"] {{ width: 160px; vertical-align: middle; }}
    .pill {{ padding:4px 8px; border:1px solid #ddd; border-radius: 999px; }}
  </style>
</head>
<body>
  <h2>Waterfall (UDP → Socket.IO)</h2>
  <div id="top">
    <span class="pill">Status: <strong id="status">disconnected</strong></span>
    <span class="pill">FPS: <strong id="fps">0</strong></span>
    <span class="pill">Frame bytes: <strong id="sz">0</strong></span>
    <label class="pill">dB min
      <input id="dbmin" type="range" min="-160" max="-20" step="1" value="-120">
      <span id="dbminv">-120</span>
    </label>
    <label class="pill">dB max
      <input id="dbmax" type="range" min="-140" max="0" step="1" value="-20">
      <span id="dbmaxv">-20</span>
    </label>
    <label class="pill">
      Colormap
      <select id="cmap">
        <option value="turbo" selected>Turbo</option>
        <option value="grayscale">Grayscale</option>
      </select>
    </label>
    <button id="pause" class="pill">Pause</button>
    <span class="pill">FFT_LEN: <strong id="nfft">auto</strong></span>
  </div>

  <canvas id="waterfall" width="{FFT_LEN if FFT_LEN>0 else 1024}" height="512"></canvas>

  <script>
    const SERVER = location.origin;      // same host:port
    const CANVAS_H = 512;

    const statusEl = document.getElementById('status');
    const fpsEl = document.getElementById('fps');
    const sizeEl = document.getElementById('sz');
    const nfftEl = document.getElementById('nfft');
    const dbminEl = document.getElementById('dbmin');
    const dbmaxEl = document.getElementById('dbmax');
    const dbminV = document.getElementById('dbminv');
    const dbmaxV = document.getElementById('dbmaxv');
    const cmapSel = document.getElementById('cmap');
    const pauseBtn = document.getElementById('pause');

    const canvas = document.getElementById('waterfall');
    const ctx = canvas.getContext('2d', {{ alpha:false }});

    let paused = false;
    pauseBtn.onclick = () => {{ paused = !paused; pauseBtn.textContent = paused ? 'Resume' : 'Pause'; }};

    function setCanvasWidth(nfft) {{
      if (canvas.width !== nfft) {{
        canvas.width = nfft;
        canvas.height = CANVAS_H;
        ctx.fillStyle = '#000';
        ctx.fillRect(0,0,canvas.width,canvas.height);
      }}
      nfftEl.textContent = nfft;
    }}

    function toDB(v) {{ return 10 * Math.log10(v + 1e-20); }}
    function norm01(db, dbMin, dbMax) {{
      if (db <= dbMin) return 0;
      if (db >= dbMax) return 1;
      return (db - dbMin) / (dbMax - dbMin);
    }}

    function turboRGB(t) {{
      const r = Math.min(1, Math.max(0, 0.13572138 + 4.61539260*t - 42.66032258*t*t + 132.13108234*t**3 - 152.94239396*t**4 + 59.28637943*t**5));
      const g = Math.min(1, Math.max(0, 0.09140261 + 2.19418839*t + 4.84296658*t*t - 14.18503333*t**3 + 4.27729857*t**4 + 2.82956604*t**5));
      const b = Math.min(1, Math.max(0, 0.10667330 + 8.18855510*t - 44.65923200*t*t + 115.13214778*t**3 - 123.90603204*t**4 + 46.85253460*t**5));
      return [r*255|0, g*255|0, b*255|0];
    }}
    function grayRGB(t) {{ const v=(t*255)|0; return [v,v,v]; }}
    function colorize(t) {{ return (cmapSel.value==='grayscale') ? grayRGB(t) : turboRGB(t); }}

    function drawRow(mags, dbMin, dbMax) {{
      const n = mags.length;
      // scroll down by 1px
      ctx.drawImage(canvas, 0, 0, canvas.width, canvas.height-1, 0, 1, canvas.width, canvas.height-1);
      const row = ctx.createImageData(n, 1);
      const data = row.data;
      for (let i=0;i<n;i++) {{
        const db = toDB(mags[i]);
        const t = norm01(db, dbMin, dbMax);
        const [r,g,b] = colorize(t);
        const j = i*4;
        data[j]=r; data[j+1]=g; data[j+2]=b; data[j+3]=255;
      }}
      ctx.putImageData(row, 0, 0);
    }}

    // FPS meter
    let frames=0,last=performance.now();
    function tickFPS() {{
      const now=performance.now();
      if (now-last>=1000) {{ fpsEl.textContent = frames.toString(); frames=0; last=now; }}
      frames++;
    }}

    function syncLabels() {{ dbminV.textContent=dbminEl.value; dbmaxV.textContent=dbmaxEl.value; }}
    dbminEl.oninput = dbmaxEl.oninput = syncLabels; syncLabels();

    const socket = io(SERVER, {{ transports: ["websocket"] }});
    socket.on('connect', () => statusEl.textContent='connected');
    socket.on('disconnect', () => statusEl.textContent='disconnected');

    socket.on('update', (buf) => {{
      if (paused) return;
      sizeEl.textContent = buf.byteLength;
      const mags = new Float32Array(buf);
      setCanvasWidth(mags.length);           // auto-adapt to incoming width
      drawRow(mags, parseFloat(dbminEl.value), parseFloat(dbmaxEl.value));
      tickFPS();
    }});
  </script>
</body>
</html>
"""

async def index(_):
    return web.Response(text=INDEX_HTML, content_type="text/html")

async def health(_):
    return web.json_response({"status": "ok"})

app.router.add_get("/", index)
app.router.add_get("/health", health)

# ---------------- Socket.IO events ----------------
@sio.event
async def connect(sid, environ):
    logging.info(f"Web client connected: {sid}")

@sio.event
async def disconnect(sid):
    logging.info(f"Web client disconnected: {sid}")

# ---------------- UDP protocol ----------------
class UdpToSIO(asyncio.DatagramProtocol):
    def __init__(self, sio_server: socketio.AsyncServer):
        self.sio = sio_server
        self.count = 0
    def connection_made(self, transport: asyncio.BaseTransport):
        self.transport = transport  # type: ignore
        addr = transport.get_extra_info("sockname")
        logging.info(f"UDP listening on udp://{addr[0]}:{addr[1]}")
    def datagram_received(self, data: bytes, addr):
        self.count += 1
        if EMIT_EVERY > 1 and self.count % EMIT_EVERY:
            return
        if FRAME_BYTES and len(data) != FRAME_BYTES and self.count % 100 == 1:
            logging.warning(f"Packet size {len(data)} (expected {FRAME_BYTES}); forwarding anyway")
        # forward to all clients as binary
        asyncio.create_task(self.sio.emit("update", data))
    def error_received(self, exc: Exception):
        logging.error(f"UDP error: {exc}")

# ---------------- Main runner ----------------
async def main():
    # HTTP/Socket.IO
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, LISTEN_IP, WEB_PORT)
    await site.start()
    logging.info(f"Web UI + Socket.IO at http://{LISTEN_IP}:{WEB_PORT}/")

    # UDP listener
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: UdpToSIO(sio),
        local_addr=(LISTEN_IP, DATA_PORT),
        allow_broadcast=False
    )
    logging.info(f"Waiting for UDP frames on {LISTEN_IP}:{DATA_PORT} ...")
    try:
        await asyncio.Event().wait()
    finally:
        transport.close()
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down.")

