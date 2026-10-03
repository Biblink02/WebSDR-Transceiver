import { maxPool } from './display'
import type { Signal } from './types'

export interface PlotSettings {
    viewMin: number; viewMax: number; center: number; rate: number; calibration: number
    gain: number; range: number; frequency: number; low: number; high: number
    lnb: number; noise: number | null; signals: Signal[]
}
export function drawPlot(ruler: HTMLCanvasElement, spectrum: HTMLCanvasElement,
    overlay: HTMLCanvasElement, data: Float32Array | null, settings: PlotSettings) {
    const w = spectrum.width, h = spectrum.height
    const x = (f: number) => (f - settings.viewMin) / (settings.viewMax - settings.viewMin) * w
    const top = settings.calibration - settings.gain
    const y = (db: number) => Math.max(0, Math.min(h, (top - db) / settings.range * h))
    const ctx = spectrum.getContext('2d')!, axis = ruler.getContext('2d')!, grid = overlay.getContext('2d')!
    ctx.fillStyle = '#09121c'; ctx.fillRect(0, 0, w, h)
    axis.fillStyle = '#101e2c'; axis.fillRect(0, 0, w, ruler.height)
    grid.clearRect(0, 0, w, overlay.height)
    ctx.font = axis.font = '11px monospace'
    ctx.fillStyle = '#8395a7'; ctx.strokeStyle = '#1e2e3d'; ctx.lineWidth = 1
    for (let normalized = Math.ceil((top - settings.range - settings.calibration) / 10) * 10;
        normalized <= top - settings.calibration; normalized += 10) {
        const db = normalized + settings.calibration
        ctx.beginPath(); ctx.moveTo(0, y(db)); ctx.lineTo(w, y(db)); ctx.stroke()
        ctx.fillText(normalized.toFixed(0) + ' dBFS', 8, Math.max(12, y(db) - 4))
    }
    const rawStep = (settings.viewMax - settings.viewMin) / Math.max(1, w / 120)
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
    const residual = rawStep / magnitude
    const step = (residual > 5 ? 10 : residual > 2 ? 5 : residual > 1 ? 2 : 1) * magnitude
    axis.textAlign = 'center'; axis.fillStyle = '#adbecd'; grid.strokeStyle = '#ffffff12'
    for (let f = Math.ceil(settings.viewMin / step) * step; f <= settings.viewMax; f += step) {
        axis.fillText(((f + settings.lnb) / 1e6).toFixed(step < 1000 ? 4 : 3), x(f), 21)
        grid.beginPath(); grid.moveTo(x(f), 0); grid.lineTo(x(f), overlay.height); grid.stroke()
    }
    if (settings.noise !== null) {
        ctx.strokeStyle = '#8593a080'; ctx.setLineDash([4, 5]); ctx.beginPath()
        ctx.moveTo(0, y(settings.noise)); ctx.lineTo(w, y(settings.noise)); ctx.stroke(); ctx.setLineDash([])
    }
    if (data?.length) {
        const first = (settings.viewMin - settings.center + settings.rate / 2) / settings.rate * data.length
        const last = (settings.viewMax - settings.center + settings.rate / 2) / settings.rate * data.length
        ctx.beginPath()
        for (let pixel = 0; pixel < w; pixel++) {
            const db = maxPool(data, pixel, w, first, last)
            if (!pixel) ctx.moveTo(pixel, y(db)); else ctx.lineTo(pixel, y(db))
        }
        ctx.strokeStyle = '#66dec7'; ctx.lineWidth = 1.25; ctx.stroke()
        ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath()
        const fill = ctx.createLinearGradient(0, 0, 0, h)
        fill.addColorStop(0, '#66dec72a'); fill.addColorStop(1, '#66dec700')
        ctx.fillStyle = fill; ctx.fill()
    }
    for (const [i, signal] of settings.signals.entries()) {
        const sx = x(signal.peakFreq)
        if (sx < 0 || sx > w) continue
        ctx.fillStyle = '#e9b872'; ctx.beginPath(); ctx.arc(sx, y(signal.peakDb), 3, 0, Math.PI * 2); ctx.fill()
        ctx.fillText(String(i + 1), sx + 5, Math.max(13, y(signal.peakDb) - 5))
    }
    for (const target of [ctx, axis, grid]) {
        const height = target.canvas.height
        target.fillStyle = '#66dec715'; target.fillRect(x(settings.low), 0, x(settings.high) - x(settings.low), height)
        target.fillStyle = '#66dec780'; target.fillRect(x(settings.low), 0, 1, height); target.fillRect(x(settings.high), 0, 1, height)
        target.fillStyle = '#66dec7'; target.fillRect(x(settings.frequency), 0, 1.5, height)
    }
}
