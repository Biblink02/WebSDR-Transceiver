import { onUnmounted, reactive, watch } from 'vue'
import { useSdrStore } from '../store'
import { recordingStream, releaseRecordingStream } from '../engine/AudioPlayer'

const MAX_SECONDS = 600, MAX_BYTES = 32 * 1024 * 1024, MAX_EVENTS = 4096
const FORMATS = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4']
export function useRecording() {
    const store = useSdrStore()
    const mime = typeof MediaRecorder === 'undefined' ? '' : FORMATS.find(format => MediaRecorder.isTypeSupported(format)) ?? ''
    const state = reactive({ supported: Boolean(mime), active: false, finishing: false, seconds: 0,
        bytes: 0, audioUrl: '', metadataUrl: '', filename: '', error: '', reason: '' })
    let recorder: MediaRecorder | null = null, timer: ReturnType<typeof setInterval> | null = null
    let chunks: Blob[] = [], events: object[] = [], started = 0, disposed = false
    const snapshot = () => ({ elapsedSeconds: (performance.now() - started) / 1000,
        frequencyHz: store.tuneFreq + store.settings.lnb_lo_freq, bandwidthHz: store.bandwidth,
        mode: store.mode === 'cw' ? 'CW' : store.sideband > 0 ? 'USB' : 'LSB', cwPitchHz: store.cwPitch,
        audioAgc: store.audioAgc, squelch: store.squelch, squelchThresholdDbfs: store.squelchThreshold,
        connection: store.connectionState, sourceGaps: store.gaps })
    function revoke() {
        if (state.audioUrl) URL.revokeObjectURL(state.audioUrl)
        if (state.metadataUrl) URL.revokeObjectURL(state.metadataUrl)
        state.audioUrl = ''; state.metadataUrl = ''
    }
    function stop(reason = 'manual') {
        if (!recorder || recorder.state === 'inactive') return
        state.active = false; state.finishing = true; state.reason = reason
        state.seconds = (performance.now() - started) / 1000
        if (timer) clearInterval(timer)
        timer = null; recorder.stop()
    }
    function start() {
        if (!mime || !store.isListening || state.active || state.finishing) return
        revoke(); state.error = ''; state.reason = ''; state.seconds = 0; state.bytes = 0
        chunks = []; events = []; started = performance.now()
        const startedAt = new Date().toISOString()
        const initial = snapshot()
        state.filename = 'websdr-' + startedAt.replace(/[:.]/g, '-') + '-' + initial.frequencyHz
        try {
            const session = new MediaRecorder(recordingStream(), { mimeType: mime, audioBitsPerSecond: 96000 })
            recorder = session; events.push(initial)
            session.ondataavailable = event => {
                if (!event.data.size || disposed) return
                if (state.bytes + event.data.size > MAX_BYTES) { stop('size limit'); return }
                chunks.push(event.data); state.bytes += event.data.size
            }
            session.onerror = () => { state.error = 'Recording failed'; stop('error') }
            session.onstop = () => {
                releaseRecordingStream(); recorder = null; state.finishing = false
                if (disposed) { chunks = []; events = []; return }
                const audio = new Blob(chunks, { type: session.mimeType })
                const metadata = { version: 1, startedAt, durationSeconds: state.seconds,
                    stopReason: state.reason, mimeType: session.mimeType, sampleRateHz: store.settings.audio_rate,
                    bytes: state.bytes, volumeIndependent: true, events }
                if (audio.size) {
                    state.audioUrl = URL.createObjectURL(audio)
                    state.metadataUrl = URL.createObjectURL(new Blob([JSON.stringify(metadata, null, 2)], { type: 'application/json' }))
                }
                chunks = []; events = []
            }
            session.start(1000); state.active = true
            timer = setInterval(() => {
                state.seconds = (performance.now() - started) / 1000
                if (state.seconds >= MAX_SECONDS) stop('duration limit')
            }, 250)
        } catch (error) { state.error = (error as Error).message; recorder = null; releaseRecordingStream() }
    }
    watch(() => store.isListening, listening => { if (!listening) stop('audio stopped') }, { flush: 'sync' })
    watch(() => [store.tuneFreq, store.bandwidth, store.sideband, store.mode, store.cwPitch,
        store.audioAgc, store.squelch, store.squelchThreshold, store.connectionState, store.gaps], () => {
        if (state.active && events.length < MAX_EVENTS) events.push(snapshot())
    })
    onUnmounted(() => {
        disposed = true; stop('page closed'); revoke()
        if (timer) clearInterval(timer)
    })
    return { state, start, stop: () => stop(), toggle: () => state.active ? stop() : start(),
        extension: mime.includes('ogg') ? 'ogg' : mime.includes('mp4') ? 'm4a' : 'webm' }
}
