import { onUnmounted, ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import SocketWorker from '@/workers/socket.worker.ts?worker'
import { useSdrStore } from '@/stores/sdr.store'
import { feedAudio, initAudio, setVolume, stopAudioPlayback } from "@/AudioPlayer"

export function useSdrWorker() {
    const store = useSdrStore()
    const toast = useToast()
    const worker = ref<Worker | null>(null)

    let graphicCallback: ((data: Float32Array) => void) | null = null

    const initWorker = (onGraphicData: (data: Float32Array) => void) => {
        graphicCallback = onGraphicData
        worker.value = new SocketWorker()
        if (!worker.value) return

        setVolume(store.volume / 100)

        worker.value.onmessage = handleWorkerMessage

        // Use store.settings
        const eventConfig = {
            WS_GRAPHICS_EVENT: store.settings.ws_graphics_event,
            WS_AUDIO_EVENT: store.settings.ws_audio_event,
            WS_SERVER_FULL_EVENT: store.settings.ws_server_full_event,
            WS_WORKER_ASSIGNED_EVENT: store.settings.ws_worker_assigned_event,
            WS_WORKER_RELEASED_EVENT: store.settings.ws_worker_released_event,
            WS_CORRECTION_EVENT: store.settings.ws_correction_event,
            WS_CONNECT_EVENT: store.settings.ws_connect_event,
            WS_DISCONNECT_EVENT: store.settings.ws_disconnect_event,
            WS_REQUEST_WORKER_EVENT: store.settings.ws_request_worker_event,
            WS_DISMISS_WORKER_EVENT: store.settings.ws_dismiss_worker_event,
            WS_TUNE_EVENT: store.settings.ws_tune_event
        }

        worker.value.postMessage({
            type: 'init',
            payload: {
                wsUrl: store.settings.ws_url,
                events: eventConfig
            }
        })
    }

    const handleWorkerMessage = (event: MessageEvent) => {
        const { type, payload } = event.data

        switch (type) {
            case 'status':
                store.setConnectionStatus(payload.isConnected, payload.status)
                if (!payload.isConnected) stopListening()
                break

            case 'graphicData':
                if (graphicCallback) graphicCallback(payload)
                break

            case 'audioData':
                feedAudio(payload)
                break

            case 'workerAssigned':
                store.setWorkerStatus('LISTENING', payload.worker)
                if (payload.freq) store.setFrequency(payload.freq)
                if (payload.error) {
                    toast.add({ severity: 'warn', summary: 'Warning', detail: payload.error, life: 3000 })
                }
                break

            case 'workerReleased':
                store.setWorkerStatus('IDLE')
                stopAudioPlayback()
                break

            case 'serverFull':
                store.setWorkerStatus('FULL',null,2000)
                toast.add({ severity: 'error', summary: 'Server Busy', detail: 'No audio workers available.', life: 3000 })
                break

            case 'correctionApplied':
                toast.add({ severity: 'info', summary: 'Correction', detail: payload.message, life: 3000 })
                if (payload.freq) store.setFrequency(payload.freq)
                if (payload.bw) store.setBandwidth(payload.bw)
                break

            case 'error':
                console.error("Worker Error:", payload)
                toast.add({ severity: 'error', summary: 'Error', detail: payload, life: 3000 })
                break
        }
    }

    const startListening = () => {
        // Pass audio rate from store to AudioPlayer
        initAudio(store.settings.audio_rate)

        worker.value?.postMessage({
            type: 'requestWorker',
            payload: { freq: store.tuneFreq, bw: store.bandwidth }
        })
    }

    const stopListening = () => {
        if (store.workerStatus === 'LISTENING') {
            worker.value?.postMessage({ type: 'releaseWorker' })
        }
        stopAudioPlayback()
    }

    const toggleAudio = () => {
        if (store.workerStatus === 'LISTENING') {
            stopListening()
        } else {
            startListening()
        }
    }

    watch([() => store.tuneFreq, () => store.bandwidth], ([newFreq, newBw]) => {
        if (store.workerStatus === 'LISTENING') {
            worker.value?.postMessage({
                type: 'tune',
                payload: { freq: Number(newFreq), bw: Number(newBw) }
            })
        }
    })

    watch(() => store.volume, (newVol) => {
        setVolume(newVol / 100)
    })

    onUnmounted(() => {
        stopListening()
        if (worker.value) {
            worker.value.postMessage({ type: 'disconnect' })
            worker.value.terminate()
        }
    })

    return { initWorker, toggleAudio }
}
