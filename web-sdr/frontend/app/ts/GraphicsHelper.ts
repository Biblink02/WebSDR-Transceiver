export function fftShift(data: Float32Array): Float32Array {
    console.log(data)
    const N = data.length;
    const halfN = Math.floor(N / 2);

    const shifted = new Float32Array(N);

    shifted.set(data.subarray(halfN));

    shifted.set(data.subarray(0, halfN), halfN);

    return shifted;
}
