# I/Q protocol and C++ receiver ABI

The SDR publishes exactly one complete binary frame per ZeroMQ message. Backend
replicas validate these frames and channelize each active receive band once
using native C++ liquid-dsp. `/iq?band=id` emits the same wire format with the
subband rate, center and resampled count; sequence and epoch remain those of
the source. `/iq?band=full` forwards the validated original frame unchanged,
sharing the same upstream subscription with any active subbands. `/bands` exposes
the full option separately as `full_band`, with ID `"full"`. An omitted selection
still receives the default subband. The route accepts no application messages.
Fine tuning and playback remain local. See [subband geometry and operation](iq-subbands.md).

Full-spectrum admission is bounded per backend by `iq_full_band_max_clients`.
Rejection sends WebSocket application close code **4008** with the reason
`Full spectrum is at capacity`, after the upgrade and without subscribing to
the source. Browsers stop reconnecting until an explicit Connect or band change.
Handshake reservations are released on failure/cancellation as well as ordinary
disconnect; numeric subbands do not consume full-spectrum slots.

## Binary frame, version 1

All multibyte fields are little endian. The 32-byte header is followed by exactly
`sample_count × 2` signed bytes, interleaved I then Q. Python's format string is
`<4sBBHIIdII`; `shared/iq_protocol.py` is the authoritative encoder/validator.

| Offset | Bytes | Field | Requirement |
| --- | --- | --- | --- |
| 0 | 4 | Magic | ASCII WSIQ |
| 4 | 1 | Version | 1 |
| 5 | 1 | Format | 1: signed interleaved I/Q8 |
| 6 | 2 | Header length | 32 |
| 8 | 4 | Sequence | uint32, increments once per frame and wraps |
| 12 | 4 | Sample rate | uint32 Hz, actual stream rate, 48,000–4,000,000 |
| 16 | 8 | Center frequency | finite positive float64 Hz, stream center before LNB offset |
| 24 | 4 | Complex sample count | 1–65,536; source normally 8,192, subband approximately 2,013 |
| 28 | 4 | Source epoch | random uint32 changed on each source process start |

Source quantization computes `round(clamp(component × iq_scale, -1, 1) × 127)`.
Invalid source components become zero and increment diagnostics. Receivers also
accept -128, mapping it to -1. The maximum frame is 131,104 bytes. Payload alone
costs `16 × sample_rate` bits/s. The 520,834 Hz upstream costs 8.33 Mbit/s
once per subscribed backend and per full-spectrum listener; each 128 kHz browser
stream costs 2.05 Mbit/s before frame/TCP/TLS overhead.

The source applies GNU Radio antialias filtering before integer decimation. The
factor is chosen near source/target while requiring an integral resulting rate.
520,834 Hz remains 520,834 Hz; 2 MHz becomes 500 kHz. Hardware-rounded rates and
frequencies are read back with libiio and included in every frame. The rate is
read from the streaming ADC device so FPGA decimation is included, matching the
[GNU Radio IIO source](https://github.com/gnuradio/gnuradio/blob/v3.10.9.2/gr-iio/lib/fmcomms2_source_impl.cc).

An epoch change, rate/center change, or sequence gap resets browser DSP and its
audio schedule. The backend clears old queued frames and rebuilds the native channelizers on
upstream discontinuity.
Each client has a bounded FIFO; overload drops its oldest frame. TCP is reliable,
so slow clients can still incur OS-buffer latency; a send deadline disconnects
clients that stop accepting data. A browser closes/reconnects after five seconds
without valid I/Q, with retry delay capped at five seconds.

## C++ DSP pipeline

`dsp-wasm/src/receiver.cpp` assembles liquid-dsp components: VCO frequency
translation, multistage antialias resampling to 48 kHz, Kaiser bandwidth filter,
USB/LSB suppressed-carrier demodulation, and Hann-windowed FFT. DSP handles use
RAII and process buffers are preallocated. No handwritten FFT, oscillator, FIR,
or resampling algorithm remains in the project.

Tuning specifies the suppressed-carrier frequency. USB passes frequencies from
carrier to carrier + bandwidth; LSB passes carrier - bandwidth to carrier. The
complete passband must fit the I/Q span. The UI overlays that interval. Frequency
controls show RF = stream center/offset + `lnb_lo_freq`, while DSP uses IF.

CW tuning denotes the received carrier itself; its filter is centered on that
frequency with bandwidth/2 on each side. A second liquid-dsp VCO shifts the
filtered carrier to the requested 300–1,200 Hz audio pitch before demodulation.
Optional liquid-dsp audio AGC targets about 0.2 RMS and limits applied boost to
40 dB. Its squelch state monitors pre-gain demodulated level, holds for 200 ms
and drives a library low-pass gate envelope. Threshold units are audio dBFS,
not calibrated RF power. No new DSP dependency or handwritten DSP algorithm is used.

FFT output has negative frequencies on the left, positive frequencies on the
right, and DC at its center. Magnitudes are normalized by Hann coherent gain,
converted to dBFS, then adjusted by `calibration`. The existing waterfall worker
applies display gain/range/palette and produces pixels; the DSP module emits dB
values so no duplicate palette or unused pixel-buffer path is needed.

## Standalone WebAssembly ABI

Build with Emscripten 4.0.15 and CMake ≥3.20. The standalone reactor has a fixed
16 MiB linear memory, a 1 MiB stack, no filesystem or threads, and no generated
runtime JS bundle. Instantiate with the WASI `fd_write` stub in `WasmDsp.ts`, then
call `_initialize()` exactly once before the receiver functions.

| Export | Behavior |
| --- | --- |
| dsp_new(rate, 48000, fft_size, calibration) | Returns nonzero receiver ID or 0 for invalid configuration/capacity. FFT size must be a power of two from 256 to 32,768. |
| dsp_free(id) | Releases all library handles and buffers. |
| dsp_input(id) | Byte address of the writable signed-I/Q input buffer, capacity 65,536 complex samples. |
| dsp_audio(id) | Byte address of float32 PCM produced by the last process call. |
| dsp_spectrum(id) | Byte address of fft_size float32 dB values. |
| dsp_fft_ready(id) | Reports whether the last process call produced an FFT. |
| dsp_set_fft(id, size) | Returns 1 on success. Rebuilds only FFT/window/history buffers; retains oscillator, filter, resampler and demodulator state. Spectrum pointers must be obtained again after resizing. |
| dsp_tune(id, offset_hz, bandwidth_hz, sideband) | Returns 1 on success. Sideband is +1 USB or -1 LSB; bandwidth is 90–15,000 Hz. Resets audio state. |
| dsp_shift(id, offset_hz) | Changes only the translation frequency; retains NCO phase, filters, resampler, modem and audio scheduling. |
| dsp_mode(id, cw, pitch_hz) | Sets CW flag and beat pitch. Call dsp_tune after a mode change to rebuild the appropriate filter; changing only pitch retains audio state. |
| dsp_audio_config(id, agc, squelch, threshold_dbfs) | Sets boolean flags and audio squelch threshold (−100 through 0 dBFS). Settings persist through stream reset. |
| dsp_audio_rssi(id), dsp_squelch_open(id) | Report library level estimate and whether the audio squelch is open. |
| dsp_reset(id) | Clears oscillator/filter/resampler/FFT history after discontinuity. |
| dsp_process(id, count, listen, fft) | Processes 1–65,536 samples. Returns PCM count or -1 for invalid ID/count. Flags select demodulation and an FFT snapshot. |

Output buffers belong to the instance and must be copied before subsequent calls
or destruction. Only those copies are transferred to the UI, preserving WASM
memory. Each worker owns one receiver. There are at most two simultaneous
instances per module. Retuning can allocate library filter/modem objects; the
real-time process function does not allocate new buffers.

liquid-dsp v1.8.3 is fetched by CMake from its release archive with SHA-256
`18fa83b73db8bb6fe6ea0376e4b5aecf8645970f4604d10d9dadbf609f3f95e2`.
Its MIT license is distributed as `/licenses/liquid-dsp.txt` alongside the WASM
and `/app/licenses/liquid-dsp.txt` in the native backend image.
