let audioContext: AudioContext | null = null
let gainNode: GainNode | null = null
let nextStartTime = 0
let currentVolume = 1.0
let activeSampleRate = 48000 // Default fallback

export async function initAudio(sampleRate: number) {
    activeSampleRate = sampleRate

    if (audioContext && audioContext.state !== 'closed') {
        if (audioContext.state === 'suspended') await audioContext.resume()
        return
    }

    const AC = window.AudioContext || (window as any).webkitAudioContext

    audioContext = new AC({
        sampleRate: activeSampleRate,
        latencyHint: 'interactive'
    })

    gainNode = audioContext.createGain()
    gainNode.gain.value = currentVolume
    gainNode.connect(audioContext.destination)

    nextStartTime = audioContext.currentTime
}

export function feedAudio(samples: Float32Array) {
    if (!audioContext || !gainNode) return

    // Use the locally stored sample rate
    const buffer = audioContext.createBuffer(1, samples.length, activeSampleRate)
    buffer.copyToChannel(samples, 0)

    const offset = 0.02
    if (nextStartTime < audioContext.currentTime)
        nextStartTime = audioContext.currentTime + offset

    const source = audioContext.createBufferSource()
    source.buffer = buffer
    source.connect(gainNode)
    source.start(nextStartTime)

    nextStartTime += buffer.duration
}

export function stopAudioPlayback() {
    if (!audioContext) return
    audioContext.close().then()
    audioContext = null
    gainNode = null
    nextStartTime = 0
}

export function setVolume(v: number) {
    currentVolume = Math.max(0, Math.min(1, v))
    if (gainNode && audioContext) {
        gainNode.gain.setTargetAtTime(currentVolume, audioContext.currentTime, 0.05)
    }
}
