export interface Signal {
    low: number
    high: number
    peakFreq: number
    peakDb: number
    snr: number
    narrow: boolean
}
export interface Analysis { signals: Signal[]; noiseDb: number; peakDb: number }
export type ReceiverMode = 'ssb' | 'cw'
export interface Bookmark { frequency: number; bandwidth: number; side: 1 | -1; mode: ReceiverMode; band: number }
export const FFT_SIZES = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768]
export const PROFILES = {
    eco: { fftSize: 2048, fps: 5 }, balanced: { fftSize: 4096, fps: 20 },
    detail: { fftSize: 32768, fps: 15 },
} as const
export const clamp = (value: number, low: number, high: number) => Math.max(low, Math.min(high, value))

export function suggestedTune(signal: Signal, side: 1 | -1, minimum = 90, maximum = 15000) {
    const frequency = signal.narrow ? signal.peakFreq - side * 700 :
        side > 0 ? signal.low - 200 : signal.high + 200
    const bandwidth = signal.narrow ? 1800 : Math.ceil((signal.high - signal.low + 400) / 100) * 100
    return { frequency: Math.round(frequency), bandwidth: clamp(bandwidth, minimum, maximum) }
}
