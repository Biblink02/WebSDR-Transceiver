import asyncio
import os
import socket
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
import zmq.asyncio
from websockets.asyncio.client import connect
from iq_protocol import FrameInfo, make_header, validate_frame

ROOT=Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));return sock.getsockname()[1]


@asynccontextmanager
async def backend(port,iq_port,tmp_path,processes=None):
    env={**os.environ,'CONFIG_PATH':str(ROOT/'config/config.yaml'),'PORT':str(port),
         'SDR_HOST':'127.0.0.1','SDR_IQ_PORT':str(iq_port),
         'PYTHONPATH':os.pathsep.join(str(ROOT/p) for p in ['shared','backend-controller'])}
    log=(tmp_path/f'backend-{port}.log').open('w')
    process=subprocess.Popen([sys.executable,str(ROOT/'backend-controller/backend_controller.py')],env=env,stdout=log,stderr=log)
    if processes is not None: processes.append(process)
    try:
        async with httpx.AsyncClient() as client:
            for _ in range(100):
                if process.poll() is not None:
                    raise AssertionError((tmp_path/f'backend-{port}.log').read_text())
                try:
                    if (await client.get(f'http://127.0.0.1:{port}/health')).status_code==200: break
                except httpx.ConnectError: pass
                await asyncio.sleep(.05)
            else: raise AssertionError('Backend did not start')
        yield f'http://127.0.0.1:{port}'
    finally:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill();process.wait(timeout=3)
        log.close()


@pytest.mark.asyncio
async def test_real_websocket_fanout_replica_independence_and_source_reconnect(tmp_path):
    context=zmq.asyncio.Context();publisher=context.socket(zmq.PUB)
    publisher.setsockopt(zmq.LINGER,0);iq_port=publisher.bind_to_random_port('tcp://127.0.0.1')
    p1,p2=free_port(),free_port()
    try:
        async with backend(p1,iq_port,tmp_path) as first, backend(p2,iq_port,tmp_path) as second:
            async with httpx.AsyncClient() as http:
                assert (await http.get(first+'/ready')).json()=={'status':'idle'}
            async with connect(first.replace('http','ws')+'/iq') as a, connect(first.replace('http','ws')+'/iq') as b, connect(second.replace('http','ws')+'/iq') as c:
                await asyncio.sleep(.25)
                async with httpx.AsyncClient() as http:
                    assert (await http.get(first+'/ready')).status_code==503
                packet=make_header(FrameInfo(0,520834,739700000,256,123))+bytes(512)
                await publisher.send(packet)
                results=await asyncio.gather(*(asyncio.wait_for(ws.recv(),2) for ws in (a,b,c)))
                assert results==[packet]*3
                async with httpx.AsyncClient() as http:
                    assert (await http.get(first+'/ready')).status_code==200
                    assert (await http.get(first+'/stream-info')).json()['clients']==2
                    assert (await http.get(second+'/stream-info')).json()['clients']==1
                await publisher.send(b'malformed')
                await asyncio.sleep(.05)
                async with httpx.AsyncClient() as http:
                    assert (await http.get(first+'/stream-info')).json()['counters']['malformed']==1
                publisher.close(linger=0)
                await asyncio.sleep(.2)
                publisher=context.socket(zmq.PUB);publisher.setsockopt(zmq.LINGER,0)
                publisher.bind(f'tcp://127.0.0.1:{iq_port}')
                received=[asyncio.create_task(ws.recv()) for ws in (a,b,c)]
                for sequence in range(30):
                    packet=make_header(FrameInfo(sequence,520834,739700000,256,456))+bytes(512)
                    await publisher.send(packet);await asyncio.sleep(.1)
                    if all(task.done() for task in received): break
                results=await asyncio.wait_for(asyncio.gather(*received),3)
                assert all(validate_frame(data).epoch==456 for data in results)
            await asyncio.sleep(.1)
            async with httpx.AsyncClient() as http:
                assert (await http.get(first+'/stream-info')).json()['clients']==0
                assert (await http.get(second+'/stream-info')).json()['clients']==0
    finally:
        publisher.close(linger=0);context.term()
