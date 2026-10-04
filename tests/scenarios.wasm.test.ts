import { test, expect } from 'bun:test'
import { instantiateDsp } from '../frontend/dev/src/app/features/sdr/engine/WasmDsp'

test('compiled liquid-dsp WASM recovers generated USB/LSB speech and keyed CW', async () => {
    const directory = process.env.SCENARIO_VECTORS
    if (!directory) throw new Error('Run bash scripts/check-scenarios.sh to prepare signal vectors')
    const bytes = await Bun.file(new URL('../frontend/dev/src/public/dsp.wasm', import.meta.url)).arrayBuffer()
    for (const [mode, offset, sideband] of [['usb', -12000, 1], ['lsb', 31000, -1], ['cw', 1000, 1]] as const) {
        const dsp = await instantiateDsp(bytes), id = dsp.dsp_new(520834, 48000, 4096, 0)
        expect(id).toBeGreaterThan(0)
        expect(dsp.dsp_audio_config(id, 0, 0, -45)).toBe(1)
        expect(dsp.dsp_mode(id, mode === 'cw' ? 1 : 0, 700)).toBe(1)
        expect(dsp.dsp_tune(id, offset, mode === 'cw' ? 500 : 3000, sideband)).toBe(1)
        const input = new Int8Array(await Bun.file(`${directory}/${mode}.iq8`).arrayBuffer())
        const output: Float32Array[] = []
        let length = 0
        try {
            for (let position = 0; position < input.length; position += 16384) {
                const count = Math.min(8192, (input.length-position)/2)
                new Int8Array(dsp.memory.buffer, dsp.dsp_input(id), count*2).set(input.subarray(position, position+count*2))
                const produced = dsp.dsp_process(id, count, 1, 0)
                expect(produced).toBeGreaterThanOrEqual(0)
                output.push(new Float32Array(dsp.memory.buffer, dsp.dsp_audio(id), produced).slice())
                length += produced
            }
            const joined = new Float32Array(length)
            let position = 0
            for (const part of output) { joined.set(part, position); position += part.length }
            await Bun.write(`${directory}/${mode}.f32`, joined)
        } finally { dsp.dsp_free(id) }
    }
}, 30000)
