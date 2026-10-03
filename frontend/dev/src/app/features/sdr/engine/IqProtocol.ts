export interface IqFrame {
    sequence: number
    sampleRate: number
    centerFreq: number
    count: number
    epoch: number
    samples: Int8Array
}

export function parseIqFrame(buffer: ArrayBuffer): IqFrame {
    if (buffer.byteLength < 32) throw new Error('Truncated I/Q header')
    const view = new DataView(buffer)
    if (view.getUint32(0, true) !== 0x51495357 || view.getUint8(4) !== 1 ||
        view.getUint8(5) !== 1 || view.getUint16(6, true) !== 32)
        throw new Error('Unsupported I/Q protocol')
    const sampleRate = view.getUint32(12, true)
    const centerFreq = view.getFloat64(16, true)
    const count = view.getUint32(24, true)
    if (sampleRate < 48000 || sampleRate > 4000000 || !Number.isFinite(centerFreq) ||
        centerFreq <= 0 || count < 1 || count > 65536 || buffer.byteLength !== 32 + count * 2)
        throw new Error('Invalid I/Q frame metadata or length')
    return { sequence: view.getUint32(8, true), sampleRate, centerFreq, count, epoch: view.getUint32(28, true),
        samples: new Int8Array(buffer, 32) }
}

export function iqWebSocketUrl(base: string): string {
    const url = new URL(base || '/', globalThis.location.href)
    if (!['http:', 'https:', 'ws:', 'wss:'].includes(url.protocol))
        throw new Error('I/Q URL must use HTTP(S) or WS(S)')
    url.protocol = ['https:', 'wss:'].includes(url.protocol) ? 'wss:' : 'ws:'
    url.pathname = `${url.pathname.replace(/\/$/, '')}/iq`
    url.search = ''; url.hash = ''
    return url.href
}
