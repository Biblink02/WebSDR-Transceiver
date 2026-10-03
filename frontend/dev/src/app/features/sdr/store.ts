import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import type { AppConfig } from '&/config'
import { FFT_SIZES, PROFILES, clamp, type Bookmark, type Signal } from './core/types'
import { PALETTES } from './core/palettes'

export const useSdrStore = defineStore('sdr', () => {
    const config = ref<AppConfig | null>(null)
    const isConnected = ref(false), isListening = ref(false), connectionWanted = ref(true)
    const statusText = ref('CONNECTING...')
    const tuneFreq = ref(0), bandwidth = ref(2700), sideband = ref<1 | -1>(1)
    const volume = ref(50), palette = ref('viridis'), fftSize = ref(4096), fps = ref(20)
    const gain = ref(-10), range = ref(40), gamma = ref(0.85), smoothing = ref(0.4)
    const frozen = ref(false), pauseHidden = ref(true)
    const autoFreq = ref(false), autoBw = ref(false), autoGain = ref(true), autoRange = ref(true)
    const signals = ref<Signal[]>([]), noiseDb = ref<number | null>(null), peakDb = ref<number | null>(null)
    const bookmarks = ref<Bookmark[]>([])
    const lastAnalysis = ref(0), frames = ref(0), gaps = ref(0), processingMs = ref(0)
    const passband = computed(() => ({
        low: tuneFreq.value + (sideband.value < 0 ? -bandwidth.value : 0),
        high: tuneFreq.value + (sideband.value > 0 ? bandwidth.value : 0),
    }))
    const settings = computed(() => {
        if (!config.value) throw new Error('SDR configuration is not loaded')
        return config.value
    })
    const limits = computed(() => ({
        low: Math.max(settings.value.lo_freq - settings.value.samp_rate / 2,
            settings.value.view_limit_min - settings.value.lnb_lo_freq),
        high: Math.min(settings.value.lo_freq + settings.value.samp_rate / 2,
            settings.value.view_limit_max - settings.value.lnb_lo_freq),
    }))
    const profile = computed(() => Object.entries(PROFILES).find(([, p]) =>
        p.fftSize === fftSize.value && p.fps === fps.value)?.[0] ?? 'custom')
    function setProfile(name: keyof typeof PROFILES) {
        fftSize.value = PROFILES[name].fftSize; fps.value = PROFILES[name].fps
    }
    function tune(frequency: number, bw = bandwidth.value, side: 1 | -1 = sideband.value) {
        if (!Number.isFinite(frequency) || !Number.isFinite(bw)) return
        bandwidth.value = clamp(Math.round(bw), settings.value.min_bw_limit, settings.value.max_bw_limit)
        sideband.value = side
        const low = limits.value.low + (side < 0 ? bandwidth.value : 0)
        const high = limits.value.high - (side > 0 ? bandwidth.value : 0)
        tuneFreq.value = clamp(Math.round(frequency), low, high)
    }
    function setFrequency(frequency: number) { tune(frequency) }
    function setBandwidth(bw: number) { tune(tuneFreq.value, bw) }
    function manualTune(frequency: number, bw = bandwidth.value, side = sideband.value) {
        autoFreq.value = false; autoBw.value = false; tune(frequency, bw, side)
    }
    function setConnectionStatus(connected: boolean, text: string) {
        isConnected.value = connected; statusText.value = text
    }
    function saveBookmark() {
        const item = { frequency: tuneFreq.value, bandwidth: bandwidth.value, side: sideband.value }
        bookmarks.value = [item, ...bookmarks.value.filter(b => b.frequency !== item.frequency)].slice(0, 8)
    }
    function init(loaded: AppConfig) {
        config.value = loaded; tuneFreq.value = loaded.lo_freq; bandwidth.value = loaded.bandwidth
        gain.value = loaded.gain_db; range.value = loaded.range_db; fftSize.value = loaded.fft_size
        // Settings are local, bounded, and optional when storage is unavailable.
        try {
            const saved = JSON.parse(localStorage.getItem('websdr-console-v1') ?? '{}')
            if (FFT_SIZES.includes(saved.fftSize)) fftSize.value = saved.fftSize
            if ([5, 10, 15, 20, 30].includes(saved.fps)) fps.value = saved.fps
            if (PALETTES.some(p => p.value === saved.palette)) palette.value = saved.palette
            if (Number.isFinite(saved.volume)) volume.value = clamp(saved.volume, 0, 100)
            if (typeof saved.pauseHidden === 'boolean') pauseHidden.value = saved.pauseHidden
            if (Array.isArray(saved.bookmarks)) bookmarks.value = saved.bookmarks.slice(0, 8).filter(
                (b: Bookmark) => b && Number.isFinite(b.frequency) && Number.isFinite(b.bandwidth) &&
                b.frequency >= limits.value.low && b.frequency <= limits.value.high &&
                b.bandwidth >= loaded.min_bw_limit && b.bandwidth <= loaded.max_bw_limit && (b.side === 1 || b.side === -1))
        } catch { /* Storage is not required for receiving. */ }
        const query = new URLSearchParams(location.search)
        if (query.has('freq')) tune(Number(query.get('freq')) - loaded.lnb_lo_freq,
            query.has('bw') ? Number(query.get('bw')) : bandwidth.value, query.get('side') === 'lsb' ? -1 : 1)
        watch([fftSize, fps, palette, volume, pauseHidden, bookmarks], () => {
            try { localStorage.setItem('websdr-console-v1', JSON.stringify({ fftSize: fftSize.value,
                fps: fps.value, palette: palette.value, volume: volume.value,
                pauseHidden: pauseHidden.value, bookmarks: bookmarks.value })) } catch { /* Optional storage. */ }
        }, { deep: true })
    }
    return { config, settings, limits, profile, isConnected, isListening, connectionWanted, statusText,
        tuneFreq, bandwidth, sideband, passband, volume, palette, fftSize, fps, gain, range, gamma, smoothing,
        frozen, pauseHidden, autoFreq, autoBw, autoGain, autoRange, signals, noiseDb, peakDb, bookmarks,
        lastAnalysis, frames, gaps, processingMs, init, setConnectionStatus, setFrequency, setBandwidth,
        tune, manualTune, setProfile, saveBookmark }
})
