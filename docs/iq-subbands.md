# Shared native I/Q subbands

This branch replaces the full-width browser stream with a filtered subband.
The Pluto/GNU Radio source remains a single demand-driven publisher. Each backend
replica subscribes once while it has viewers, runs one native C++ liquid-dsp
channelizer per distinct active band, then shares that result with all listeners
of the band. No backend FFT, demodulation or audio is introduced. The browser
still owns SSB/CW, AGC, squelch, AFC, spectrum analysis and recording.

## Geometry and selection

`iq_subband_rate` defaults to 128,000 Hz and is limited to the upstream rate.
A usable span of 80% excludes the resampler's transition region. Neighboring
centers are at most 62.5% of the output rate apart, with at least 16 kHz overlap
for complete 15 kHz SSB passbands. The plan clips to the configured RF view and
upstream Nyquist span; at the outer capture edges it leaves a 10% output-rate
guard. Plans larger than 16 bands fail configuration validation.

With the current 520,834 Hz capture and 400 kHz RF view, five 128 kHz bands cover
the view. Their centers are 80 kHz apart; usable spans overlap by 22.4 kHz.
`GET /bands` lists numeric IDs, IF centers, sample rates, usable IF bounds and
payload bitrates. It works while idle without subscribing upstream or waking
Pluto. `GET /iq?band=id` opens that band; omitted `band` selects the band nearest
the source center. Invalid IDs are rejected before admission. Frames carry the
actual band center/rate/count and preserve source sequence/epoch.

The console selects a receive band and clamps fine tuning to its usable interval.
A manually entered frequency may select another band that contains the complete
passband. Saved frequencies and share links retain band selection. Changing band
terminates the old DSP worker, stops audio and finalizes recording, clears
tracking/history, and starts a new stream. Audio requires a new Start audio click.
Ordinary fine tuning/AFC continues locally without WebSocket control messages.

## Native implementation and bounds

`dsp-wasm/src/channelizer.cpp` uses liquid-dsp's VCO and multistage antialias
resampler, with 80 dB design attenuation. It reuses input/complex/output buffers;
RAII owns the library objects. It does not implement oscillator/filter/resampler
algorithms itself. The backend binds the narrow C ABI through standard Python
`ctypes`; no extra Python or browser dependency is added.

The required shared library is built in a separate Docker stage, from the same
checksum-pinned liquid-dsp v1.8.3 archive as the browser. The runtime image includes
libstdc++ and the MIT license, without compilers. Missing native code fails startup.
For local Python runs, build the `websdr_channelizer` CMake target and set
`SUBBAND_LIBRARY` to the absolute `.so` path. Tests default to
`dsp-wasm/build-native/libwebsdr_channelizer.so`.

There is at most one channelizer per active band per replica. Its native buffers
use approximately 1.75 MiB plus library state; the catalog bounds instances to 16.
Each listener retains its existing bounded FIFO/send deadline. The final viewer
of a band frees its channelizer. The final viewer of a replica closes its upstream
subscription, preserving capture idle/sleep behavior across replicas. Sequence,
epoch and upstream metadata changes clear backlog and native filter/phase history.
The catalog is recalculated from actual source metadata; configuration changes
should still restart source/backends together.

## Cost and verification

Payload falls from 8.33 Mbit/s at 520,834 Hz to 2.048 Mbit/s at 128 kHz per browser,
a 75.4% reduction before overhead. The internal source-to-backend stream retains
its original rate. Channelizer CPU scales with distinct bands on each replica,
not with listeners sharing a band. `/stream-info` adds `active_bands` and counters
for `channel_frames`, `processing_microseconds` and `delivered_bytes`.

The native tests process actual quantized tones, verify frequency translation,
output sample count, edge passband response, rejection of an out-of-band tone,
exact output equality across 1,001/8,192/65,536-sample block sizes, invalid ABI
parameters, band coverage with complete 15 kHz passbands and resource release.
The tested rejected tone is suppressed by more than 47 dB at I/Q8 precision.
Five simultaneously active bands processed 2.013 seconds of I/Q in 0.517 seconds
on this development machine; a concurrent build run took 0.854 seconds. Both met
the real-time budget. These measurements do not estimate production CPU capacity.

Real WebSocket tests cover shared processing, different bands, replica independence,
invalid IDs and last-listener cleanup. Chromium checks band changes, recording
finalization, band-aware saved/shared frequencies and actual audio from a carrier
in an overlapping band. Existing drift/CW/AGC/squelch/background/recording tests
also run on the narrower stream. Deployment checks use a dedicated Kind cluster
and synthetic capture through Caddy TLS/WSS.

Channelization starts from already quantized I/Q8 and requantizes filtered output
without automatic gain. Its quantization noise, actual RF coverage (including the
existing 250 kHz hardware RF bandwidth), production CPU/headroom and receiver
sensitivity still require acceptance with the production Pluto. No hardware
settings or production services were changed during these checks.
