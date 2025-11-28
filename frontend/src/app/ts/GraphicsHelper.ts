import {ComplexArray} from "@thi.ng/dsp";

export function fftShift(data: Float32Array): Float32Array {
    const N = data.length;
    const halfN = Math.floor(N / 2);

    const shifted = new Float32Array(N);

    shifted.set(data.subarray(halfN));

    shifted.set(data.subarray(0, halfN), halfN);

    return shifted;
}

export function calculateMagnitudesDb(
    fftData: ComplexArray,
    minDb: number = -100
): Float32Array {

    const fftReal = fftData[0];
    const fftImag = fftData[1];
    const N = fftReal.length;

    if (N === 0) return new Float32Array(0);

    if (N !== fftImag.length) {
        console.error("Different size of real and imaginary arrays");
        return new Float32Array(0);
    }

    const magnitudesDb = new Float32Array(N);

    for (let i = 0; i < N; i++) {
        const mag = Math.sqrt(fftReal[i] * fftReal[i] + fftImag[i] * fftImag[i]);

        const normMag = mag / N;

        if (normMag === 0) {
            magnitudesDb[i] = minDb;
        } else {
            const db = 20 * Math.log10(normMag);
            magnitudesDb[i] = Math.max(minDb, db);
        }
    }

    return magnitudesDb;
}
