import audioWorkletUrl from '@/workers/audio.worker.ts?worker&url';
import { getConfig } from "@/ConfigStore";

const SAMPLE_RATE = 48000;

let audioContext: AudioContext | null = null;
let workletNode: AudioWorkletNode | null = null;
let gainNode: GainNode | null = null;

export async function initAudio() {
    if (audioContext && audioContext.state !== 'closed') {
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }
        return;
    }

    const config = getConfig();

    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    audioContext = new AudioContextClass({
        sampleRate: SAMPLE_RATE,
        latencyHint: 'interactive'
    });

    try {
        await audioContext.audioWorklet.addModule(audioWorkletUrl);

        workletNode = new AudioWorkletNode(audioContext, 'pcm-processor', {
            processorOptions: {
                bufferThreshold: config.BUFFER_THRESHOLD,
                maxQueueSize: config.MAX_QUEUE_SIZE
            }
        });

        gainNode = audioContext.createGain();
        gainNode.gain.value = 1.0;

        workletNode.connect(gainNode);
        gainNode.connect(audioContext.destination);

        console.log("Audio Engine Initialized");
    } catch (e) {
        console.error("Failed to load Audio Worklet:", e);
    }
}

export function feedAudio(samples: Float32Array) {
    if (workletNode) {
        workletNode.port.postMessage(samples);
    }
}

export async function startAudioPlayback() {
    await initAudio();
}

export function stopAudioPlayback() {
    if (audioContext) {
        audioContext.close();
        audioContext = null;
        workletNode = null;
        gainNode = null;
    }
}

export function setVolume(val: number) {
    if (gainNode && audioContext) {
        const clamped = Math.max(0, Math.min(1, val));
        gainNode.gain.setTargetAtTime(clamped, audioContext.currentTime, 0.05);
    }
}
