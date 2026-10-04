import { onUnmounted, watch, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import DspWorker from '../workers/dsp.worker.ts?worker'
import { useSdrStore } from '../store'
import { feedAudio, initAudio, resetAudioQueue, setVolume, stopAudioPlayback } from '&/features/sdr/engine/AudioPlayer'
import { useAutomation } from './useAutomation'
import { exhaustive, typedWorker, type TypedWorker, type DspCommand, type DspEvent, type Tuning } from '../engine/messages'

export function useReceiver() {
    const store = useSdrStore(), toast = useToast(), automation = useAutomation()
    const hidden = ref(document.hidden)
    let worker: TypedWorker<DspCommand, DspEvent> | null = null
    let audioGeneration = 0, audioStarting = false, suspended = false, active = false
    let graphicCallback: ((data: Float32Array) => void) | null = null
    const tuning = (): Tuning => ({ freq: store.tuneFreq, bw: store.bandwidth, side: store.sideband, mode: store.mode, pitch: store.cwPitch })
    const audio = () => ({ agc: store.audioAgc, squelch: store.squelch, threshold: store.squelchThreshold })
    const display = () => ({ fftSize: store.fftSize, fps: store.fps,
        visible: !hidden.value && !store.frozen,
        analyze: (!hidden.value && !store.frozen) || (store.isListening && Boolean(store.trackingTarget || store.autoFreq || store.autoBw)),
        limitLow: store.limits.low, limitHigh: store.limits.high })
    const connect = () => {
        if (!worker || active) return
        active = true; suspended = false
        worker.postMessage({ type: 'init', payload: {
            wsUrl: store.settings.ws_url, wasmUrl: new URL('/dsp.wasm', window.location.href).href,
            band: store.selectedBand,
            audioRate: store.settings.audio_rate, calibration: store.settings.calibration,
            ...tuning(), ...display(), audio: audio(),
        } })
    }
    const stopListening = () => {
        audioGeneration++; audioStarting = false; store.isListening = false
        worker?.postMessage({ type: 'listen', payload: false }); stopAudioPlayback()
    }
    const toggleAudio = async () => {
        if (store.isListening || audioStarting) { stopListening(); return }
        const generation = ++audioGeneration
        audioStarting = true
        try {
            await initAudio(store.settings.audio_rate)
            if (generation !== audioGeneration || !store.connectionWanted || !worker) return
            store.isListening = true; worker.postMessage({ type: 'listen', payload: true })
        } catch (error) {
            if (generation !== audioGeneration) return
            stopListening()
            toast.add({ severity: 'error', summary: 'Audio unavailable', detail: (error as Error).message, life: 4000 })
        } finally { if (generation === audioGeneration) audioStarting = false }
    }
    const toggleConnection = () => {
        store.connectionWanted = !store.connectionWanted
        if (!store.connectionWanted) {
            stopListening(); worker?.postMessage({ type: 'disconnect' }); active = false
            store.setConnectionState('disconnected'); automation.reset()
        } else if (!worker && graphicCallback) initWorker(graphicCallback)
        else connect()
    }
    function syncVisibility() {
        hidden.value = document.hidden
        const shouldPause = hidden.value && store.pauseHidden && !store.isListening
        if (shouldPause && active) {
            worker?.postMessage({ type: 'disconnect' }); active = false; suspended = true
            store.setConnectionState('suspended'); automation.reset()
        } else if (!shouldPause && suspended && store.connectionWanted) connect()
        worker?.postMessage({ type: 'display', payload: display() })
    }
    const initWorker = (callback: (data: Float32Array) => void) => {
        graphicCallback = callback; worker?.terminate(); worker = typedWorker<DspCommand, DspEvent>(new DspWorker())
        active = false; setVolume(store.volume / 100)
        worker.onerror = event => {
            active = false; store.connectionWanted = false; store.setConnectionState('failed'); stopListening()
            worker?.terminate(); worker = null
            toast.add({ severity: 'error', summary: 'Receiver error', detail: event.message, life: 4000 })
        }
        worker.onmessage = event => {
            const message = event.data
            switch (message.type) {
                case 'status':
                    if (!store.connectionWanted || suspended) {
                        store.setConnectionState(suspended && store.connectionWanted ? 'suspended' : 'disconnected')
                        break
                    }
                    store.setConnectionState(message.payload)
                    if (message.payload !== 'connected') resetAudioQueue()
                    if (message.payload === 'unavailable') { active = false; store.connectionWanted = false; stopListening() }
                    break
                case 'graphicData':
                    try { if (!store.frozen && !hidden.value) graphicCallback?.(message.payload) }
                    finally { worker?.postMessage({ type: 'ackGraphics', session: message.session }) }
                    break
                case 'analysis': automation.accept(message.payload); break
                case 'telemetry':
                    store.frames = message.payload.frames; store.gaps = message.payload.gaps; store.processingMs = message.payload.processingMs
                    store.audioRssi = message.payload.rssi; store.squelchOpen = message.payload.squelchOpen
                    break
                case 'audioData':
                    try { if (store.isListening) feedAudio(message.payload) }
                    finally { worker?.postMessage({ type: 'ackAudio', session: message.session }) }
                    break
                case 'streamGap':
                    resetAudioQueue(); if (message.payload === 'source') automation.reset()
                    break
                case 'streamInfo':
                    store.settings.samp_rate = message.payload.sampleRate; store.settings.lo_freq = message.payload.centerFreq
                    store.tune(store.tuneFreq)
                    break
                case 'correctionApplied': store.tune(message.payload.freq, message.payload.bw); break
                case 'error':
                    toast.add({ severity: 'error', summary: 'Receiver error', detail: message.payload.message, life: 4000 })
                    break
                default: exhaustive(message)
            }
        }
        if (store.connectionWanted) connect()
        syncVisibility()
    }
    watch(() => store.selectedBand, () => {
        stopListening(); automation.reset()
        store.setConnectionState(store.connectionWanted ? 'connecting' : 'disconnected')
        if (graphicCallback) initWorker(graphicCallback)
    })
    watch([() => store.tuneFreq, () => store.bandwidth, () => store.sideband, () => store.mode, () => store.cwPitch], () =>
        worker?.postMessage({ type: 'tune', payload: tuning() }))
    watch([() => store.audioAgc, () => store.squelch, () => store.squelchThreshold], () =>
        worker?.postMessage({ type: 'audio', payload: audio() }))
    watch([() => store.fftSize, () => store.fps, () => store.frozen,
        () => store.settings.samp_rate, () => store.settings.lo_freq,
        () => store.trackingTarget, () => store.autoFreq, () => store.autoBw], () =>
        worker?.postMessage({ type: 'display', payload: display() }))
    watch([() => store.pauseHidden, () => store.isListening], syncVisibility)
    watch(() => store.volume, value => setVolume(value / 100))
    document.addEventListener('visibilitychange', syncVisibility)
    onUnmounted(() => {
        store.connectionWanted = true; stopListening()
        document.removeEventListener('visibilitychange', syncVisibility)
        worker?.postMessage({ type: 'disconnect' }); worker?.terminate(); worker = null
        store.setConnectionState('disconnected'); automation.reset()
    })
    return { initWorker, toggleAudio, toggleConnection, ...automation }
}
