export interface DspExports extends WebAssembly.Exports {
    memory: WebAssembly.Memory
    _initialize(): void
    dsp_new(rate: number, audioRate: number, fftSize: number, calibration: number): number
    dsp_free(handle: number): void
    dsp_input(handle: number): number
    dsp_audio(handle: number): number
    dsp_spectrum(handle: number): number
    dsp_fft_ready(handle: number): number
    dsp_set_fft(handle: number, size: number): number
    dsp_reset(handle: number): void
    dsp_tune(handle: number, offset: number, bw: number, side: number): number
    dsp_shift(handle: number, offset: number): number
    dsp_mode(handle: number, cw: number, pitch: number): number
    dsp_audio_config(handle: number, agc: number, squelch: number, threshold: number): number
    dsp_audio_rssi(handle: number): number
    dsp_squelch_open(handle: number): number
    dsp_process(handle: number, count: number, listen: number, fft: number): number
}

export async function instantiateDsp(bytes: BufferSource): Promise<DspExports> {
    // Standalone Emscripten reactor: no filesystem, threads, or runtime JS glue.
    const module = await WebAssembly.compile(bytes)
    const instance = await WebAssembly.instantiate(module, { wasi_snapshot_preview1: {
        proc_exit: (code: number) => { throw new Error(`DSP terminated: ${code}`) },
        fd_write: () => 8, // EBADF: the receiver has no writable file descriptors.
        fd_close: () => 8,
        fd_seek: () => 8,
    } })
    const exports = instance.exports as DspExports
    exports._initialize()
    return exports
}
