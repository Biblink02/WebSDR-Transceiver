import { test, expect } from 'bun:test'
import { parseIqFrame, iqWebSocketUrl } from './IqProtocol'
function frame() {
    const buffer=new ArrayBuffer(32+512)
    const view=new DataView(buffer)
    view.setUint32(0,0x51495357,true);view.setUint8(4,1);view.setUint8(5,1)
    view.setUint16(6,32,true);view.setUint32(8,0xffffffff,true)
    view.setUint32(12,520834,true);view.setFloat64(16,739700000,true)
    view.setUint32(24,256,true);view.setUint32(28,123,true)
    return buffer
}
test('parses source epoch, sequence wrap, and exact sample rate', () => {
    const parsed=parseIqFrame(frame())
    expect(parsed.epoch).toBe(123); expect(parsed.sequence).toBe(0xffffffff)
    expect(parsed.sampleRate).toBe(520834);expect(parsed.samples.length).toBe(512)
})
test('rejects truncated, unsupported, nonfinite and oversized packets', () => {
    expect(()=>parseIqFrame(new ArrayBuffer(16))).toThrow()
    for(const mutate of [
        (v:DataView)=>v.setUint8(4,2),
        (v:DataView)=>v.setFloat64(16,NaN,true),
        (v:DataView)=>v.setUint32(24,65537,true),
        (v:DataView)=>v.setUint32(12,1000,true),
    ]) { const buffer=frame();mutate(new DataView(buffer));expect(()=>parseIqFrame(buffer)).toThrow() }
})
test('uses secure WebSockets for HTTPS and preserves a deployment base path', () => {
    Object.defineProperty(globalThis,'location',{value:{href:'https://receiver.test/sdr'},configurable:true})
    expect(iqWebSocketUrl('https://receiver.test')).toBe('wss://receiver.test/iq')
    expect(iqWebSocketUrl('http://receiver.test/radio/')).toBe('ws://receiver.test/radio/iq')
    expect(iqWebSocketUrl('/')).toBe('wss://receiver.test/iq')
    expect(()=>iqWebSocketUrl('file:///tmp/radio')).toThrow()
})
