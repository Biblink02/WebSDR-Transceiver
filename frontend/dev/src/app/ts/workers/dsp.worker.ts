import { parseIqFrame, iqWebSocketUrl } from '@/IqProtocol'
import { instantiateDsp, type DspExports } from '@/WasmDsp'

interface ReceiverConfig {
    wsUrl: string
    wasmUrl: string
    audioRate: number
    fftSize: number
    calibration: number
    freq: number
    bw: number
    side: 1 | -1
}
let dsp: DspExports | null = null
let socket: WebSocket | null = null
let handle = 0
let config: ReceiverConfig | null = null
let tuning = { freq: 0, bw: 2700, side: 1 }
let activeRate = 0, activeCenter = 0, activeEpoch: number | null = null
let previousSequence: number | null = null
let listening = false, stopped = true
let audioPending = false, graphicsPending = false, audioDropped = false
let lastFft = 0, lastFrame = 0, retry = 250
let timer: ReturnType<typeof setTimeout> | null = null
let heartbeat: ReturnType<typeof setInterval> | null = null
let generation = 0

function status(text: string, connected: boolean) {
    self.postMessage({ type: 'status', payload: { status: text, isConnected: connected } })
}
function resetStream() {
    previousSequence = null
    if (dsp && handle) dsp.dsp_reset(handle)
    self.postMessage({ type: 'streamGap' })
}
function applyTune() {
    if (!dsp || !handle) return
    if (!Number.isFinite(tuning.freq) || !Number.isFinite(tuning.bw))
        throw new Error('Frequency and bandwidth must be finite')
    const bw = Math.max(90, Math.min(15000, tuning.bw))
    const side = tuning.side === -1 ? -1 : 1
    const low = -activeRate / 2 + (side < 0 ? bw : 0)
    const high = activeRate / 2 - (side > 0 ? bw : 0)
    const offset = Math.max(low, Math.min(high, tuning.freq - activeCenter))
    if (!dsp.dsp_tune(handle, offset, bw, side)) throw new Error('Invalid local tuning parameters')
    const freq = activeCenter + offset
    if (freq !== tuning.freq || bw !== tuning.bw) {
        tuning = { freq, bw, side }
        self.postMessage({ type: 'correctionApplied', payload: { freq, bw } })
    }
    self.postMessage({ type: 'streamGap' })
}
function processFrame(buffer: ArrayBuffer) {
    if (!dsp || !config) return
    const frame = parseIqFrame(buffer)
    lastFrame = performance.now()
    if (!handle || activeRate !== frame.sampleRate || activeCenter !== frame.centerFreq) {
        if (handle) dsp.dsp_free(handle)
        activeRate = frame.sampleRate; activeCenter = frame.centerFreq
        handle = dsp.dsp_new(activeRate, config.audioRate, config.fftSize, config.calibration)
        if (!handle) throw new Error('Unsupported DSP configuration')
        resetStream(); applyTune()
        self.postMessage({ type: 'streamInfo', payload: { sampleRate: activeRate, centerFreq: activeCenter } })
    }
    if (activeEpoch !== frame.epoch ||
        (previousSequence !== null && frame.sequence !== ((previousSequence + 1) >>> 0))) resetStream()
    activeEpoch = frame.epoch
    previousSequence = frame.sequence
    new Int8Array(dsp.memory.buffer, dsp.dsp_input(handle), frame.samples.length).set(frame.samples)
    const now = performance.now()
    const render = !graphicsPending && now - lastFft >= 1000 / 30
    const count = dsp.dsp_process(handle, frame.count, Number(listening), Number(render))
    if (count < 0) throw new Error('DSP rejected an I/Q frame')
    if (count && !audioPending) {
        if (audioDropped) { self.postMessage({ type: 'streamGap' }); audioDropped = false }
        const audio = new Float32Array(dsp.memory.buffer, dsp.dsp_audio(handle), count).slice()
        audioPending = true
        self.postMessage({ type: 'audioData', payload: audio }, { transfer: [audio.buffer] })
    } else if (count) audioDropped = true
    if (render && dsp.dsp_fft_ready(handle)) {
        const spectrum = new Float32Array(dsp.memory.buffer, dsp.dsp_spectrum(handle), config.fftSize).slice()
        graphicsPending = true; lastFft = now
        self.postMessage({ type: 'graphicData', payload: spectrum }, { transfer: [spectrum.buffer] })
    }
}
function connect(current: number) {
    if (stopped || current !== generation || !config) return
    status('CONNECTING...', false)
    const connection = new WebSocket(iqWebSocketUrl(config.wsUrl))
    socket = connection
    connection.binaryType = 'arraybuffer'
    connection.onopen = () => {
        retry = 250; lastFrame = performance.now(); resetStream(); status('CONNECTED', true)
        if (heartbeat) clearInterval(heartbeat)
        heartbeat = setInterval(() => {
            if (performance.now() - lastFrame > 5000) connection.close(1000, 'I/Q source stalled')
        }, 1000)
    }
    connection.onmessage = event => {
        try {
            if (!(event.data instanceof ArrayBuffer)) throw new Error('Expected binary I/Q data')
            processFrame(event.data)
        } catch (error) {
            self.postMessage({ type: 'error', payload: (error as Error).message })
            resetStream(); connection.close(1003, 'Invalid I/Q stream')
        }
    }
    connection.onerror = () => status('CONNECTION ERROR', false)
    connection.onclose = () => {
        if (heartbeat) clearInterval(heartbeat)
        heartbeat = null
        resetStream(); status(stopped ? 'DISCONNECTED' : 'RECONNECTING...', false)
        if (!stopped && current === generation) {
            timer = setTimeout(() => connect(current), retry)
            retry = Math.min(retry * 2, 5000)
        }
    }
}
function disconnect() {
    stopped = true; generation++
    if (timer) clearTimeout(timer)
    if (heartbeat) clearInterval(heartbeat)
    timer = null; heartbeat = null
    if (socket) {
        socket.onclose = null; socket.onmessage = null; socket.onopen = null; socket.onerror = null
        socket.close(); socket = null
    }
    if (dsp && handle) dsp.dsp_free(handle)
    handle = 0; previousSequence = null; activeEpoch = null; listening = false
    audioPending = false; graphicsPending = false; audioDropped = false
}
self.onmessage = async (event: MessageEvent) => {
    const { type, payload } = event.data
    try {
        switch (type) {
            case 'init': {
                disconnect(); stopped = false; config = payload
                tuning = { freq: payload.freq, bw: payload.bw, side: payload.side }
                const current = generation
                status('LOADING DSP...', false)
                if (!dsp) {
                    const response = await fetch(payload.wasmUrl)
                    if (!response.ok) throw new Error('Unable to load the DSP module')
                    const instance = await instantiateDsp(await response.arrayBuffer())
                    if (current !== generation) return
                    dsp = instance
                }
                connect(current)
                break
            }
            case 'disconnect': disconnect(); status('DISCONNECTED', false); break
            case 'listen':
                listening = Boolean(payload)
                if (dsp && handle) { dsp.dsp_reset(handle); applyTune() }
                break
            case 'tune': tuning = payload; applyTune(); break
            case 'ackAudio': audioPending = false; break
            case 'ackGraphics': graphicsPending = false; break
        }
    } catch (error) {
        self.postMessage({ type: 'error', payload: (error as Error).message })
        if (type === 'init') { disconnect(); status('DSP UNAVAILABLE', false) }
    }
}
export {}
