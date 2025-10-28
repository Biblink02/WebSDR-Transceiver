
import { Float32PcmPlayer } from '@yume-chan/pcm-player';

const SAMPLE_RATE = 48000;
const CHANNEL_COUNT = 1;

const player = new Float32PcmPlayer(SAMPLE_RATE, CHANNEL_COUNT);


export function feedAudio(samples: Float32Array) {
    if (player) {
        player.feed(samples);
    }
}


export function startAudioPlayback() {
    if (player) {
        player.start().then();
    }
}


export function stopAudioPlayback() {
    if (player) {
        player.stop().then();
    }
}
