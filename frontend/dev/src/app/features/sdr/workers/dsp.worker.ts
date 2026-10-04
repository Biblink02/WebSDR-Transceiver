import { parseIqFrame, iqWebSocketUrl } from '../engine/IqProtocol'
import { instantiateDsp, type DspExports } from '../engine/WasmDsp'
import { exhaustive, type DspCommand, type DspEvent, type ReceiverConfig, type ReceiverState, type Tuning } from '../engine/messages'
import { SpectrumAnalyzer } from '../core/analysis'

let dsp: DspExports | null = null, socket: WebSocket | null = null
let handle = 0, config: ReceiverConfig | null = null, applied: Tuning | null = null
let activeRate = 0, activeCenter = 0, activeEpoch: number | null = null, previousSequence: number | null = null
let listening = false, stopped = true, audioPending = false, graphicsPending = false, audioDropped = false
let lastFft = 0, lastFrame = 0, retry = 250, generation = 0
let timer: ReturnType<typeof setTimeout> | null = null, heartbeat: ReturnType<typeof setInterval> | null = null
let loading: AbortController | null = null
const analyzer = new SpectrumAnalyzer()
let received = false, frames = 0, gaps = 0, processingMs = 0, lastTelemetry = 0
const send = (message: DspEvent, transfer: Transferable[] = []) => self.postMessage(message, { transfer })
const status = (state: ReceiverState) => send({ type: 'status', payload: state })

function resetStream() {
    previousSequence = null
    if (dsp && handle) dsp.dsp_reset(handle)
    analyzer.reset(); gaps++
    send({ type: 'streamGap', payload: 'source' })
}
function applyAudio() {
    if (!dsp || !handle || !config) return
    const { agc, squelch, threshold } = config.audio
    if (!dsp.dsp_audio_config(handle, Number(agc), Number(squelch), threshold)) throw new Error('Invalid audio settings')
}
function applyTune() {
    if (!dsp || !handle || !config) return
    const { freq, bw, side, mode, pitch } = config
    if (!Number.isFinite(freq) || !Number.isFinite(bw)) throw new Error('Frequency and bandwidth must be finite')
    const width = Math.max(90, Math.min(15000, bw))
    const low = -activeRate / 2 + (mode === 'cw' ? width / 2 : side < 0 ? width : 0)
    const high = activeRate / 2 - (mode === 'cw' ? width / 2 : side > 0 ? width : 0)
    const offset = Math.max(low, Math.min(high, freq - activeCenter))
    const rebuild = !applied || applied.bw !== width || applied.side !== side || applied.mode !== mode
    if (!dsp.dsp_mode(handle, Number(mode === 'cw'), pitch)) throw new Error('Invalid CW pitch')
    const valid = rebuild ? dsp.dsp_tune(handle, offset, width, side) : dsp.dsp_shift(handle, offset)
    if (!valid) throw new Error('Invalid local tuning parameters')
    applied = { freq: activeCenter + offset, bw: width, side, mode, pitch }
    if (applied.freq !== freq || width !== bw) {
        config.freq = applied.freq; config.bw = width
        send({ type: 'correctionApplied', payload: { freq: applied.freq, bw: width } })
    }
    if (rebuild) send({ type: 'streamGap', payload: 'tune' })
}
function processFrame(buffer: ArrayBuffer) {
    if (!dsp || !config) return
    const frame = parseIqFrame(buffer)
    lastFrame = performance.now(); frames++
    if (!handle || activeRate !== frame.sampleRate || activeCenter !== frame.centerFreq) {
        if (handle) dsp.dsp_free(handle)
        activeRate = frame.sampleRate; activeCenter = frame.centerFreq
        handle = dsp.dsp_new(activeRate, config.audioRate, config.fftSize, config.calibration)
        if (!handle) throw new Error('Unsupported DSP configuration')
        applied = null; resetStream(); applyTune(); applyAudio()
        send({ type: 'streamInfo', payload: { sampleRate: activeRate, centerFreq: activeCenter } })
    }
    if (activeEpoch !== frame.epoch ||
        (previousSequence !== null && frame.sequence !== ((previousSequence + 1) >>> 0))) resetStream()
    activeEpoch = frame.epoch; previousSequence = frame.sequence
    new Int8Array(dsp.memory.buffer, dsp.dsp_input(handle), frame.samples.length).set(frame.samples)
    const now = performance.now()
    const render = ((config.visible && !graphicsPending) || config.analyze) &&
        now - lastFft >= 1000 / (config.visible ? config.fps : 4)
    const count = dsp.dsp_process(handle, frame.count, Number(listening), Number(render))
    processingMs = processingMs * 0.9 + (performance.now() - now) * 0.1
    if (count < 0) throw new Error('DSP rejected an I/Q frame')
    if (!received) { received = true; retry = 250; status('connected') }
    if (count && !audioPending) {
        if (audioDropped) { send({ type: 'streamGap', payload: 'audio' }); audioDropped = false }
        const audio = new Float32Array(dsp.memory.buffer, dsp.dsp_audio(handle), count).slice()
        audioPending = true
        send({ type: 'audioData', payload: audio, session: generation }, [audio.buffer])
    } else if (count) audioDropped = true
    if (render && dsp.dsp_fft_ready(handle)) {
        const spectrum = new Float32Array(dsp.memory.buffer, dsp.dsp_spectrum(handle), config.fftSize).slice()
        const analysis = analyzer.update(spectrum, activeRate, activeCenter, now, config.limitLow, config.limitHigh)
        if (analysis && config.analyze) send({ type: 'analysis', payload: analysis })
        lastFft = now
        if (config.visible && !graphicsPending) {
            graphicsPending = true
            send({ type: 'graphicData', payload: spectrum, session: generation }, [spectrum.buffer])
        }
    }
    if (now - lastTelemetry > 1000) {
        lastTelemetry = now
        send({ type: 'telemetry', payload: { frames, gaps, processingMs,
            rssi: dsp.dsp_audio_rssi(handle), squelchOpen: Boolean(dsp.dsp_squelch_open(handle)) } })
    }
}
function connect(current: number) {
    if (stopped || current !== generation || !config) return
    status('connecting')
    const url = new URL(iqWebSocketUrl(config.wsUrl))
    url.searchParams.set('band', String(config.band))
    const connection = new WebSocket(url)
    socket = connection; connection.binaryType = 'arraybuffer'
    connection.onopen = () => {
        if (current !== generation) return
        received = false; lastFrame = performance.now(); resetStream(); status('warming')
        if (heartbeat) clearInterval(heartbeat)
        heartbeat = setInterval(() => {
            if (performance.now() - lastFrame > (received ? 5000 : 30000)) connection.close(1000, 'I/Q source stalled')
        }, 1000)
    }
    connection.onmessage = event => {
        if (current !== generation) return
        try {
            if (!(event.data instanceof ArrayBuffer)) throw new Error('Expected binary I/Q data')
            processFrame(event.data)
        } catch (error) {
            send({ type: 'error', payload: { message: (error as Error).message, fatal: false } })
            resetStream(); connection.close(1003, 'Invalid I/Q stream')
        }
    }
    connection.onerror = () => { if (current === generation) status('connection-error') }
    connection.onclose = () => {
        if (current !== generation) return
        if (heartbeat) clearInterval(heartbeat)
        heartbeat = null; socket = null
        resetStream(); status(stopped ? 'disconnected' : 'reconnecting')
        if (!stopped) { timer = setTimeout(() => connect(current), retry); retry = Math.min(retry * 2, 5000) }
    }
}
function disconnect() {
    stopped = true; generation++; loading?.abort(); loading = null
    if (timer) clearTimeout(timer)
    if (heartbeat) clearInterval(heartbeat)
    timer = null; heartbeat = null
    if (socket) {
        socket.onclose = null; socket.onmessage = null; socket.onopen = null; socket.onerror = null
        socket.close(); socket = null
    }
    if (dsp && handle) dsp.dsp_free(handle)
    handle = 0; applied = null; previousSequence = null; activeEpoch = null; listening = false
    audioPending = false; graphicsPending = false; audioDropped = false; lastFft = 0
    analyzer.reset(); received = false; retry = 250
}
async function initialize(payload: ReceiverConfig) {
    disconnect(); stopped = false; config = payload
    const current = generation
    status('loading')
    try {
        if (!dsp) {
            loading = new AbortController()
            const response = await fetch(payload.wasmUrl, { signal: loading.signal })
            if (!response.ok) throw new Error('Unable to load the DSP module')
            const instance = await instantiateDsp(await response.arrayBuffer())
            if (current !== generation) return
            dsp = instance; loading = null
        }
        connect(current)
    } catch (error) {
        if (current !== generation) return
        disconnect(); status('unavailable')
        send({ type: 'error', payload: { message: (error as Error).message, fatal: true } })
    }
}
self.onmessage = (event: MessageEvent<DspCommand>) => {
    const message = event.data
    try {
        switch (message.type) {
            case 'init': void initialize(message.payload); break
            case 'disconnect': disconnect(); status('disconnected'); break
            case 'listen': listening = message.payload; if (dsp && handle) { dsp.dsp_reset(handle); applyTune() } break
            case 'tune': if (config) { Object.assign(config, message.payload); applyTune() } break
            case 'audio': if (config) { config.audio = message.payload; applyAudio() } break
            case 'display':
                if (config) {
                    const payload = message.payload
                    if (dsp && handle && !dsp.dsp_set_fft(handle, payload.fftSize)) throw new Error('Unsupported FFT resolution')
                    if (config.fftSize !== payload.fftSize) analyzer.reset()
                    Object.assign(config, payload, { fps: Math.max(5, Math.min(30, payload.fps)) })
                }
                break
            case 'ackAudio': if (message.session === generation) audioPending = false; break
            case 'ackGraphics': if (message.session === generation) graphicsPending = false; break
            default: exhaustive(message)
        }
    } catch (error) { send({ type: 'error', payload: { message: (error as Error).message, fatal: false } }) }
}
export {}
