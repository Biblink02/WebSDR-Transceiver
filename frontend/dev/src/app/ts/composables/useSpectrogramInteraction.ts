import { ref, computed } from 'vue'
import { AppConfig } from '@/ConfigService'

interface Props {
    modelValue: number // Current Frequency
    bandwidth: number
}

interface Emits {
    (e: 'update:modelValue', val: number): void
    (e: 'update:bandwidth', val: number): void
}

export function useSpectrogramInteraction(
    config: AppConfig,
    props: () => Props,
    emit: Emits,
    canvasRef: () => HTMLCanvasElement | null
) {
    // State
    const zoom = ref(1)
    const panHz = ref(0)
    const dragging = ref(false)
    const hoverCursor = ref('default')

    // Constants
    const MIN_BW = 500
    // UPDATED: Use snake_case key from new AppConfig
    const MAX_BW = config.max_bw_limit
    const MIN_ZOOM = 1
    const MAX_ZOOM = 10
    const SELECTOR_HEIGHT = 60

    // Internal Drag State
    let startX = 0
    let startFreq = 0
    let startPan = 0
    let dragMode: 'MOVE' | 'RESIZE_L' | 'RESIZE_R' | 'PAN' | null = null

    // Computed Views
    const viewSpan = computed(() => config.samp_rate / zoom.value)
    const viewMin = computed(() => config.lo_freq + panHz.value - viewSpan.value / 2)
    const viewMax = computed(() => config.lo_freq + panHz.value + viewSpan.value / 2)

    // Math Helpers
    function hzToPx(hz: number, w: number): number {
        const range = viewMax.value - viewMin.value
        return ((hz - viewMin.value) / range) * w
    }

    function pxToHz(px: number, w: number): number {
        const range = viewMax.value - viewMin.value
        return viewMin.value + (px / w) * range
    }

    function clampPan() {
        const maxOffset = (config.samp_rate - viewSpan.value) / 2
        if (panHz.value > maxOffset) panHz.value = maxOffset
        if (panHz.value < -maxOffset) panHz.value = -maxOffset
    }

    function getAdaptiveStep(visibleHz: number, widthPx: number): number {
        const minPxBetweenTicks = 100
        const maxTicks = widthPx / minPxBetweenTicks
        const rawStep = visibleHz / maxTicks
        const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
        const residual = rawStep / magnitude

        if (residual > 5) return 10 * magnitude
        if (residual > 2) return 5 * magnitude
        if (residual > 1) return 2 * magnitude
        return magnitude
    }

    function formatFreq(hz: number): string {
        const trueFreq = hz + config.lnb_lo_freq
        return (trueFreq / 1e6).toFixed(hz % 1000 !== 0 ? 4 : 3)
    }

    // Event Handlers
    function getMouseCoords(e: MouseEvent) {
        const canvas = canvasRef()
        if (!canvas) return { x: 0, y: 0, w: 0 }
        const r = canvas.getBoundingClientRect()
        return {
            x: (e.clientX - r.left) * (canvas.width / r.width),
            y: (e.clientY - r.top) * (canvas.height / r.height),
            w: canvas.width
        }
    }

    function onDown(e: MouseEvent) {
        const { x, y, w } = getMouseCoords(e)
        if (!w) return

        const p = props()
        const cx = hzToPx(p.modelValue, w)
        const hzVisible = viewMax.value - viewMin.value
        const bwPx = (p.bandwidth / hzVisible) * w
        const left = cx - bwPx / 2
        const right = cx + bwPx / 2
        const tol = 12

        dragging.value = true
        startX = x
        startFreq = p.modelValue
        startPan = panHz.value

        if (y <= SELECTOR_HEIGHT) {
            if (Math.abs(x - left) < tol) dragMode = 'RESIZE_L'
            else if (Math.abs(x - right) < tol) dragMode = 'RESIZE_R'
            else dragMode = 'MOVE'
        } else {
            if (zoom.value > 1.01) {
                dragMode = 'PAN'
                hoverCursor.value = "grabbing"
            } else {
                dragging.value = false
            }
        }
    }

    function onMove(e: MouseEvent) {
        const { x, y, w } = getMouseCoords(e)
        if (!w) return

        if (!dragging.value) {
            if (y > SELECTOR_HEIGHT) {
                hoverCursor.value = zoom.value > 1.01 ? "grab" : "default"
                return
            }

            const p = props()
            const cx = hzToPx(p.modelValue, w)
            const hzVisible = viewMax.value - viewMin.value
            const bwPx = (p.bandwidth / hzVisible) * w
            const left = cx - bwPx / 2
            const right = cx + bwPx / 2
            const tol = 12

            if (Math.abs(x - left) < tol || Math.abs(x - right) < tol) hoverCursor.value = "ew-resize"
            else if (x > left && x < right) hoverCursor.value = "move"
            else hoverCursor.value = "crosshair"
            return
        }

        const dx = x - startX
        const hzPerPx = (viewMax.value - viewMin.value) / w

        if (dragMode === 'MOVE') {
            let f = startFreq + dx * hzPerPx

            f = Math.round(f)

            // UPDATED: Use snake_case keys
            const minHw = config.lo_freq - config.samp_rate / 2
            const maxHw = config.lo_freq + config.samp_rate / 2
            f = Math.max(minHw, Math.min(maxHw, f))
            emit("update:modelValue", f)
        }
        else if (dragMode === 'RESIZE_L' || dragMode === 'RESIZE_R') {
            const currentHz = pxToHz(x, w)
            const p = props()

            let bw = Math.round(Math.abs(currentHz - p.modelValue) * 2)

            bw = Math.max(MIN_BW, Math.min(MAX_BW, bw))
            emit("update:bandwidth", bw)
        }
        else if (dragMode === 'PAN') {
            panHz.value = startPan - (dx * hzPerPx)
            clampPan()
        }
    }

    function onUp() {
        dragging.value = false
        dragMode = null
        if (hoverCursor.value === 'grabbing') hoverCursor.value = 'grab'
    }

    function onWheel(e: WheelEvent) {
        e.preventDefault()
        const p = props()

        if (e.shiftKey) {
            let bw = Math.round(p.bandwidth + (e.deltaY > 0 ? -200 : 200))

            bw = Math.max(MIN_BW, Math.min(MAX_BW, bw))
            emit("update:bandwidth", bw)
            return
        }
        const factor = e.deltaY > 0 ? 0.9 : 1.1
        let z = zoom.value * factor
        zoom.value = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, z))
        clampPan()
    }

    return {
        // State
        zoom,
        panHz,
        hoverCursor,
        viewMin,
        viewMax,
        // Methods
        onDown,
        onMove,
        onUp,
        onWheel,
        hzToPx,
        getAdaptiveStep,
        formatFreq
    }
}
