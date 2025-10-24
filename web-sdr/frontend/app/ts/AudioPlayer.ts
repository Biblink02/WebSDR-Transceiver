/**
 * Plays an array of raw audio samples (number[] or Float32Array)
 * using the Web Audio API.
 * This code must be executed in a browser environment.
 *
 * @param samples - The array of audio samples (e.g. [-0.5, 0.1, 0.8, ...])
 * @param audioSampleRate - The audio sample rate (e.g. 48000)
 */
const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();

export function playAudio(samples: number[] | Float32Array, audioSampleRate: number) {
    console.log("Samples:\n")
    console.log(samples)
    let i=1000000000000;
    while(--i);
    const numSamples = samples.length;
    const audioBuffer = audioContext.createBuffer(
        1,
        numSamples,
        audioContext.sampleRate
    );
    const channelData = audioBuffer.getChannelData(0);

    channelData.set(samples);

    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    console.log("Avvio riproduzione audio...");
    source.start(0);

    source.onended = () => {
        console.log("Riproduzione terminata.");
        // Potresti voler chiudere il context qui se non ti serve più
        // audioContext.close();
    };
}
