"""Test-only static SPA server with isolated stream configuration."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen
import yaml

parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,required=True)
parser.add_argument('--backend',required=True);args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
config=yaml.safe_load((root/'config/config.yaml').read_text());config['ws_url']=args.backend
payload=yaml.safe_dump(config).encode()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(root/'frontend/dev/src/dist'),**kw)
    def do_GET(self):
        request_path = urlsplit(self.path).path
        if request_path=='/config.yaml':
            self.send_response(200);self.send_header('Content-Type','application/yaml')
            self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        elif request_path == '/bands':
            with urlopen(args.backend + '/bands', timeout=3) as response:
                data = response.read()
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        else:
            if request_path in ['/sdr','/about-us','/resources']:self.path='/index.html'
            super().do_GET()
    def log_message(self,*a):pass
ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
