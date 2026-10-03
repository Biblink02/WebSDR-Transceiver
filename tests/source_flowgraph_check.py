"""Run with system Python/GNU Radio: exercise source filtering and packetization."""
import numpy as np
from gnuradio import gr, blocks, filter as gr_filter
from sdr_server import antialias_taps, decimation_for, IqSink
from iq_publisher import Packetizer
from iq_protocol import validate_frame


def filtered_rms(frequency):
    rate=2000000
    data=np.exp(2j*np.pi*frequency*np.arange(100000)/rate).astype(np.complex64)
    graph=gr.top_block()
    source=blocks.vector_source_c(data.tolist(),False)
    decimator=gr_filter.fir_filter_ccf(4,antialias_taps(rate,4))
    sink=blocks.vector_sink_c()
    graph.connect(source,decimator,sink);graph.run()
    output=np.asarray(sink.data())
    assert len(output)==25000
    return np.sqrt(np.mean(np.abs(output[1000:])**2))


def main():
    assert decimation_for(520834,500000)==1
    assert decimation_for(2000000,500000)==4
    assert decimation_for(1500000,500000)==3
    wanted=filtered_rms(50000);alias=filtered_rms(450000)
    assert wanted>0.95
    assert alias<wanted*0.001
    class Capture:
        def __init__(self):
            self.packetizer=Packetizer(500000,739700000,256,epoch=42)
            self.frames=[]
        def push(self,samples): self.frames.extend(self.packetizer.push(samples))
    capture=Capture();graph=gr.top_block()
    source=blocks.vector_source_c([0.25+0.5j]*1024,False)
    sink=IqSink(capture);graph.connect(source,sink);graph.run()
    assert len(capture.frames)==4
    assert all(validate_frame(frame).sample_rate==500000 for frame in capture.frames)
    print(f'GNU Radio source check passed: wanted RMS {wanted:.6f}, alias RMS {alias:.8f}, four valid packed frames')


if __name__=='__main__':main()
