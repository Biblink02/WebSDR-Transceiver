import { paletteColors } from '../core/palettes'
import { maxPool, WaterfallHistory } from '../core/display'
import { clamp } from '../core/types'

const history = new WaterfallHistory()
let canvas = new OffscreenCanvas(1, WaterfallHistory.rows)
let context = canvas.getContext('2d', { alpha: false })!
let colors = paletteColors('viridis')
let config = { width: 1, viewMin: 0, viewMax: 1, rate: 1, center: 0,
    calibration: 0, gain: 0, range: 40, gamma: 0.85, palette: 'viridis' }
let pending = false, dirty = false

function drawRow(age: number, y: number) {
    const row = history.row(age), width = canvas.width
    const first = (config.viewMin - config.center + config.rate / 2) / config.rate * row.length
    const last = (config.viewMax - config.center + config.rate / 2) / config.rate * row.length
    const image = context.createImageData(width, 1)
    const top = config.calibration - config.gain
    for (let x = 0; x < width; x++) {
        const db = maxPool(row, x, width, first, last)
        const level = Math.pow(clamp((db - top + config.range) / config.range, 0, 1), config.gamma)
        const color = Math.round(level * 255) * 4
        const pixel = x * 4
        image.data[pixel] = colors[color]; image.data[pixel + 1] = colors[color + 1]
        image.data[pixel + 2] = colors[color + 2]; image.data[pixel + 3] = 255
    }
    context.putImageData(image, 0, y)
}
function redraw() {
    context.fillStyle = '#060c12'; context.fillRect(0, 0, canvas.width, canvas.height)
    for (let age = 0; age < history.count; age++) drawRow(age, age)
    sendFrame()
}
function sendFrame() {
    if (pending) { dirty = true; return }
    pending = true; dirty = false
    // transferToImageBitmap clears the canvas; createImageBitmap retains scrolling history.
    createImageBitmap(canvas).then(bitmap => {
        self.postMessage({ type: 'frame', bitmap }, { transfer: [bitmap] })
    }).catch(() => { pending = false })
}
self.onmessage = event => {
    const { type, payload } = event.data
    switch (type) {
        case 'config': {
            const old = config
            config = { ...config, ...payload }
            if (old.palette !== config.palette) colors = paletteColors(config.palette)
            const width = clamp(Math.round(config.width), 1, 2400)
            if (width !== canvas.width) {
                canvas = new OffscreenCanvas(width, WaterfallHistory.rows)
                context = canvas.getContext('2d', { alpha: false })!
            }
            if (old.rate !== config.rate || old.center !== config.center) history.clear()
            redraw()
            break
        }
        case 'fft': {
            const changed = history.size !== payload.length
            history.push(payload)
            if (changed) redraw()
            else {
                context.drawImage(canvas, 0, 0, canvas.width, canvas.height - 1,
                    0, 1, canvas.width, canvas.height - 1)
                drawRow(0, 0); sendFrame()
            }
            self.postMessage({ type: 'fftConsumed' })
            break
        }
        case 'clear': history.clear(); redraw(); break
        case 'ackFrame': pending = false; if (dirty) sendFrame(); break
    }
}
export {}
