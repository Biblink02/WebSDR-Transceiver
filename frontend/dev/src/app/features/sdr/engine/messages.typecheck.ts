import type { DspCommand, DspEvent, WaterfallCommand } from './messages'

// Compile-time protocol regression checks. This file has no runtime imports.
function contractChecks() {
    const listen: DspCommand = { type: 'listen', payload: true }
    // @ts-expect-error A numeric flag cannot silently replace a boolean command.
    const invalidListen: DspCommand = { type: 'listen', payload: 1 }
    // @ts-expect-error Acknowledgements must identify the producing session.
    const invalidAck: DspCommand = { type: 'ackAudio' }
    // @ts-expect-error Connection state is one typed state, not contradictory flags.
    const invalidState: DspEvent = { type: 'status', payload: { status: 'CONNECTED', isConnected: false } }
    // @ts-expect-error FFT payloads must be transferable float arrays.
    const invalidSpectrum: WaterfallCommand = { type: 'fft', payload: [1, 2, 3] }
    return [listen, invalidListen, invalidAck, invalidState, invalidSpectrum]
}
export type WorkerContractChecks = typeof contractChecks
