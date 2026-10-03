import { onUnmounted, watch, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import DspWorker from '../workers/dsp.worker.ts?worker'
import { useSdrStore } from '../store'
import { feedAudio, initAudio, resetAudioQueue, setVolume, stopAudioPlayback } from '&/features/sdr/engine/AudioPlayer'
import { useAutomation } from './useAutomation'

export function useReceiver() {
    const store = useSdrStore(), toast = useToast(), automation = useAutomation()
    const hidden = ref(document.hidden)
    let worker: Worker | null = null
    let audioGeneration = 0, audioStarting = false, suspended = false, active = false
    let graphicCallback: ((data: Float32Array) => void) | null = null
    const tuning = () => ({ freq: store.tuneFreq, bw: store.bandwidth, side: store.sideband })
    const display = () => ({ fftSize: store.fftSize, fps: store.fps,
        visible: !hidden.value && !store.frozen, limitLow: store.limits.low, limitHigh: store.limits.high })
    const connect = () => {
        if (!worker || active) return
        active = true; suspended = false
        worker.postMessage({ type: 'init', payload: {
            wsUrl: store.settings.ws_url, wasmUrl: new URL('/dsp.wasm', window.location.href).href,
            audioRate: store.settings.audio_rate, calibration: store.settings.calibration,
            ...tuning(), ...display(),
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
            store.setConnectionStatus(false, 'DISCONNECTED'); automation.reset()
        } else connect()
    }
    function syncVisibility() {
        hidden.value = document.hidden
        const shouldPause = hidden.value && store.pauseHidden && !store.isListening
        if (shouldPause && active) {
            worker?.postMessage({ type: 'disconnect' }); active = false; suspended = true
            store.setConnectionStatus(false, 'PAUSED IN BACKGROUND'); automation.reset()
        } else if (!shouldPause && suspended && store.connectionWanted) connect()
        worker?.postMessage({ type: 'display', payload: display() })
    }
    const initWorker = (callback: (data: Float32Array) => void) => {
        graphicCallback = callback; worker?.terminate(); worker = new DspWorker()
        active = false; setVolume(store.volume / 100)
        worker.onerror = event => {
            store.setConnectionStatus(false, 'DSP ERROR'); stopListening()
            toast.add({ severity: 'error', summary: 'Receiver error', detail: event.message, life: 4000 })
        }
        worker.onmessage = event => {
            const { type, payload } = event.data
            switch (type) {
                case 'status':
                    if (!store.connectionWanted || suspended) {
                        store.setConnectionStatus(false, suspended && store.connectionWanted ?
                            'PAUSED IN BACKGROUND' : 'DISCONNECTED')
                        break
                    }
                    store.setConnectionStatus(payload.isConnected, payload.status)
                    if (!payload.isConnected) resetAudioQueue()
                    if (payload.status === 'DSP UNAVAILABLE') { active = false; store.connectionWanted = false; stopListening() }
                    break
                case 'graphicData':
                    try { if (!store.frozen && !hidden.value) graphicCallback?.(payload) }
                    finally { worker?.postMessage({ type: 'ackGraphics' }) }
                    break
                case 'analysis': automation.accept(payload); break
                case 'telemetry':
                    store.frames = payload.frames; store.gaps = payload.gaps; store.processingMs = payload.processingMs
                    break
                case 'audioData':
                    try { if (store.isListening) feedAudio(payload) }
                    finally { worker?.postMessage({ type: 'ackAudio' }) }
                    break
                case 'streamGap':
                    resetAudioQueue(); if (payload === 'source') automation.reset()
                    break
                case 'streamInfo':
                    store.settings.samp_rate = payload.sampleRate; store.settings.lo_freq = payload.centerFreq
                    store.tune(store.tuneFreq)
                    break
                case 'correctionApplied': store.tune(payload.freq, payload.bw); break
                case 'error':
                    toast.add({ severity: 'error', summary: 'Receiver error', detail: payload, life: 4000 })
                    break
            }
        }
        if (store.connectionWanted) connect()
        syncVisibility()
    }
    watch([() => store.tuneFreq, () => store.bandwidth, () => store.sideband], () =>
        worker?.postMessage({ type: 'tune', payload: tuning() }))
    watch([() => store.fftSize, () => store.fps, () => store.frozen,
        () => store.settings.samp_rate, () => store.settings.lo_freq], () =>
        worker?.postMessage({ type: 'display', payload: display() }))
    watch([() => store.pauseHidden, () => store.isListening], syncVisibility)
    watch(() => store.volume, value => setVolume(value / 100))
    document.addEventListener('visibilitychange', syncVisibility)
    onUnmounted(() => {
        store.connectionWanted = true; stopListening()
        document.removeEventListener('visibilitychange', syncVisibility)
        worker?.postMessage({ type: 'disconnect' }); worker?.terminate(); worker = null
        store.setConnectionStatus(false, 'DISCONNECTED'); automation.reset()
    })
    return { initWorker, toggleAudio, toggleConnection, ...automation }
}
