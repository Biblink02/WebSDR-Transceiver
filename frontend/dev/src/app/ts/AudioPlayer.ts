import {getConfig} from "@/ConfigStore";

let audioContext: AudioContext | null = null
let gainNode: GainNode | null = null
let nextStartTime = 0
let currentVolume = 1.0;

export async function initAudio() {
    const config = getConfig();
    if (audioContext && audioContext.state !== 'closed') {
        if (audioContext.state === 'suspended') await audioContext.resume()
        return
    }

    const AC = window.AudioContext || (window as any).webkitAudioContext

    audioContext = new AC({
        sampleRate: config.audio_rate,
        latencyHint: 'interactive'
    })

    gainNode = audioContext.createGain()
    gainNode.gain.value = currentVolume;
    gainNode.connect(audioContext.destination)

    nextStartTime = audioContext.currentTime
}

export function feedAudio(samples: Float32Array) {
    if (!audioContext || !gainNode) return

    const cfg = getConfig()

    const buffer = audioContext.createBuffer(1, samples.length, cfg.audio_rate)
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

export async function startAudioPlayback() {
    await initAudio()
}

export function stopAudioPlayback() {
    if (!audioContext) return
    audioContext.close().then()
    audioContext = null
    gainNode = null
    nextStartTime = 0
}

export function setVolume(v: number) {
    currentVolume = Math.max(0, Math.min(1, v));
    if (gainNode && audioContext) {
        gainNode.gain.setTargetAtTime(currentVolume, audioContext.currentTime, 0.05)
    }
}
