import {AppConfig} from "@/ConfigService";

let config: AppConfig | null = null;

let maxDb = -20;
let minDb = -100;

let offscreenCanvas: OffscreenCanvas | null = null;
let offscreenCtx: OffscreenCanvasRenderingContext2D | null = null;
let bufferWidth = 0;
let bufferHeight = 0;

const COLOR_MAP = new Uint32Array(256);

let hwMinFreq = 0;
let hwMaxFreq = 0;
let viewMinFreq = 0;
let viewMaxFreq = 0;

function initColorMap() {
    const stops = [
        {pos: 0.00, r: 0, g: 0, b: 0},
        {pos: 0.20, r: 0, g: 0, b: 128},
        {pos: 0.40, r: 0, g: 0, b: 255},
        {pos: 0.60, r: 0, g: 255, b: 255},
        {pos: 0.80, r: 255, g: 255, b: 0},
        {pos: 1.00, r: 255, g: 0, b: 0}
    ];

    for (let i = 0; i < 256; i++) {
        const t = i / 255.0;
        let s1 = stops[0];
        let s2 = stops[stops.length - 1];

        for (let j = 0; j < stops.length - 1; j++) {
            if (t >= stops[j].pos && t <= stops[j + 1].pos) {
                s1 = stops[j];
                s2 = stops[j + 1];
                break;
            }
        }

        const range = s2.pos - s1.pos;
        const localT = (t - s1.pos) / range;
        const r = Math.round(s1.r + (s2.r - s1.r) * localT);
        const g = Math.round(s1.g + (s2.g - s1.g) * localT);
        const b = Math.round(s1.b + (s2.b - s1.b) * localT);

        COLOR_MAP[i] = (255 << 24) | (b << 16) | (g << 8) | r;
    }
}

function resizeBuffer(w: number, h: number) {
    if (bufferWidth === w && bufferHeight === h && offscreenCanvas) return;

    const oldBuffer = offscreenCanvas;

    bufferWidth = w;
    bufferHeight = h;
    offscreenCanvas = new OffscreenCanvas(w, h);
    offscreenCtx = offscreenCanvas.getContext('2d', {
        willReadFrequently: true,
        alpha: false
    }) as OffscreenCanvasRenderingContext2D;

    offscreenCtx.fillStyle = 'black';
    offscreenCtx.fillRect(0, 0, w, h);

    if (oldBuffer) {
        offscreenCtx.drawImage(oldBuffer, 0, 0, w, h);
    }
}

function processFFT(data: Float32Array) {
    if (!offscreenCanvas || !offscreenCtx || !config) return;

    const fftSize = data.length;

    if (fftSize !== bufferWidth) {
        resizeBuffer(fftSize, bufferHeight);
    }

    let peak = -200;
    for (let i = 0; i < fftSize; i += 16) {
        if (data[i] > peak) peak = data[i];
    }

    if (peak > -200 && peak < 100) {
        // Use snake_case keys
        if (peak > maxDb) {
            maxDb += (peak - maxDb) * config.gain_attack;
        } else {
            maxDb -= (maxDb - peak) * config.gain_release;
        }
    }

    // Use snake_case keys
    minDb = maxDb - config.range_db;

    offscreenCtx.drawImage(offscreenCanvas, 0, 0, bufferWidth, bufferHeight - 1, 0, 1, bufferWidth, bufferHeight - 1);

    const imgData = offscreenCtx.createImageData(bufferWidth, 1);
    const pixels = new Uint32Array(imgData.data.buffer);

    for (let i = 0; i < bufferWidth; i++) {
        let db = data[i];
        let norm = (db - minDb) / (maxDb - minDb);
        if (norm < 0) norm = 0;
        else if (norm > 1) norm = 1;

        const idx = (norm * 255) | 0;
        pixels[i] = COLOR_MAP[idx];
    }

    offscreenCtx.putImageData(imgData, 0, 0);
    sendFrame();
}

function sendFrame() {
    if (!offscreenCanvas) return;

    const totalHwSpan = hwMaxFreq - hwMinFreq;
    if (totalHwSpan <= 0) return;

    const ratioStart = (viewMinFreq - hwMinFreq) / totalHwSpan;
    const ratioEnd = (viewMaxFreq - hwMinFreq) / totalHwSpan;

    let sx = Math.floor(ratioStart * bufferWidth);
    let sw = Math.ceil((ratioEnd - ratioStart) * bufferWidth);

    if (sx < 0) sx = 0;
    if (sx + sw > bufferWidth) sw = bufferWidth - sx;
    if (sw <= 0) return;

    createImageBitmap(offscreenCanvas, sx, 0, sw, bufferHeight)
        .then(bitmap => {
            self.postMessage({type: 'frame', bitmap}, [bitmap]);
        })
        .catch(err => console.error("Bitmap error", err));
}

self.onmessage = (e) => {
    const {type, payload} = e.data;

    switch (type) {
        case 'config':
            config = payload;
            break;

        case 'init':
            initColorMap();
            hwMinFreq = payload.hwMinFreq;
            hwMaxFreq = payload.hwMaxFreq;
            viewMinFreq = payload.viewMinFreq;
            viewMaxFreq = payload.viewMaxFreq;
            resizeBuffer(payload.fftSize, payload.height);
            break;

        case 'resize':
            resizeBuffer(bufferWidth, payload.height);
            break;

        case 'view':
            viewMinFreq = payload.viewMin;
            viewMaxFreq = payload.viewMax;
            sendFrame();
            break;

        case 'fft':
            processFFT(payload);
            break;
    }
};

export {};
