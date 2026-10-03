# WebSDR browser DSP implementation plan

Audited on 2026-10-03. All work is in English on `feat/webassembly`. Checkboxes
mean verified completion; code presence alone does not prove runtime behavior.

## Scope and decisions

The final architecture is **PlutoSDR → GNU Radio capture/antialias decimation →
packed I/Q over ZeroMQ → bounded WebSocket fanout → C++ WebAssembly in a browser
worker → waterfall and Web Audio**. Frequency, bandwidth, and USB/LSB changes
remain local to each browser. No legacy mode, Redis, Socket.IO, server audio or
graphics workers, or worker-allocation compatibility layer will remain.

C++ is the selected WASM language. Use liquid-dsp for oscillators, resampling,
filter design/filtering, SSB demodulation, and FFT; write only integration code.
Use CMake FetchContent with a pinned release and SHA-256, Emscripten for WASM,
and Bun with a frozen lockfile for all frontend install/build/test commands.

Retain GNU Radio for hardware capture and antialias filtering. Replace generated
GRC runtime code with one maintained Python flowgraph; no GRC compilation step
or generated embedded-Python modules should be needed for deployment.

The existing user configuration contains `samp_rate: 520834`, `lo_freq: 739700000`,
and a public HTTPS URL; preserve these values. Convert noninteger ratios to
48 kHz accurately. A 500 ksps signed 8-bit I/Q stream costs approximately 8 Mbit/s
per listener before overhead; scaling remains bounded by network and client CPU.

## Original TODO audit

| Original item | Baseline evidence | Final disposition |
| --- | --- | --- |
| Redis shared worker state | Three local dictionaries and local listener counts; no Redis implementation | Superseded: remove workers and allocation entirely |
| Replica-safe broadcasts | Local Socket.IO emits from UDP receivers | Replace with one ZeroMQ subscriber and independent fanout per backend replica |
| SDR data-flow probes | No health endpoint/timestamps/probes; watchdog restarts downstream workloads | Add source/publication health and SDR-only restart probes; prove reconnect |
| Audio-worker recovery | GNU Radio SUB sources reconnect but no acceptance evidence | Workers removed; test distributor and browser recovery instead |
| GainNode volume | Active AudioPlayer already uses native GainNode; unused HTTPS player mutates samples | Keep one bounded native player and delete duplicate playback code |
| Keep-latest UDP graphics | One async task per packet, no bounds | UDP removed; bound I/Q client queues and worker-to-UI transfers, throttle FFT to 30 FPS |
| Raw browser I/Q | Hardware publishes float32 I/Q to server workers only | Quantize once at SDR source and publish a versioned binary protocol |
| WASM FFT and SSB | No production WASM; unused JS demodulator resets per packet | Replace with a C++ receiver assembled from liquid-dsp components |
| Frontend workers | Socket decoding and waterfall workers already transfer buffers | Keep waterfall renderer; replace socket worker with WebSocket/WASM DSP worker |
| Reproducible checks | No automated suite or dependency lock; malformed config YAML | Add C++/WASM/backend/browser verification and Bun lockfile |

## 1. Remove obsolete architecture and stabilize configuration

- [x] Create `feat/webassembly` before modifying project files.
- [x] Inspect original TODO and expand it before implementing changes.
- [ ] Delete Redis code/dependencies/manifests, server audio/graphics directories,
  Socket.IO handlers/events/dependencies, allocation state, control sockets,
  legacy UDP listeners, stale worker UI, duplicate players, and unused JS DSP.
- [ ] Delete Rust prototype and replace it with library-backed C++.
- [ ] Remove legacy settings/manifests/deployment branches and update documentation;
  no dormant compatibility path may remain.
- [ ] Fix invalid YAML indentation while preserving user hardware/URL edits.
- [ ] Validate loaded configuration and support explicit CONFIG_PATH for local runs.
- [ ] Replace all npm commands and package-lock files with Bun and bun.lock.

## 2. Hardware source, packed protocol, and health

- [ ] Add a maintained Python GNU Radio flowgraph using the current IIO API.
- [ ] Configure Pluto sample rate, center, RF bandwidth, buffer and gain from YAML.
- [ ] Filter before hardware-rate integer decimation using GNU Radio FIR components;
  choose an integral resulting rate and advertise the actual stream rate.
- [ ] Quantize once at the source: normalized float32 → clipped interleaved signed
  8-bit I/Q. Avoid per-listener conversion work.
- [ ] Specify/validate a 32-byte little-endian header: magic/version/format/size,
  sequence, actual rate, center frequency, sample count, and source epoch.
- [ ] Preserve bounded packetization history across scheduler buffers; count source
  samples/malformed values/saturated samples/published/dropped frames.
- [ ] Use bounded nonblocking ZeroMQ publication. Health must track actual source
  progress and publication using monotonic time, failing after a two-second stall.
- [ ] Add startup/readiness/liveness HTTP probes; default recovery restarts SDR only.
- [ ] Remove the cascading watchdog and document how to diagnose the reported libiio
  issue with source health and isolated restart/reconnect evidence.
- [ ] Test quantization/clipping/header metadata, arbitrary source chunk boundaries,
  filtered rate conversion, malformed inputs, healthy/stalled/resumed health.

## 3. Stateless distributor

- [ ] Consume packed frames directly with one ZeroMQ SUB socket per replica;
  perform no audio/FFT DSP or worker allocation in the backend.
- [ ] Validate frame size/version/rate/center/count/epoch and bound upstream messages.
- [ ] Serve binary `/iq`, `/health`, `/ready`, and `/stream-info` endpoints.
- [ ] Bound per-client queues and WebSocket send times; drop oldest queued frames
  for slow clients without delaying others. Expose drops/malformed/client counts.
- [ ] Detect upstream discontinuities, reconnect after source restart, discard stale
  queues, and shut down sockets/tasks/clients without leaking resources.
- [ ] Proxy ws/wss upgrades through nginx and serve WASM as application/wasm.
- [ ] Test real two-client WebSocket delivery, two independent backend replicas,
  slow-client isolation, malformed packets, subscriber cleanup, and source restart.

## 4. C++ WebAssembly receiver using liquid-dsp

- [ ] Pin liquid-dsp with FetchContent URL/checksum and preserve license attribution.
- [ ] Prove library compiles for both native C++ tests and Emscripten before integration.
- [ ] Wrap DSP handles with RAII, validate all boundary values, preallocate buffers,
  and expose a small documented ABI with bounded WASM memory.
- [ ] Use library NCO frequency translation, antialias rate conversion, bandwidth
  filtering, and USB/LSB demodulation; preserve state across chunks.
- [ ] Produce accurate 48 kHz audio from 520,834 Hz and other supported source rates.
- [ ] Use library FFT and Hann window, FFT shift, normalized log-magnitude and
  calibration; feed existing automatic-range/palette renderer.
- [ ] Reset state on tuning/stream epoch/sequence gaps and free resources on stop.
- [ ] Test tone placement/normalization, USB/LSB rejection, unwanted channels and
  aliases, silence, saturation, invalid values, retuning, packet invariance,
  output-rate accuracy, and bounded memory across repeated construction/reset.
- [ ] Execute compiled WASM tests with Bun and benchmark sustained configured-rate
  processing; report measured throughput rather than assuming sufficient speed.

## 5. Browser integration and playback

- [ ] DSP worker owns raw WebSocket and C++ WASM instance; no DSP runs on Vue thread.
- [ ] Validate binary headers, stream epochs and sequences; reconnect with capped
  backoff and recover from malformed input and unavailable WASM.
- [ ] Transfer FFT/audio buffers with bounded outstanding messages; render at 30 FPS.
- [ ] Replace server-worker request/status flows with local listen state and local
  tune/BW/USB/LSB messages; send no remote tuning commands.
- [ ] Preserve controls, RF/IF conversion, zoom/pan/palettes, connection state, volume,
  and show the selected sideband's actual passband in the waterfall overlay.
- [ ] Native AudioBufferSource → GainNode → destination with smooth volume changes;
  bound scheduling latency, recover underruns, and stop/disconnect on cleanup.
- [ ] Handle asynchronous audio start/stop races and user-gesture resume errors.
- [ ] Reset playback queues on discontinuity; resume audio after transient reconnect.
- [ ] Add synthetic multi-tone I/Q source and browser integration tests covering
  rendered FFT, local retuning, USB/LSB, audio lifecycle/volume, reconnect and cleanup.

## 6. Builds, deployment, documentation, and acceptance

- [ ] Build WASM before Vite; pin Bun/Emscripten and include generated assets through
  a reproducible Docker build. No root-owned host dependency installs are needed.
- [ ] Simplify deployment to SDR/backend/frontend and existing public proxy; remove
  obsolete workloads during an explicitly requested deployment.
- [ ] Add meaningful backend/C++/compiled-WASM/browser checks and frozen lockfiles.
- [ ] Pass frontend typecheck/production build, Python checks, shell syntax, and
  Kubernetes/nginx validation; fix resulting implementation failures.
- [ ] Verify container builds and an isolated Kubernetes rollout with synthetic I/Q,
  healthy probes and recovery after source restart without cascading restarts.
- [ ] Document architecture, all config, protocol, ABI, DSP/tuning convention,
  library attribution, build/development/test commands and bandwidth costs in English.
- [ ] Verify actual Pluto reception, browser audio quality, hardware restart recovery,
  and multiple listeners when hardware is available; record concrete limits.
- [ ] Audit every checkbox against authoritative evidence, leaving unverifiable
  hardware/environment acceptance open with precise reasons.

## Verification evidence

Initial baseline: no automated test suite. Original user edits existed in
config/config.yaml and TODO.md. Branch creation succeeded. Existing deployment
context is kind-kind and must not be changed solely for testing. Use isolated
services/cluster. Emscripten and Bun are being installed under /tmp for local
verification. Previously introduced Redis/Rust/legacy work is being removed in
accordance with the user's final architecture decision.
