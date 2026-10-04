import { watch } from 'vue'
import { useSdrStore } from '../store'
import { autoDisplay } from '../core/analysis'
import { suggestedTune, type Analysis, type Signal } from '../core/types'
import { SignalTracker } from '../core/tracking'

export function useAutomation() {
    const store = useSdrStore()
    let tracked: Signal | null = null
    let lastSeen = 0
    let lastTune = 0
    let pinned: SignalTracker | null = null, pinnedFrequency = 0
    function targetTune(signal: Signal) {
        return store.mode === 'cw' ? { frequency: Math.round(signal.peakFreq), bandwidth: Math.min(500, store.bandwidth) } :
            suggestedTune(signal, store.sideband, store.settings.min_bw_limit, store.settings.max_bw_limit)
    }
    function pin(signal: Signal) {
        select(signal)
        store.trackingTarget = { ...signal }; store.trackingState = 'acquiring'; store.drift = 0
        pinned = new SignalTracker(signal); pinnedFrequency = store.tuneFreq
    }
    function select(signal: Signal, manual = true) {
        const next = targetTune(signal)
        if (manual) store.releaseTracking()
        if (manual) { store.autoFreq = false; store.autoBw = false }
        store.tune(next.frequency, manual || store.autoBw ? next.bandwidth : store.bandwidth)
        tracked = signal; lastSeen = performance.now(); lastTune = lastSeen
    }
    function accept(analysis: Analysis) {
        const now = performance.now()
        store.signals = analysis.signals; store.noiseDb = analysis.noiseDb
        store.peakDb = analysis.peakDb; store.lastAnalysis = now
        const display = autoDisplay(analysis, store.settings.calibration)
        if (store.autoGain) store.gain += (display.gain - store.gain) * 0.2
        if (store.autoRange) store.range += (display.range - store.range) * 0.2
        if (store.trackingTarget && pinned) {
            const binHz = store.settings.samp_rate / store.fftSize
            const result = pinned.update(analysis.signals, binHz, store.maxDrift)
            store.trackingState = result.state; store.drift = result.drift
            const tolerance = store.afc && store.trackingTarget.narrow ? 2 : Math.max(150, binHz * 2)
            if (result.signal && Math.abs(pinnedFrequency + result.drift - store.tuneFreq) >= tolerance)
                store.tune(pinnedFrequency + result.drift)
            return
        }
        if (!store.autoFreq && !store.autoBw) return
        const candidate = tracked && analysis.signals.find(s => Math.abs(s.peakFreq - tracked!.peakFreq) <
            Math.max(1000, tracked!.high - tracked!.low))
        if (candidate) lastSeen = now
        const chosen = candidate ?? ((!tracked || now - lastSeen > 3000) ? analysis.signals[0] : null)
        if (!chosen || now - lastTune < 1500) return
        const next = targetTune(chosen)
        if (store.autoFreq) {
            // Stable signals don't continually reset the demodulator on bin jitter.
            if (!tracked || Math.abs(next.frequency - store.tuneFreq) > Math.max(150, store.settings.samp_rate / store.fftSize * 2)
                || (store.autoBw && Math.abs(next.bandwidth - store.bandwidth) >= 200))
                store.tune(next.frequency, store.autoBw ? next.bandwidth : store.bandwidth)
        } else if (store.autoBw) {
            const nearby = analysis.signals.find(s => s.high >= store.passband.low && s.low <= store.passband.high)
            if (nearby) {
                const bw = suggestedTune(nearby, store.sideband).bandwidth
                if (Math.abs(bw - store.bandwidth) >= 200) store.setBandwidth(bw)
            }
        }
        tracked = chosen; lastTune = now
    }
    function findStrongest() { if (store.signals[0]) select(store.signals[0]) }
    function autoAll() {
        store.releaseTracking()
        store.autoFreq = true; store.autoBw = true; store.autoGain = true; store.autoRange = true
        tracked = null; lastTune = 0
        if (store.signals[0]) select(store.signals[0], false)
    }
    function reset() {
        store.signals = []; store.noiseDb = null; store.peakDb = null; tracked = null; lastTune = 0
        if (store.trackingTarget) store.trackingState = 'acquiring'
    }
    watch(() => store.autoFreq, value => { tracked = null; lastTune = 0; if (value) store.releaseTracking() })
    watch(() => store.trackingTarget, value => { if (!value) pinned = null })
    return { accept, select, pin, findStrongest, autoAll, reset }
}
