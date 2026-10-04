"""Monotonic source/publication health independent of GNU Radio's scheduler."""
import json
import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class StreamHealth:
    def __init__(self, stall_seconds=2.0, clock=time.monotonic):
        if not math.isfinite(stall_seconds) or stall_seconds <= 0:
            raise ValueError('Stall timeout must be positive')
        self.clock, self.stall_seconds = clock, stall_seconds
        self.last_source = None
        self.last_publish = None
        self.server = None
        self.thread = None
        self.mode = 'streaming'
        self.mode_since = self.clock()
        self.warmup_since = None
        self.warmup_seconds = 30
        self.details = lambda: {}

    def set_mode(self, mode):
        if mode != self.mode:
            self.mode, self.mode_since = mode, self.clock()
            if mode == 'waking' and self.warmup_since is None:
                self.warmup_since = self.mode_since
            elif mode in ('idle', 'streaming', 'fault'):
                self.warmup_since = None

    def source_progress(self):
        self.last_source = self.clock()

    def published(self):
        self.last_publish = self.clock()

    def status(self):
        now = self.clock()
        source_age = now - self.last_source if self.last_source is not None else None
        publish_age = now - self.last_publish if self.last_publish is not None else None
        progressing = (source_age is not None and publish_age is not None and
                   source_age <= self.stall_seconds and publish_age <= self.stall_seconds)
        warming = (self.warmup_since is not None and
                   now-self.warmup_since <= self.warmup_seconds)
        healthy = (self.mode == 'idle' or
                   (self.mode in ('waking', 'cooling') and warming) or
                   (self.mode in ('streaming', 'cooling') and progressing))
        return healthy, {'status': self.mode if healthy else 'stalled', 'mode': self.mode,
                         'source_age_seconds': source_age, 'publish_age_seconds': publish_age,
                         **self.details()}

    def serve(self, port=8081, host='0.0.0.0'):
        health = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path not in ('/health', '/ready', '/startup'):
                    self.send_error(404)
                    return
                healthy, result = health.status()
                payload = json.dumps(result).encode()
                self.send_response(200 if healthy else 503)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):
                pass

        self.server = ThreadingHTTPServer((host, port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=2)
            self.server = None
