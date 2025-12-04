import {Float32PcmPlayer} from '@yume-chan/pcm-player';

let player: Float32PcmPlayer | null = null;
let isRunning = false;
let currentVolume = 1.0; // Default 100%

export function initAudioPlayer(sampleRate: number, channelCount: number) {
    isRunning = false;

    if (player) {
        try {
            player.stop();
        } catch (e) {
            // Ignore errors
        }
    }

    player = new Float32PcmPlayer(sampleRate, channelCount);
}

export function setVolume(value: number) {
    // Clamp between 0.0 and 1.0
    currentVolume = Math.max(0, Math.min(1, value));
}

export function feedAudio(samples: Float32Array) {
    if (!player || !isRunning) return;

    try {
        // Apply software volume if not at 100%
        if (currentVolume !== 1.0) {
            for (let i = 0; i < samples.length; i++) {
                samples[i] *= currentVolume;
            }
        }

        player.feed(samples);
    } catch (e: any) {
        if (e.message && e.message.includes('stopped')) {
            isRunning = false;
            console.warn("Audio packet dropped: Player is stopped.");
        } else {
            console.error(e);
        }
    }
}

export async function startAudioPlayback() {
    if (!player) return;
    try {
        await player.start();
        isRunning = true;
        console.log("Audio Engine Started");
    } catch (e) {
        console.error("Audio Engine Start Failed", e);
    }
}

export async function stopAudioPlayback() {
    isRunning = false;
    if (player) {
        try {
            await player.stop();
        } catch (e) {
            // Ignore errors
        }
    }
}
