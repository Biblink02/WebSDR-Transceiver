import { test, expect } from 'bun:test'
import { SpectrumAnalyzer, autoDisplay } from './analysis'
import { suggestedTune } from './types'
import { maxPool, WaterfallHistory } from './display'
import { PALETTES, paletteColors } from './palettes'

function analyze(spectrum: Float32Array, low?: number, high?: number) {
    const analyzer = new SpectrumAnalyzer()
    expect(analyzer.update(spectrum, spectrum.length * 10, 1000000, 0, low, high)).toBeNull()
    expect(analyzer.update(spectrum, spectrum.length * 10, 1000000, 100, low, high)).toBeNull()
    return analyzer.update(spectrum, spectrum.length * 10, 1000000, 500, low, high)!
}
test('persistent narrow and occupied bands are ranked; noise, DC, edges and spikes do not tune', () => {
    const fft = new Float32Array(4096).fill(-100)
    fft[2148] = -25; fft[2348] = -40
    fft[2048] = -2; fft[0] = -1
    for (let i = 2500; i <= 2700; i++) fft[i] = -50 + Math.sin(i)
    const result = analyze(fft)
    expect(result.signals).toHaveLength(3)
    expect(result.signals[0].peakFreq).toBe(1001000)
    expect(result.signals[0].narrow).toBe(true)
    const voice = result.signals.find(s => !s.narrow)!
    expect(voice.high - voice.low).toBe(2000)
    expect(suggestedTune(voice, 1)).toEqual({ frequency: voice.low - 200, bandwidth: 2400 })
    expect(suggestedTune(voice, -1)).toEqual({ frequency: voice.high + 200, bandwidth: 2400 })
    expect(suggestedTune(result.signals[0], 1)).toEqual({ frequency: 1000300, bandwidth: 1800 })
    expect(analyze(fft, 1002500, 1007000).signals.some(s => s.peakFreq === 1001000)).toBe(false)
    const noise = new Float32Array(4096).fill(-100)
    expect(analyze(noise).signals).toHaveLength(0)
    const analyzer = new SpectrumAnalyzer()
    const spike = noise.slice(); spike[2148] = -20
    analyzer.update(spike, 40960, 1000000, 0)
    analyzer.update(noise, 40960, 1000000, 100)
    expect(analyzer.update(noise, 40960, 1000000, 500)!.signals).toHaveLength(0)
    noise[100] = NaN; noise[101] = Infinity
    expect(analyze(noise).noiseDb).toBe(-100)
})
test('FFT changes reset detection; display limits remain finite and bounded', () => {
    const analyzer = new SpectrumAnalyzer()
    const first = new Float32Array(4096).fill(-100); first[2148] = -10
    for (let i = 0; i < 4; i++) analyzer.update(first, 520834, 739700000, i * 500)
    expect(analyzer.update(new Float32Array(32768).fill(-100), 520834, 739700000, 2500)).toBeNull()
    const display = autoDisplay({ signals: [], noiseDb: -190, peakDb: -82 }, -72)
    expect(display.gain).toBe(4); expect(display.range).toBe(100)
    expect(autoDisplay({ signals: [], noiseDb: -100, peakDb: -100 }, 0).range).toBe(20)
})
test('max pooling preserves subpixel carriers and waterfall storage is bounded at 32K', () => {
    const history = new WaterfallHistory()
    const fft = new Float32Array(32768).fill(-150); fft[12345] = -20
    const pixel = Math.floor(12345 / 32768 * 1000)
    expect(maxPool(fft, pixel, 1000, 0, 32768)).toBe(-20)
    for (let i = 0; i < 300; i++) { fft[0] = i; history.push(fft) }
    expect(history.count).toBe(256); expect(history.bytes).toBe(32 * 1048576)
    expect(history.row(0)[0]).toBe(299); expect(history.row(255)[0]).toBe(44)
    history.clear(); expect(history.count).toBe(0)
    history.push(new Float32Array(2048)); expect(history.count).toBe(1)
    expect(history.bytes).toBe(2048 * 256 * 4)
})
test('all palettes provide opaque bounded color tables and distinct endpoints', () => {
    expect(PALETTES.length).toBe(10)
    for (const palette of PALETTES) {
        const bytes = paletteColors(palette.value)
        expect(bytes).toHaveLength(1024)
        expect(Array.from(bytes).filter((_, i) => i % 4 === 3).every(a => a === 255)).toBe(true)
        expect(Array.from(bytes.slice(0, 3))).not.toEqual(Array.from(bytes.slice(1020, 1023)))
    }
})
