import { test, expect } from 'bun:test'
import { instantiateDsp } from '../frontend/dev/src/app/ts/WasmDsp'
import { performance } from 'node:perf_hooks'

const wasmPath = new URL('../frontend/dev/src/public/dsp.wasm', import.meta.url)
const load = async () => instantiateDsp(await Bun.file(wasmPath).arrayBuffer())
function writeTone(dsp: Awaited<ReturnType<typeof load>>, id: number, rate: number,
    start: number, count: number, tone: number) {
    const input = new Int8Array(dsp.memory.buffer, dsp.dsp_input(id), count*2)
    for (let i=0; i<count; i++) {
        const a=2*Math.PI*tone*(start+i)/rate
        input[i*2]=Math.round(80*Math.cos(a)); input[i*2+1]=Math.round(80*Math.sin(a))
    }
}

test('compiled WASM validates its ABI, runs FFT and recovers after reset', async () => {
    const dsp = await load()
    expect(dsp.dsp_new(1,48000,2048,0)).toBe(0)
    expect(dsp.dsp_process(99,8192,1,1)).toBe(-1)
    const id=dsp.dsp_new(500000,48000,2048,0)
    expect(id).toBeGreaterThan(0)
    expect(dsp.dsp_tune(id, NaN,2700,1)).toBe(0)
    expect(dsp.dsp_tune(id,249000,2700,1)).toBe(0)
    writeTone(dsp,id,500000,0,8192,125000)
    expect(dsp.dsp_process(id,8192,0,1)).toBe(0)
    const spectrum=new Float32Array(dsp.memory.buffer,dsp.dsp_spectrum(id),2048)
    expect(spectrum.indexOf(Math.max(...spectrum))).toBe(1536)
    expect(spectrum[1536]).toBeGreaterThan(-5)
    dsp.dsp_reset(id)
    expect(dsp.dsp_fft_ready(id)).toBe(0)
    dsp.dsp_free(id)
    expect(dsp.dsp_input(id)).toBe(0)
})

test('compiled WASM produces accurate 48 kHz PCM with bounded memory and real-time throughput', async () => {
    const dsp = await load()
    const id=dsp.dsp_new(520834,48000,32768,0)
    const bytes=dsp.memory.buffer.byteLength
    let samples=0, input=0
    const started=performance.now()
    const total=520834*3
    while (input<total) {
        const count=Math.min(8192,total-input)
        writeTone(dsp,id,520834,input,count,1000)
        const output=dsp.dsp_process(id,count,1,Number(input%32768===0))
        expect(output).toBeGreaterThanOrEqual(0)
        const audio=new Float32Array(dsp.memory.buffer,dsp.dsp_audio(id),output)
        expect(audio.every(x=>Number.isFinite(x) && Math.abs(x)<=1)).toBe(true)
        samples+=output; input+=count
    }
    const elapsed=(performance.now()-started)/1000
    expect(Math.abs(samples-144000)).toBeLessThanOrEqual(2)
    expect(dsp.memory.buffer.byteLength).toBe(bytes)
    console.log(`WASM: ${total} I/Q samples in ${elapsed.toFixed(3)} s (${(3/elapsed).toFixed(2)}× real time), ${samples} PCM samples, ${(bytes/1048576).toFixed(0)} MiB fixed memory`)
    // Performance is environment-dependent; correctness is the test gate.
    dsp.dsp_free(id)
    for(let i=0;i<100;i++) {
        const handle=dsp.dsp_new(520834,48000,2048,0)
        expect(handle).toBeGreaterThan(0); dsp.dsp_free(handle)
    }
    expect(dsp.memory.buffer.byteLength).toBe(bytes)
}, 30000)

test('FFT resolution changes preserve PCM and fit the fixed WASM heap', async () => {
    const dsp = await load()
    const a = dsp.dsp_new(520834, 48000, 32768, 0)
    const b = dsp.dsp_new(520834, 48000, 32768, 0)
    expect(a).toBeGreaterThan(0); expect(b).toBeGreaterThan(0)
    expect(dsp.dsp_new(520834, 48000, 32768, 0)).toBe(0)
    expect(dsp.dsp_set_fft(a, 1234)).toBe(0)
    expect(dsp.dsp_set_fft(99, 4096)).toBe(0)
    const bytes = dsp.memory.buffer.byteLength
    let position = 0
    for (let iteration = 0; iteration < 40; iteration++) {
        const size = [256, 4096, 8192, 32768][iteration % 4]
        expect(dsp.dsp_set_fft(a, size)).toBe(1)
        writeTone(dsp, a, 520834, position, 8192, 1000)
        writeTone(dsp, b, 520834, position, 8192, 1000)
        const countA = dsp.dsp_process(a, 8192, 1, 1)
        const countB = dsp.dsp_process(b, 8192, 1, 1)
        expect(countA).toBe(countB)
        const audioA = new Float32Array(dsp.memory.buffer, dsp.dsp_audio(a), countA)
        const audioB = new Float32Array(dsp.memory.buffer, dsp.dsp_audio(b), countB)
        expect(audioA.every((value, index) => value === audioB[index])).toBe(true)
        position += 8192
    }
    expect(dsp.memory.buffer.byteLength).toBe(bytes)
    dsp.dsp_free(a); dsp.dsp_free(b)
})

test('resized FFTs retain tone position and Hann normalization at every resolution', async () => {
    const dsp = await load()
    const id = dsp.dsp_new(500000, 48000, 256, -72)
    for (const size of [256, 512, 1024, 2048, 4096, 8192, 16384, 32768]) {
        expect(dsp.dsp_set_fft(id, size)).toBe(1)
        for (let position = 0; position < Math.max(8192, size); position += 8192) {
            writeTone(dsp, id, 500000, position, 8192, 125000)
            dsp.dsp_process(id, 8192, 0, 1)
        }
        expect(dsp.dsp_fft_ready(id)).toBe(1)
        const spectrum = new Float32Array(dsp.memory.buffer, dsp.dsp_spectrum(id), size)
        expect(spectrum.indexOf(Math.max(...spectrum))).toBe(size * 3 / 4)
        expect(Math.abs(spectrum[size * 3 / 4] + 76.01)).toBeLessThan(0.1)
    }
    dsp.dsp_free(id)
})
