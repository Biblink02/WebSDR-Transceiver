import { clamp, type Signal } from './types'

export interface TrackingResult { state: 'tracking' | 'lost'; drift: number; signal: Signal | null }
const reference = (signal: Signal) => signal.narrow ? signal.peakFreq : (signal.low + signal.high) / 2

// A pinned target never switches to another carrier after signal loss.
export class SignalTracker {
    private anchor: number
    private last: Signal
    private estimate = 0
    constructor(signal: Signal) { this.anchor = reference(signal); this.last = { ...signal } }
    update(signals: Signal[], binHz: number, maxDrift: number): TrackingResult {
        if (!Number.isFinite(binHz) || binHz <= 0 || !Number.isFinite(maxDrift))
            return { state: 'lost', drift: this.estimate, signal: null }
        maxDrift = clamp(maxDrift, 100, 5000)
        const radius = this.last.narrow ? Math.max(80, Math.min(400, binHz * 2)) :
            Math.max(binHz * 2, (this.last.high - this.last.low) / 2)
        const candidate = signals.filter(s => s.narrow === this.last.narrow &&
            Math.abs(reference(s) - this.anchor) <= maxDrift &&
            Math.abs(reference(s) - reference(this.last)) <= radius)
            .sort((a, b) => Math.abs(reference(a) - reference(this.last)) - Math.abs(reference(b) - reference(this.last)))[0]
        if (!candidate) return { state: 'lost', drift: this.estimate, signal: null }
        this.last = candidate
        this.estimate += clamp((reference(candidate) - this.anchor - this.estimate) * 0.35, -50, 50)
        return { state: 'tracking', drift: this.estimate, signal: candidate }
    }
}
