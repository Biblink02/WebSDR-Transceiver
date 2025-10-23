import {
    osc,
    OscType,
    mulC,
    fir,
    sinc,
    window,
    kaiser,
    type IProc,
} from "@thi.ng/dsp";
import { map, iterator, comp, downsample } from "@thi.ng/transducers";

// Define a type alias for complex numbers as [real, imag]
type Complex = number[];

/**
 * Creates a stateful Numerical Controlled Oscillator (NCO) generator.
 * @param freqRel - Normalized frequency (frequency / sampleRate)
 */
/* NOTA: Questa funzione personalizzata è stata rimossa per utilizzare
   i generatori 'osc()' integrati, come da richiesta.
const createNCO = (freqRel: number): (() => Complex) => {
    let phase = 0;
    const delta = freqRel * Math.PI * 2;
    return (): Complex => {
        // e^(j*phase) = cos(phase) + j*sin(phase)
        // We need the conjugate for down-shifting: e^(-j*phase)
        const res: Complex = [Math.cos(phase), -Math.sin(phase)];
        phase += delta;
        return res;
    };
};
*/

/**
 * Creates a stateful transducer-like map function for FIR filtering complex signals.
 * @param taps - FIR filter tap coefficients
 */
const complexFIR = (taps: number[]): ((sample: Complex) => Complex) => {
    const firI: IProc<number, number> = fir(taps);
    const firQ: IProc<number, number> = fir(taps);
    return (sample: Complex): Complex => [
        firI.next(sample[0]).value,
        firQ.next(sample[1]).value,
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
): number[] {

    const decimationFactor = Math.round(sampleRate / audioSampleRate);
    if (decimationFactor < 1 || sampleRate % audioSampleRate !== 0) {
        console.warn(
            `Sample rate ${sampleRate} is not an integer multiple of audio rate ${audioSampleRate}.
            Using decimation factor ${decimationFactor}, actual audio rate may vary.`
        );
    }

    const cutoffRel = bandwidth / sampleRate;
    const numTaps = 101;
    const taps = window(
        kaiser(numTaps, 5.0), // Kaiser window (beta=5 is a good general-purpose choice)
        sinc(numTaps, cutoffRel) // Sinc kernel for LPF
    );

    const freqRel = frequency / sampleRate;
    const loReal = osc(OscType.COSINE, freqRel);
    const loImag = osc(OscType.SINE, freqRel);
    const filter = complexFIR(taps);

    const ssbDemodChain = comp(
        map((sample: Complex) =>
            mulC(sample, [loReal.next().value, -loImag.next().value])
        ),
        map(filter),
        downsample(decimationFactor),
        map((sample: Complex) => sample[0])
    );

    const audioOutput = [...iterator(ssbDemodChain, complexSignal)];

    return audioOutput;
}


