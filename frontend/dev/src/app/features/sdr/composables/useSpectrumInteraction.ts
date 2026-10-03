import { ref, computed, watch } from 'vue'
import { useSdrStore } from '../store'
import { clamp } from '../core/types'

export function useSpectrumInteraction(container: () => HTMLElement | null) {
    const store = useSdrStore()
    const zoom = ref(1), center = ref(store.settings.lo_freq)
    const span = computed(() => (store.limits.high - store.limits.low) / zoom.value)
    const viewMin = computed(() => center.value - span.value / 2)
    const viewMax = computed(() => center.value + span.value / 2)
    const hzToPx = (hz: number, width: number) => (hz - viewMin.value) / span.value * width
    let drag: { x: number; center: number; freq: number; mode: 'pan' | 'tune' | 'bw'; moved: boolean } | null = null
    function clampCenter() { center.value = clamp(center.value,
        store.limits.low + span.value / 2, store.limits.high - span.value / 2) }
    function resetView() { zoom.value = 1; center.value = (store.limits.low + store.limits.high) / 2 }
    function zoomBy(factor: number, anchor = 0.5) {
        const target = viewMin.value + anchor * span.value
        zoom.value = clamp(zoom.value * factor, 1, 64)
        center.value = target + (0.5 - anchor) * span.value; clampCenter()
    }
    function coordinates(event: MouseEvent) {
        const rect = container()!.getBoundingClientRect()
        return { x: event.clientX - rect.left, y: event.clientY - rect.top, width: rect.width }
    }
    function onDown(event: PointerEvent) {
        if (event.button !== 0 || !container()) return
        const p = coordinates(event), low = hzToPx(store.passband.low, p.width), high = hzToPx(store.passband.high, p.width)
        const mode = p.y < 32 && (Math.abs(p.x - low) < 7 || Math.abs(p.x - high) < 7) ? 'bw' :
            p.y < 182 ? 'tune' : 'pan'
        drag = { x: p.x, center: center.value, freq: store.tuneFreq, mode, moved: false }
        container()!.setPointerCapture(event.pointerId)
        if (mode === 'tune') store.manualTune(viewMin.value + p.x / p.width * span.value)
    }
    function onMove(event: PointerEvent) {
        if (!drag || !container()) return
        const p = coordinates(event), dx = p.x - drag.x
        if (Math.abs(dx) > 3) drag.moved = true
        if (drag.mode === 'pan') { center.value = drag.center - dx / p.width * span.value; clampCenter() }
        else if (drag.mode === 'bw') store.manualTune(store.tuneFreq,
            Math.abs(viewMin.value + p.x / p.width * span.value - store.tuneFreq))
        else store.manualTune(viewMin.value + p.x / p.width * span.value)
    }
    function onUp(event: PointerEvent) {
        if (!drag || !container()) return
        if (drag.mode === 'pan' && !drag.moved) {
            const p = coordinates(event)
            store.manualTune(viewMin.value + p.x / p.width * span.value)
        }
        drag = null
        if (container()!.hasPointerCapture(event.pointerId)) container()!.releasePointerCapture(event.pointerId)
    }
    function onWheel(event: WheelEvent) {
        event.preventDefault()
        if (event.shiftKey) { store.autoBw = false; store.setBandwidth(store.bandwidth + (event.deltaY > 0 ? -100 : 100)); return }
        const p = coordinates(event)
        zoomBy(event.deltaY > 0 ? 0.8 : 1.25, p.x / p.width)
    }
    watch(() => [store.settings.samp_rate, store.settings.lo_freq], resetView)
    resetView()
    return { zoom, viewMin, viewMax, hzToPx, resetView, zoomBy, onDown, onMove, onUp, onWheel,
        onCancel: () => { drag = null } }
}
