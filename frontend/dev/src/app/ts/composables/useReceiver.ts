import { onUnmounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import DspWorker from '@/workers/dsp.worker.ts?worker'
import { useSdrStore } from '@/stores/sdr.store'
import { feedAudio, initAudio, resetAudioQueue, setVolume, stopAudioPlayback } from '@/AudioPlayer'

export function useReceiver() {
    const store = useSdrStore()
    const toast = useToast()
    let worker: Worker | null = null
    let audioGeneration = 0
    let audioStarting = false
    let manuallyDisconnected = false
    let graphicCallback: ((data: Float32Array) => void) | null = null
    const tuning = () => ({ freq: store.tuneFreq, bw: store.bandwidth, side: store.sideband })
    const connect = () => {
        manuallyDisconnected = false
        worker?.postMessage({ type: 'init', payload: {
            wsUrl: store.settings.ws_url,
            wasmUrl: new URL('/dsp.wasm', window.location.href).href,
            audioRate: store.settings.audio_rate,
            fftSize: store.settings.fft_size,
            calibration: store.settings.calibration,
            ...tuning(),
        } })
    }
    const stopListening = () => {
        audioGeneration++
        audioStarting = false
        store.isListening = false
        worker?.postMessage({ type: 'listen', payload: false })
        stopAudioPlayback()
    }
    const toggleAudio = async () => {
        if (store.isListening || audioStarting) { stopListening(); return }
        const generation = ++audioGeneration
        audioStarting = true
        try {
            await initAudio(store.settings.audio_rate)
            if (generation !== audioGeneration || manuallyDisconnected || !worker) return
            store.isListening = true
            worker.postMessage({ type: 'listen', payload: true })
        } catch (error) {
            if (generation !== audioGeneration) return
            stopListening()
            toast.add({ severity: 'error', summary: 'Audio unavailable',
                detail: (error as Error).message, life: 4000 })
        } finally {
            if (generation === audioGeneration) audioStarting = false
        }
    }
    const toggleConnection = () => {
        if (store.isConnected || !manuallyDisconnected) {
            manuallyDisconnected = true
            stopListening()
            worker?.postMessage({ type: 'disconnect' })
            store.setConnectionStatus(false, 'DISCONNECTED')
        } else connect()
    }
    const initWorker = (callback: (data: Float32Array) => void) => {
        graphicCallback = callback
        worker?.terminate()
        worker = new DspWorker()
        setVolume(store.volume / 100)
        worker.onerror = event => {
            store.setConnectionStatus(false, 'DSP ERROR')
            stopListening()
            toast.add({ severity: 'error', summary: 'Receiver error', detail: event.message, life: 4000 })
        }
        worker.onmessage = event => {
            const { type, payload } = event.data
            switch (type) {
                case 'status':
                    store.setConnectionStatus(payload.isConnected, payload.status)
                    if (!payload.isConnected) resetAudioQueue()
                    break
                case 'graphicData':
                    try { graphicCallback?.(payload) }
                    finally { worker?.postMessage({ type: 'ackGraphics' }) }
                    break
                case 'audioData':
                    try { if (store.isListening) feedAudio(payload) }
                    finally { worker?.postMessage({ type: 'ackAudio' }) }
                    break
                case 'streamGap': resetAudioQueue(); break
                case 'streamInfo':
                    store.settings.samp_rate = payload.sampleRate
                    store.settings.lo_freq = payload.centerFreq
                    break
                case 'correctionApplied':
                    store.setFrequency(payload.freq)
                    store.setBandwidth(payload.bw)
                    break
                case 'error':
                    toast.add({ severity: 'error', summary: 'Receiver error', detail: payload, life: 4000 })
                    break
            }
        }
        connect()
    }
    watch([() => store.tuneFreq, () => store.bandwidth, () => store.sideband], () => {
        worker?.postMessage({ type: 'tune', payload: tuning() })
    })
    watch(() => store.volume, value => setVolume(value / 100))
    onUnmounted(() => {
        manuallyDisconnected = true
        stopListening()
        worker?.postMessage({ type: 'disconnect' })
        worker?.terminate(); worker = null
    })
    return { initWorker, toggleAudio, toggleConnection }
}
