let audioContext: AudioContext | null = null
let gainNode: GainNode | null = null
let nextStartTime = 0
let currentVolume = 1
let activeSampleRate = 48000
const sources = new Set<AudioBufferSourceNode>()
const MAX_SCHEDULED_SECONDS = 0.25
const SCHEDULE_LEAD_SECONDS = 0.02

export async function initAudio(sampleRate: number) {
    if (!Number.isFinite(sampleRate) || sampleRate <= 0) throw new Error('Invalid audio rate')
    if (audioContext && activeSampleRate !== sampleRate) stopAudioPlayback()
    activeSampleRate = sampleRate
    if (!audioContext || audioContext.state === 'closed') {
        const AC = window.AudioContext || (window as any).webkitAudioContext
        audioContext = new AC({ sampleRate, latencyHint: 'interactive' })
        gainNode = audioContext!.createGain()
        gainNode.gain.value = currentVolume
        gainNode.connect(audioContext!.destination)
        nextStartTime = audioContext!.currentTime
    }
    if (audioContext!.state === 'suspended') await audioContext!.resume()
}

export function resetAudioQueue() {
    for (const source of sources) {
        source.onended = null
        try { source.stop() } catch { /* Already stopped. */ }
        source.disconnect()
    }
    sources.clear()
    nextStartTime = audioContext ? audioContext.currentTime + SCHEDULE_LEAD_SECONDS : 0
}

export function feedAudio(samples: Float32Array) {
    if (!audioContext || !gainNode || audioContext.state !== 'running' || !samples.length) return
    const limit = Math.floor(activeSampleRate * (MAX_SCHEDULED_SECONDS - SCHEDULE_LEAD_SECONDS))
    if (samples.length > limit) samples = samples.subarray(samples.length - limit)
    if (nextStartTime - audioContext.currentTime + samples.length / activeSampleRate > MAX_SCHEDULED_SECONDS)
        resetAudioQueue()
    const buffer = audioContext.createBuffer(1, samples.length, activeSampleRate)
    buffer.copyToChannel(samples as Float32Array<ArrayBuffer>, 0)
    nextStartTime = Math.max(nextStartTime, audioContext.currentTime + SCHEDULE_LEAD_SECONDS)
    const source = audioContext.createBufferSource()
    source.buffer = buffer; source.connect(gainNode)
    sources.add(source)
    source.onended = () => { sources.delete(source); source.disconnect() }
    source.start(nextStartTime)
    nextStartTime += buffer.duration
}

export function stopAudioPlayback() {
    resetAudioQueue()
    const context = audioContext
    audioContext = null; gainNode = null; nextStartTime = 0
    if (context && context.state !== 'closed') void context.close()
}

export function setVolume(value: number) {
    if (!Number.isFinite(value)) return
    currentVolume = Math.max(0, Math.min(1, value))
    if (gainNode && audioContext)
        gainNode.gain.setTargetAtTime(currentVolume, audioContext.currentTime, 0.05)
}
