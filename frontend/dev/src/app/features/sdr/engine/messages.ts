import type { IqSelection } from '&/config'
import type { Analysis, ReceiverMode } from '../core/types'

export type ReceiverState = 'disconnected' | 'loading' | 'connecting' | 'warming' |
    'connected' | 'reconnecting' | 'suspended' | 'unavailable' | 'failed' | 'connection-error'
export const STATE_LABELS: Record<ReceiverState, string> = {
    disconnected: 'DISCONNECTED', loading: 'LOADING DSP...', connecting: 'CONNECTING...',
    warming: 'WAKING RECEIVER...', connected: 'CONNECTED', reconnecting: 'RECONNECTING...',
    suspended: 'PAUSED IN BACKGROUND', unavailable: 'DSP UNAVAILABLE', failed: 'DSP ERROR',
    'connection-error': 'CONNECTION ERROR',
}
export interface Tuning { freq: number; bw: number; side: 1 | -1; mode: ReceiverMode; pitch: number }
export interface AudioSettings { agc: boolean; squelch: boolean; threshold: number }
export interface DisplaySettings { fftSize: number; fps: number; visible: boolean; analyze: boolean; limitLow: number; limitHigh: number }
export interface ReceiverConfig extends Tuning, DisplaySettings {
    band: IqSelection
    wsUrl: string; wasmUrl: string; audioRate: number; calibration: number; audio: AudioSettings
}
export type DspCommand =
    | { type: 'init'; payload: ReceiverConfig }
    | { type: 'disconnect' }
    | { type: 'listen'; payload: boolean }
    | { type: 'tune'; payload: Tuning }
    | { type: 'audio'; payload: AudioSettings }
    | { type: 'display'; payload: DisplaySettings }
    | { type: 'ackAudio' | 'ackGraphics'; session: number }
export type DspEvent =
    | { type: 'status'; payload: ReceiverState }
    | { type: 'graphicData' | 'audioData'; payload: Float32Array; session: number }
    | { type: 'analysis'; payload: Analysis }
    | { type: 'telemetry'; payload: { frames: number; gaps: number; processingMs: number; rssi: number; squelchOpen: boolean } }
    | { type: 'streamGap'; payload: 'source' | 'tune' | 'audio' }
    | { type: 'streamInfo'; payload: { sampleRate: number; centerFreq: number } }
    | { type: 'correctionApplied'; payload: { freq: number; bw: number } }
    | { type: 'error'; payload: { message: string; fatal: boolean } }
export interface WaterfallSettings {
    width: number; viewMin: number; viewMax: number; rate: number; center: number;
    calibration: number; gain: number; range: number; gamma: number; palette: string
}
export type WaterfallCommand = { type: 'config'; payload: WaterfallSettings } |
    { type: 'fft'; payload: Float32Array } | { type: 'clear' | 'ackFrame' }
export type WaterfallEvent = { type: 'frame'; bitmap: ImageBitmap } | { type: 'fftConsumed' }

export type TypedWorker<In, Out> = Omit<Worker, 'postMessage' | 'onmessage'> & {
    postMessage(message: In, transfer?: Transferable[]): void
    onmessage: ((event: MessageEvent<Out>) => void) | null
}
export function typedWorker<In, Out>(worker: Worker) { return worker as TypedWorker<In, Out> }
export function exhaustive(value: never): never { throw new Error(`Unexpected worker message: ${JSON.stringify(value)}`) }
