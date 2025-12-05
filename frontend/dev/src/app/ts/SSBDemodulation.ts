import {biquadLP, cos, type IProc, osc, sin} from "@thi.ng/dsp";
import {comp, iterator, map, takeNth} from "@thi.ng/transducers";

type Complex = number[];

/**
 * Creates a stateful transducer-like map function for filtering complex signals
 * using a Biquad Low-Pass filter.
 * @param cutoff - Normalized cutoff frequency (0 .. 0.5)
 * @param q - Filter Q (resonance)
 */
const complexFilter = (cutoff: number, q: number): ((sample: Complex) => Complex) => {
    // Instantiate separate filters for the I and Q channels
    const filterI: IProc<number, number> = biquadLP(cutoff, q);
    const filterQ: IProc<number, number> = biquadLP(cutoff, q);

    return (sample: Complex): Complex => [
        filterI.next(sample[0]).value,
        filterQ.next(sample[1]).value,
    ];
};

/**
 * Demodulates an SSB signal from a complex I/Q stream.
 *
 * @param complexSignal - Input iterable of I/Q samples [I, Q]
 * @param sampleRate - Sample rate of the input signal (e.g., 2048000)
 * @param audioSampleRate - Desired audio sample rate (e.g., 48000)
 * @param frequency - Center frequency of the SSB signal's suppressed carrier (offset from 0 Hz)
 * @param bandwidth - The bandwidth of the audio (e.g., 3000 Hz)
 * @returns An array of demodulated audio samples (float)
 */
export function demodulateSSB(
    complexSignal: Iterable<Complex>,
    sampleRate: number,
    audioSampleRate: number,
    frequency: number,
    bandwidth: number
): Float32Array<ArrayBuffer> {

    const decimationFactor = Math.round(sampleRate / audioSampleRate);
    if (decimationFactor < 1 || sampleRate % audioSampleRate !== 0) {
        /*console.warn(
            `Sample rate ${sampleRate} is not an integer multiple of audio rate ${audioSampleRate}.
            Using decimation factor ${decimationFactor}, actual audio rate may vary.`
        );*/
    }

    // Calculate normalized frequencies for the LO and the filter
    const cutoffRel = bandwidth / sampleRate;
    const freqRel = frequency / sampleRate;

    // Create oscillators for the Local Oscillator (LO)
    const loReal = osc(cos, freqRel);
    const loImag = osc(sin, freqRel);

    // Create the complex filter using the documented biquadLP
    // 0.707 is a standard "Butterworth" Q value (no resonance)
    const filter = complexFilter(cutoffRel, 0.707);

    const ssbDemodChain = comp(
        // Step 1: Frequency shift (complex multiplication)
        map((sample: Complex) => {
            const I = sample[0];
            const Q = sample[1];
            const loR = loReal.next().value;
            // Use conjugate of LO: [R, -I]
            const loI = -loImag.next().value;

            // Complex multiplication: (I + iQ) * (loR + iloI)
            const outI = I * loR - Q * loI; // Real part: ac - bd
            const outQ = I * loI + Q * loR; // Imag part: ad + bc

            return [outI, outQ];
        }),
        // Step 2: Low-pass filter the I/Q signal
        map(filter),
        // Step 3: Decimate (downsample) to the target audio rate
        // Corretto: Sostituito 'downsample' con 'takeNth'
        takeNth(decimationFactor),
        // Step 4: Take the Real (I) part as the final audio signal
        map((sample: Complex) => sample[0])
    );

    return Float32Array.from(iterator(ssbDemodChain, complexSignal));
}
