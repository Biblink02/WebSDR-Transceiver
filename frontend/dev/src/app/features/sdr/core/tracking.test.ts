import { test, expect } from 'bun:test'
import { SignalTracker } from './tracking'
import type { Signal } from './types'
const signal = (frequency: number, snr = 30): Signal => ({ low: frequency - 20, high: frequency + 20,
    peakFreq: frequency, peakDb: -30, snr, narrow: true })

test('pinned tracking follows slow drift, ignores stronger carriers and holds loss', () => {
    const tracker = new SignalTracker(signal(1000))
    for (let step = 1; step <= 20; step++) {
        const result = tracker.update([signal(31000, 80), signal(1000 + step * 5)], 16, 200)
        expect(result.state).toBe('tracking')
        expect(result.signal!.peakFreq).toBe(1000 + step * 5)
    }
    const lost = tracker.update([signal(31000, 80)], 16, 200)
    expect(lost.state).toBe('lost'); expect(lost.signal).toBeNull()
    expect(lost.drift).toBeGreaterThan(80)
    expect(tracker.update([signal(1100)], 16, 200).state).toBe('tracking')
    expect(tracker.update([signal(1250)], 16, 200).state).toBe('lost')
})

test('wide signal tracking uses occupied center instead of a changing voice peak', () => {
    const voice = { ...signal(1000), narrow: false, low: 500, high: 2500 }
    const tracker = new SignalTracker(voice)
    const result = tracker.update([{ ...voice, peakFreq: 2300 }], 16, 500)
    expect(result.drift).toBe(0)
    expect(tracker.update([signal(1500)], 16, 500).state).toBe('lost')
})
