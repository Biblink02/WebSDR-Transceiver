import { clamp } from './types'

export function maxPool(data: Float32Array, pixel: number, width: number, first: number, last: number) {
    const low = clamp(Math.floor(first + pixel / width * (last - first)), 0, data.length - 1)
    const high = clamp(Math.ceil(first + (pixel + 1) / width * (last - first)), low + 1, data.length)
    let peak = -200
    for (let i = low; i < high; i++) if (Number.isFinite(data[i])) peak = Math.max(peak, data[i])
    return peak
}

// Raw dB history permits recolouring and zooming old rows without growing canvases.
export class WaterfallHistory {
    static readonly rows = 256
    private data = new Float32Array(0)
    private position = 0
    count = 0
    size = 0
    push(spectrum: Float32Array) {
        if (spectrum.length !== this.size) {
            this.size = spectrum.length
            this.data = new Float32Array(this.size * WaterfallHistory.rows)
            this.position = 0; this.count = 0
        }
        this.data.set(spectrum, this.position * this.size)
        this.position = (this.position + 1) % WaterfallHistory.rows
        this.count = Math.min(this.count + 1, WaterfallHistory.rows)
    }
    row(age: number) {
        const index = (this.position - 1 - age + WaterfallHistory.rows) % WaterfallHistory.rows
        return this.data.subarray(index * this.size, (index + 1) * this.size)
    }
    clear() { this.count = 0 }
    get bytes() { return this.data.byteLength }
}
