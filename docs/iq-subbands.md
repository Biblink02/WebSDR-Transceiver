# Shared native I/Q subbands

This branch defaults to a filtered subband and allows each listener to manually
select the complete capture instead.
The Pluto/GNU Radio source remains a single demand-driven publisher. Each backend
replica subscribes once while it has viewers, runs one native C++ liquid-dsp
channelizer per distinct active subband, then shares that result with all listeners
of the band. Full-spectrum listeners receive the validated source frames directly,
without a channelizer, alongside any active subbands. No backend FFT, demodulation
or audio is introduced. The browser still owns SSB/CW, AGC, squelch, AFC, spectrum
analysis and recording.

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
payload bitrates in `bands`, plus `full_band` with ID `"full"` and the source
center/rate. The full view is clipped to the configured limits and upstream
Nyquist span. It works while idle without subscribing upstream or waking
Pluto. `GET /iq?band=id` opens that band; omitted `band` selects the band nearest
the source center. `GET /iq?band=full` forwards complete source frames, byte for
byte, with the original rate, center and count. Invalid IDs are rejected before
admission. Frames carry the actual band center/rate/count and preserve source
sequence/epoch.

The console selects a receive band and clamps fine tuning to its usable interval.
A manually entered frequency may select another band that contains the complete
passband. **Receive band → Full spectrum** makes the whole configured capture
view available and preserves the current tuning. Fine tuning in that selection
does not return to a subband. The choice is per listener; no capacity/load/user-count
policy changes it automatically. Saved frequencies and share links retain band
selection. Changing band terminates the old DSP worker, stops audio and finalizes recording, clears
tracking/history, and starts a new stream. Audio requires a new Start audio click.
Ordinary fine tuning/AFC continues locally without WebSocket control messages.

## Full-spectrum admission

`iq_full_band_max_clients` in `config/config.yaml` is the maximum number of
concurrent full-spectrum WebSockets on each backend replica. It defaults to 4;
0 disables full-spectrum reception. It must be a nonnegative integer, and
`IQ_FULL_BAND_MAX_CLIENTS` overrides YAML. Changes take effect when the backend
restarts through the existing configuration/reload workflow.

Each tab/connection counts, including while capture warms up or audio is off.
Subband connections do not consume the allowance. A slot is reserved synchronously
before awaiting the WebSocket handshake and released on handshake failure,
cancellation, disconnect or send timeout. Concurrent requests cannot exceed the
configured count. Rejected requests do not subscribe upstream or wake capture.

At capacity, the backend accepts the WebSocket upgrade only to send application
close code 4008 with a capacity reason. The browser shows **FULL SPECTRUM AT
CAPACITY**, stops retrying, and keeps the selected band. Choose a subband to
reconnect, or press Connect to explicitly retry full reception. Existing listeners
are retained, and audio/recording remain stopped after a band change.

The allowance belongs to a backend process, not the whole cluster. With two
replicas and a limit of 4, up to 8 full connections can be admitted in total,
provided they are distributed across replicas; a request to a full replica is
rejected even if another has room. This is a static admission limit, not a CPU or
network capacity measurement. Choose the count for the available link/headroom;
subband traffic and other workloads still consume resources.

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
Full-spectrum listeners share the same bounded queues, send deadlines and
discontinuity handling. A full listener keeps capture awake after the last
subband listener leaves, while the unused native channelizer is freed immediately.
The catalog is recalculated from actual source metadata; configuration changes
should still restart source/backends together.

## Cost and verification

Payload falls from 8.33 Mbit/s at 520,834 Hz to 2.048 Mbit/s at 128 kHz per browser,
a 75.4% reduction before overhead. The internal source-to-backend stream retains
its original rate. Channelizer CPU scales with distinct bands on each replica,
not with listeners sharing a band. Full selection costs 8.33 Mbit/s per browser
and processes all samples in browser WASM, while adding no native channelizer
work. `/stream-info` adds `active_bands`, `full_band_clients`,
`full_band_max_clients` and counters for `full_band_rejected`, `channel_frames`,
`processing_microseconds` and `delivered_bytes`.

The native tests process actual quantized tones, verify frequency translation,
output sample count, edge passband response, rejection of an out-of-band tone,
exact output equality across 1,001/8,192/65,536-sample block sizes, invalid ABI
parameters, band coverage with complete 15 kHz passbands and resource release.
The tested rejected tone is suppressed by more than 47 dB at I/Q8 precision.
Five simultaneously active bands processed 2.013 seconds of I/Q in 0.517 seconds
on this development machine; a concurrent build run took 0.854 seconds. Both met
the real-time budget. These measurements do not estimate production CPU capacity.

Real WebSocket tests cover shared processing, mixed full/subband listeners on one
upstream subscription, exact full-frame forwarding, source epochs, replica
independence, invalid IDs and last-listener cleanup. Chromium checks manual
full/subband changes, full-view tuning without a selection change, recording
finalization, band-aware saved/shared frequencies and actual audio from a carrier
in an overlapping band. Existing drift/CW/AGC/squelch/background/recording tests
also run on the narrower stream. Deployment checks use a dedicated Kind cluster
and synthetic capture through Caddy TLS/WSS.

Admission tests exercise 12 simultaneous requests against a one-slot replica,
independent allowance on a second replica, slot reuse, rejection without source
wake, a paused handshake and cancellation/failure cleanup. Chromium checks the
capacity message, lack of automatic retries, preservation of the existing full
listener's audio, manual subband selection, recording finalization and Connect
retry after a slot is freed.

Channelization starts from already quantized I/Q8 and requantizes filtered output
without automatic gain. Its quantization noise, actual RF coverage (including the
existing 250 kHz hardware RF bandwidth), production CPU/headroom and receiver
sensitivity still require acceptance with the production Pluto. No hardware
settings or production services were changed during these checks.
