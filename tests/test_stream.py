import asyncio
import struct
import numpy as np
import pytest
from iq_protocol import HEADER, FrameInfo, make_header, validate_frame
from iq_publisher import Packetizer
from iq import IQDistributor
from stream_health import StreamHealth


def frame(sequence=0, epoch=1):
    return make_header(FrameInfo(sequence,520834,739700000,256,epoch))+bytes(512)


def test_protocol_quantization_and_chunk_boundaries():
    values=np.array([2-2j, 0.5+0.5j, np.nan+1j, 0j]*256,dtype=np.complex64)
    packetizer=Packetizer(520834,739700000,256,epoch=42)
    frames=[]
    for chunk in (values[:13], values[13:91], values[91:]): frames.extend(packetizer.push(chunk))
    assert len(frames)==4
    assert packetizer.used==0
    assert packetizer.counters['malformed_samples']==256
    assert packetizer.counters['saturated_components']==512
    for index,data in enumerate(frames):
        info=validate_frame(data)
        assert info == FrameInfo(index,520834,739700000,256,42)
        iq=np.frombuffer(data,dtype=np.int8,offset=32)
        assert iq[:8].tolist()==[127,-127,64,64,0,127,0,0]


@pytest.mark.parametrize('data',[b'',bytes(32),frame()[:-1],frame()+b'x',
                                 HEADER.pack(b'WSIQ',2,1,32,0,520834,739700000,256,1)+bytes(512)])
def test_protocol_rejects_invalid_frames(data):
    with pytest.raises(ValueError): validate_frame(data)


def test_health_source_and_publication_stalls_and_recovery():
    now=[10.0]
    health=StreamHealth(clock=lambda:now[0])
    assert not health.status()[0]
    health.source_progress();health.published()
    assert health.status()[0]
    now[0]+=2.1;health.source_progress()
    assert not health.status()[0]
    health.published();assert health.status()[0]
    now[0]+=2.1;assert not health.status()[0]
    health.source_progress();health.published();assert health.status()[0]


@pytest.mark.asyncio
async def test_bounded_fanout_and_source_epoch_discards_stale_backlog():
    distributor=IQDistributor(None,'unused',queue_size=2)
    slow,fast=distributor.subscribe(),distributor.subscribe()
    for sequence in range(20):
        packet=frame(sequence)
        distributor.ingest(packet)
        assert await fast.get()==packet
        assert slow.qsize()<=2
    assert distributor.counters['client_dropped']==18
    assert validate_frame(await slow.get()).sequence==18
    distributor.ingest(frame(0,epoch=2))
    assert slow.qsize()==1
    assert validate_frame(await slow.get()).epoch==2
    distributor.ingest(b'bad')
    assert distributor.counters['malformed']==1
    distributor.unsubscribe(slow);distributor.unsubscribe(fast)
    assert not distributor.clients
