import {computed, ref} from 'vue'
import {AppConfig} from '@/ConfigService'
import {calculateDisplayFrequency} from "@/Utils";

interface Props {
    modelValue: number
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
    containerRef: () => HTMLElement | null
) {
    // Limits logic: Use Config values or fallback to hardcoded
    const LIMIT_MIN_RF = config.view_limit_min ?? 10_489_500_000
    const LIMIT_MAX_RF = config.view_limit_max ?? 10_489_900_000;

    // Convert RF limits to IF (Intermediate Frequency)
    const LIMIT_MIN_IF = LIMIT_MIN_RF - config.lnb_lo_freq;
    const LIMIT_MAX_IF = LIMIT_MAX_RF - config.lnb_lo_freq;
    const ALLOWED_SPAN = LIMIT_MAX_IF - LIMIT_MIN_IF;

    // Constants
    const MIN_BW = config.min_bw_limit || 90;
    const MAX_BW = config.max_bw_limit;

    // Dynamic MIN_ZOOM: Ensure we can't zoom out further than the allowed window
    // We add a tiny epsilon to avoid floating point boundary issues
    const MIN_ZOOM = Math.max(1, config.samp_rate / ALLOWED_SPAN);
    const MAX_ZOOM = 10;
    const SELECTOR_HEIGHT = 30;

    // State
    const zoom = ref(MIN_ZOOM)
    const panHz = ref(0)
    const dragging = ref(false)
    const hoverCursor = ref('default')

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
        const halfSpan = viewSpan.value / 2;

        const minPan = LIMIT_MIN_IF - config.lo_freq + halfSpan;
        const maxPan = LIMIT_MAX_IF - config.lo_freq - halfSpan;

        // Use a small epsilon to prevent jitter when minPan is very close to maxPan
        const EPSILON = 1.0;

        if (minPan > maxPan + EPSILON) {
            // View is wider than limits: Center it
            const centerIF = (LIMIT_MIN_IF + LIMIT_MAX_IF) / 2;
            panHz.value = Math.round(centerIF - config.lo_freq);
        } else {
            // Normal clamping
            if (panHz.value < minPan) panHz.value = Math.round(minPan);
            else if (panHz.value > maxPan) panHz.value = Math.round(maxPan);
            else panHz.value = Math.round(panHz.value); // Keep integers
        }
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
        const trueFreq = calculateDisplayFrequency(hz)
        return (trueFreq / 1e6).toFixed(hz % 1000 !== 0 ? 4 : 3)
    }

    // Event Handlers
    function getMouseCoords(e: MouseEvent) {
        const el = containerRef()
        if (!el) return {x: 0, y: 0, w: 0}
        const r = el.getBoundingClientRect()
        return {
            x: (e.clientX - r.left),
            y: (e.clientY - r.top),
            w: el.clientWidth
        }
    }

    function onDown(e: MouseEvent) {
        const {x, y, w} = getMouseCoords(e)
        if (!w) return

        const p = props()
        const cx = hzToPx(p.modelValue, w)
        const hzVisible = viewMax.value - viewMin.value
        const bwPx = (p.bandwidth / hzVisible) * w
        const left = cx - bwPx / 2
        const right = cx + bwPx / 2
        const tol = 10

        dragging.value = true
        startX = x
        startFreq = p.modelValue
        startPan = panHz.value

        if (y <= SELECTOR_HEIGHT) {
            if (Math.abs(x - left) < tol) dragMode = 'RESIZE_L'
            else if (Math.abs(x - right) < tol) dragMode = 'RESIZE_R'
            else dragMode = 'MOVE'
        } else {
            // Only allow panning if zoomed in significantly
            if (zoom.value > MIN_ZOOM + 0.05) {
                dragMode = 'PAN'
                hoverCursor.value = "grabbing"
            } else {
                dragging.value = false
            }
        }
    }

    function onMove(e: MouseEvent) {
        const {x, y, w} = getMouseCoords(e)
        if (!w) return

        if (!dragging.value) {
            if (y > SELECTOR_HEIGHT) {
                hoverCursor.value = zoom.value > MIN_ZOOM + 0.05 ? "grab" : "default"
                return
            }

            const p = props()
            const cx = hzToPx(p.modelValue, w)
            const hzVisible = viewMax.value - viewMin.value
            const bwPx = (p.bandwidth / hzVisible) * w
            const left = cx - bwPx / 2
            const right = cx + bwPx / 2
            const tol = 10

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
            // Clamp frequency tune dragging
            f = Math.max(LIMIT_MIN_IF, Math.min(LIMIT_MAX_IF, f))
            emit("update:modelValue", f)
        } else if (dragMode === 'RESIZE_L' || dragMode === 'RESIZE_R') {
            const currentHz = pxToHz(x, w)
            const p = props()
            let bw = Math.round(Math.abs(currentHz - p.modelValue) * 2)
            bw = Math.max(MIN_BW, Math.min(MAX_BW, bw))
            emit("update:bandwidth", bw)
        } else if (dragMode === 'PAN') {
            // Rounding here prevents jitter during drag
            panHz.value = Math.round(startPan - (dx * hzPerPx))
            clampPan()
        }
    }

    function onUp() {
        dragging.value = false
        dragMode = null

        if (zoom.value > MIN_ZOOM + 0.05 && hoverCursor.value === 'grabbing') {
            hoverCursor.value = 'grab'
        } else if (hoverCursor.value === 'grabbing') {
            hoverCursor.value = 'default'
        }
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

        if (zoom.value <= MIN_ZOOM + 0.05 && hoverCursor.value === 'grab') {
            hoverCursor.value = 'default'
        }
    }

    // Force clamp on init
    clampPan();

    return {
        zoom,
        panHz,
        hoverCursor,
        viewMin,
        viewMax,
        onDown,
        onMove,
        onUp,
        onWheel,
        hzToPx,
        getAdaptiveStep,
        formatFreq
    }
}
