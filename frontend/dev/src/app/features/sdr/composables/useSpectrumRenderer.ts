import { onMounted, onUnmounted, watch, type Ref } from 'vue'
import WaterfallWorker from '../workers/waterfall.worker.ts?worker'
import { useSdrStore } from '../store'
import { drawPlot } from '../core/drawSpectrum'
import { typedWorker, type TypedWorker, type WaterfallCommand, type WaterfallEvent } from '../engine/messages'

export function useSpectrumRenderer(elements: {
    container: Ref<HTMLElement | null>; ruler: Ref<HTMLCanvasElement | null>
    spectrum: Ref<HTMLCanvasElement | null>; waterfall: Ref<HTMLCanvasElement | null>; overlay: Ref<HTMLCanvasElement | null>
}, viewMin: Ref<number>, viewMax: Ref<number>) {
    const store = useSdrStore()
    let worker: TypedWorker<WaterfallCommand, WaterfallEvent> | null = null, observer: ResizeObserver | null = null
    let pending = false, latest: Float32Array | null = null, trace: Float32Array | null = null
    let animation = 0
    const config = () => ({ width: elements.waterfall.value?.width ?? 1,
        viewMin: viewMin.value, viewMax: viewMax.value, rate: store.settings.samp_rate,
        center: store.settings.lo_freq, calibration: store.settings.calibration,
        gain: Math.round(store.gain * 2) / 2, range: Math.round(store.range * 2) / 2,
        gamma: store.gamma, palette: store.palette })
    function draw() {
        if (!elements.ruler.value || !elements.spectrum.value || !elements.overlay.value) return
        drawPlot(elements.ruler.value, elements.spectrum.value, elements.overlay.value, trace, {
            ...config(), frequency: store.tuneFreq, ...store.passband,
            lnb: store.settings.lnb_lo_freq, noise: store.noiseDb, signals: store.signals,
        })
    }
    function scheduleDraw() {
        if (animation || store.frozen) return
        animation = requestAnimationFrame(() => { animation = 0; draw() })
    }
    function setLatestData(data: Float32Array) {
        if (!worker || store.frozen) return
        if (!trace || trace.length !== data.length) trace = data.slice()
        else for (let i = 0; i < data.length; i++)
            trace[i] = trace[i] * store.smoothing + data[i] * (1 - store.smoothing)
        scheduleDraw()
        if (pending) { latest = data; return }
        pending = true; worker.postMessage({ type: 'fft', payload: data }, [data.buffer])
    }
    watch(() => [store.tuneFreq, store.bandwidth, store.sideband, store.signals], scheduleDraw)
    watch(() => Object.values(config()), () => {
        worker?.postMessage({ type: 'config', payload: config() }); scheduleDraw()
    })
    watch(() => [store.fftSize, store.selectedBand], () => { trace = null; latest = null; worker?.postMessage({ type: 'clear' }); scheduleDraw() })
    onMounted(() => {
        worker = typedWorker<WaterfallCommand, WaterfallEvent>(new WaterfallWorker())
        worker.onmessage = event => {
            if (event.data.type === 'fftConsumed') {
                pending = false
                if (latest) { const data = latest; latest = null; setLatestData(data) }
            } else if (event.data.type === 'frame') {
                const bitmap = event.data.bitmap
                if (elements.waterfall.value && !store.frozen) {
                    const canvas = elements.waterfall.value
                    canvas.getContext('2d', { alpha: false })!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
                }
                bitmap.close(); worker?.postMessage({ type: 'ackFrame' })
            }
        }
        function resize() {
            const width = Math.max(1, Math.min(2400, elements.container.value!.clientWidth))
            for (const canvas of [elements.ruler.value, elements.spectrum.value, elements.waterfall.value, elements.overlay.value]) {
                if (canvas) canvas.width = width
            }
            const height = Math.max(1, Math.min(1024, elements.container.value!.clientHeight - 182))
            elements.waterfall.value!.height = height; elements.overlay.value!.height = height
            worker?.postMessage({ type: 'config', payload: config() }); scheduleDraw()
        }
        observer = new ResizeObserver(resize); observer.observe(elements.container.value!); resize()
    })
    onUnmounted(() => {
        observer?.disconnect(); worker?.terminate(); latest = null; trace = null
        cancelAnimationFrame(animation)
    })
    return { setLatestData }
}
