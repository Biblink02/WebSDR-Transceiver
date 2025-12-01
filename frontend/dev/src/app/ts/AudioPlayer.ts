import { Float32PcmPlayer } from '@yume-chan/pcm-player';

const SAMPLE_RATE = 48000;
const CHANNEL_COUNT = 1;

let player: Float32PcmPlayer | null = null;
let currentVolume = 1.0;

export function initAudio() {
    if (!player) {
        player = new Float32PcmPlayer(SAMPLE_RATE, CHANNEL_COUNT);
    }
}

export function feedAudio(samples: Float32Array) {
    if (!player) return;

    try {
        if (currentVolume !== 1.0) {
            for (let i = 0; i < samples.length; i++) {
                samples[i] *= currentVolume;
            }
        }
        player.feed(samples);
    } catch (e) {
        console.warn("Audio packet dropped:", e);
    }
}

export function startAudioPlayback() {
    initAudio();
    player?.start().catch(e => console.error("Audio playback failed:", e));
}

export function stopAudioPlayback() {
    if (player) {
        player.stop();
        player = null;
    }
}

export function getVolume(): number {
    return currentVolume;
}

export function setVolume(val: number) {
    currentVolume = Math.max(0, Math.min(1, val));
}
