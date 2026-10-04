import { type Analysis, type Signal, clamp } from './types'

// Signal-region estimation consumes liquid-dsp spectra; no sample-level DSP here.
export class SpectrumAnalyzer {
    private average = new Float32Array(0)
    private frames = 0
    private lastTime = 0
    private persistence = new Uint8Array(0)
    reset() { this.average = new Float32Array(0); this.persistence = new Uint8Array(0); this.frames = 0; this.lastTime = 0 }
    update(spectrum: Float32Array, rate: number, center: number, now: number,
        limitLow = center - rate / 2, limitHigh = center + rate / 2): Analysis | null {
        if (this.average.length !== spectrum.length) {
            this.average = new Float32Array(spectrum.length); this.frames = 0; this.lastTime = 0
            this.persistence = new Uint8Array(spectrum.length)
        }
        const alpha = this.frames ? 0.22 : 1
        for (let i = 0; i < spectrum.length; i++) {
            const db = Number.isFinite(spectrum[i]) ? spectrum[i] : -200
            this.average[i] += alpha * (db - this.average[i])
        }
        this.frames++
        const n = this.average.length, binHz = rate / n, start = center - rate / 2
        const first = clamp(Math.ceil((limitLow - start) / binHz), 2, n - 3)
        const last = clamp(Math.floor((limitHigh - start) / binHz), first, n - 3)
        const samples: number[] = []
        const stride = Math.max(1, Math.floor((last - first) / 512))
        for (let i = first; i <= last; i += stride) samples.push(this.average[i])
        samples.sort((a, b) => a - b)
        // Robust lower percentile prevents a few carriers from setting the noise floor.
        const noiseDb = Math.max(-190, samples[Math.floor(samples.length * 0.35)] ?? -190)
        const threshold = noiseDb + 12
        for (let i = first; i <= last; i++) this.persistence[i] = spectrum[i] >= threshold ?
            Math.min(3, this.persistence[i] + 1) : Math.max(0, this.persistence[i] - 1)
        if (this.frames < 3 || now - this.lastTime < 250) return null
        this.lastTime = now
        const regions: { low: number; high: number; peak: number }[] = []
        const maxGap = Math.max(1, Math.floor(400 / binHz))
        let region: typeof regions[number] | null = null
        let peakDb = noiseDb
        for (let i = first; i <= last; i++) {
            // Ignore the receiver's DC bin and immediate neighbours.
            if (Math.abs(i - n / 2) <= 1) continue
            const db = this.average[i]
            peakDb = Math.max(peakDb, db)
            if (db < threshold) continue
            if (!region || i - region.high > maxGap) {
                region = { low: i, high: i, peak: i }; regions.push(region)
            } else {
                region.high = i
                if (db > this.average[region.peak]) region.peak = i
            }
        }
        // Measure occupied edges relative to each peak, avoiding Hann leakage tails.
        for (const r of regions) {
            const edge = Math.max(threshold, this.average[r.peak] - 25)
            while (r.low < r.peak && this.average[r.low] < edge) r.low++
            while (r.high > r.peak && this.average[r.high] < edge) r.high--
        }
        const signals: Signal[] = regions.filter(r => this.persistence[r.peak] >= 3 && this.average[r.peak] - noiseDb >= 15).map(r => ({
            low: start + r.low * binHz, high: start + r.high * binHz,
            peakFreq: start + (r.peak + peakFraction(this.average, r.peak)) * binHz, peakDb: this.average[r.peak],
            snr: this.average[r.peak] - noiseDb,
            narrow: (r.high - r.low) * binHz < Math.max(500, binHz * 5),
        })).sort((a, b) => b.snr - a.snr).slice(0, 12)
        return { signals, noiseDb, peakDb }
    }
}

// Sub-bin estimate of the library Hann FFT peak; never a modulation/carrier detector.
function peakFraction(spectrum: Float32Array, bin: number) {
    const left = spectrum[bin - 1], peak = spectrum[bin], right = spectrum[bin + 1]
    const curvature = left - 2 * peak + right
    return Number.isFinite(curvature) && curvature < -0.01 ? clamp(0.5 * (left - right) / curvature, -0.5, 0.5) : 0
}

export function autoDisplay(analysis: Analysis, calibration: number) {
    const top = analysis.peakDb + 6
    return { gain: clamp(calibration - top, -40, 120), range: clamp(top - analysis.noiseDb + 4, 20, 100) }
}
