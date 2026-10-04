import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import type { AppConfig, IqSelection } from '&/config'
import { FFT_SIZES, PROFILES, clamp, type Bookmark, type Signal, type ReceiverMode } from './core/types'
import { STATE_LABELS, type ReceiverState } from './engine/messages'
import { PALETTES } from './core/palettes'

export const useSdrStore = defineStore('sdr', () => {
    const config = ref<AppConfig | null>(null)
    const selectedBand = ref<IqSelection>(0)
    const bands = computed(() => settings.value.bands.bands)
    const receiveOptions = computed(() => [settings.value.bands.full_band, ...bands.value])
    const isConnected = ref(false), isListening = ref(false), connectionWanted = ref(true)
    const statusText = ref('CONNECTING...')
    const tuneFreq = ref(0), bandwidth = ref(2700), sideband = ref<1 | -1>(1)
    const mode = ref<ReceiverMode>('ssb'), cwPitch = ref(700), tuningStep = ref(100)
    const audioAgc = ref(true), squelch = ref(false), squelchThreshold = ref(-45)
    const audioRssi = ref(-120), squelchOpen = ref(true)
    const trackingTarget = ref<Signal | null>(null), trackingState = ref<'off' | 'acquiring' | 'tracking' | 'lost'>('off')
    const drift = ref(0), afc = ref(true), maxDrift = ref(2000)
    const connectionState = ref<ReceiverState>('connecting')
    const volume = ref(50), palette = ref('viridis'), fftSize = ref(4096), fps = ref(20)
    const gain = ref(-10), range = ref(40), gamma = ref(0.85), smoothing = ref(0.4)
    const frozen = ref(false), pauseHidden = ref(true)
    const autoFreq = ref(false), autoBw = ref(false), autoGain = ref(true), autoRange = ref(true)
    const signals = ref<Signal[]>([]), noiseDb = ref<number | null>(null), peakDb = ref<number | null>(null)
    const bookmarks = ref<Bookmark[]>([])
    const lastAnalysis = ref(0), frames = ref(0), gaps = ref(0), processingMs = ref(0)
    const passband = computed(() => ({
        low: tuneFreq.value + (mode.value === 'cw' ? -bandwidth.value / 2 : sideband.value < 0 ? -bandwidth.value : 0),
        high: tuneFreq.value + (mode.value === 'cw' ? bandwidth.value / 2 : sideband.value > 0 ? bandwidth.value : 0),
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
        const low = limits.value.low + (mode.value === 'cw' ? bandwidth.value / 2 : side < 0 ? bandwidth.value : 0)
        const high = limits.value.high - (mode.value === 'cw' ? bandwidth.value / 2 : side > 0 ? bandwidth.value : 0)
        tuneFreq.value = clamp(Math.round(frequency), low, high)
    }
    function setFrequency(frequency: number) { tune(frequency) }
    function setBandwidth(bw: number) { tune(tuneFreq.value, bw) }
    function manualTune(frequency: number, bw = bandwidth.value, side = sideband.value) {
        if (!Number.isFinite(frequency) || !Number.isFinite(bw)) return
        const width = clamp(bw, settings.value.min_bw_limit, settings.value.max_bw_limit)
        const low = frequency + (mode.value === 'cw' ? -width / 2 : side < 0 ? -width : 0)
        const high = frequency + (mode.value === 'cw' ? width / 2 : side > 0 ? width : 0)
        const available = bands.value.filter(band => low >= band.low && high <= band.high)
        if (selectedBand.value !== 'full' && !available.some(band => band.id === selectedBand.value) && available.length) {
            const nearest = available.reduce((a, b) => Math.abs(a.center_freq - frequency) < Math.abs(b.center_freq - frequency) ? a : b)
            selectBand(nearest.id, frequency)
        }
        autoFreq.value = false; autoBw.value = false; releaseTracking(); tune(frequency, bw, side)
    }
    function selectBand(id: IqSelection, frequency?: number) {
        const band = receiveOptions.value.find(item => item.id === id)
        if (!band) return
        selectedBand.value = band.id
        settings.value.samp_rate = band.sample_rate; settings.value.lo_freq = band.center_freq
        settings.value.view_limit_min = band.low + settings.value.lnb_lo_freq
        settings.value.view_limit_max = band.high + settings.value.lnb_lo_freq
        autoFreq.value = false; autoBw.value = false; releaseTracking(); signals.value = []; frozen.value = false
        tune(frequency ?? (id === 'full' ? tuneFreq.value : band.center_freq))
    }
    function setMode(next: ReceiverMode) {
        if (mode.value === next) return
        const frequency = tuneFreq.value + sideband.value * cwPitch.value * (next === 'cw' ? 1 : -1)
        mode.value = next; manualTune(frequency, next === 'cw' ? 500 : 2700)
    }
    function releaseTracking() { trackingTarget.value = null; trackingState.value = 'off'; drift.value = 0 }
    function setConnectionState(state: ReceiverState) {
        connectionState.value = state; isConnected.value = state === 'connected'; statusText.value = STATE_LABELS[state]
    }
    function saveBookmark() {
        const item = { frequency: tuneFreq.value, bandwidth: bandwidth.value, side: sideband.value, mode: mode.value, band: selectedBand.value }
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
            if (typeof saved.audioAgc === 'boolean') audioAgc.value = saved.audioAgc
            if (typeof saved.squelch === 'boolean') squelch.value = saved.squelch
            if (Number.isFinite(saved.squelchThreshold)) squelchThreshold.value = clamp(saved.squelchThreshold, -100, 0)
            if (Number.isFinite(saved.cwPitch)) cwPitch.value = clamp(saved.cwPitch, 300, 1200)
            if (Array.isArray(saved.bookmarks)) bookmarks.value = saved.bookmarks.slice(0, 8).filter(
                (b: Bookmark) => b && Number.isFinite(b.frequency) && Number.isFinite(b.bandwidth) &&
                receiveOptions.value.some(band => band.id === b.band && b.frequency >= band.low && b.frequency <= band.high) &&
                b.bandwidth >= loaded.min_bw_limit && b.bandwidth <= loaded.max_bw_limit && (b.side === 1 || b.side === -1) &&
                (b.mode === 'ssb' || b.mode === 'cw'))
        } catch { /* Storage is not required for receiving. */ }
        const query = new URLSearchParams(location.search)
        const requestedBand: IqSelection = query.get('band') === 'full' ? 'full' : Number(query.get('band'))
        selectBand(query.has('band') && receiveOptions.value.some(band => band.id === requestedBand) ? requestedBand : loaded.bands.default)
        if (query.get('mode') === 'cw') mode.value = 'cw'
        if (query.has('pitch') && Number.isFinite(Number(query.get('pitch')))) cwPitch.value = clamp(Number(query.get('pitch')), 300, 1200)
        if (query.has('freq')) manualTune(Number(query.get('freq')) - loaded.lnb_lo_freq,
            query.has('bw') ? Number(query.get('bw')) : bandwidth.value, query.get('side') === 'lsb' ? -1 : 1)
        watch([fftSize, fps, palette, volume, pauseHidden, bookmarks, audioAgc, squelch, squelchThreshold, cwPitch], () => {
            try { localStorage.setItem('websdr-console-v1', JSON.stringify({ fftSize: fftSize.value,
                fps: fps.value, palette: palette.value, volume: volume.value,
                pauseHidden: pauseHidden.value, bookmarks: bookmarks.value, audioAgc: audioAgc.value,
                squelch: squelch.value, squelchThreshold: squelchThreshold.value, cwPitch: cwPitch.value })) } catch { /* Optional storage. */ }
        }, { deep: true })
    }
    return { config, settings, limits, profile, bands, receiveOptions, selectedBand, selectBand, isConnected, isListening, connectionWanted, statusText,
        tuneFreq, bandwidth, sideband, passband, volume, palette, fftSize, fps, gain, range, gamma, smoothing,
        frozen, pauseHidden, autoFreq, autoBw, autoGain, autoRange, signals, noiseDb, peakDb, bookmarks,
        lastAnalysis, frames, gaps, processingMs, init, setConnectionState, setFrequency, setBandwidth,
        mode, cwPitch, tuningStep, audioAgc, squelch, squelchThreshold, audioRssi, squelchOpen,
        trackingTarget, trackingState, drift, afc, maxDrift, connectionState, releaseTracking, setMode,
        tune, manualTune, setProfile, saveBookmark }
})
