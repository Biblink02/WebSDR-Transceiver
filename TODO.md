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
- [x] Delete Redis code/dependencies/manifests, server audio/graphics directories,
  Socket.IO handlers/events/dependencies, allocation state, control sockets,
  legacy UDP listeners, stale worker UI, duplicate players, and unused JS DSP.
- [x] Delete Rust prototype and replace it with library-backed C++.
- [x] Remove legacy settings/manifests/deployment branches and update documentation;
  no dormant compatibility path may remain.
- [x] Fix invalid YAML indentation while preserving user hardware/URL edits.
- [x] Validate loaded configuration and support explicit CONFIG_PATH for local runs.
- [x] Replace all npm commands and package-lock files with Bun and bun.lock.

## 2. Hardware source, packed protocol, and health

- [x] Add a maintained Python GNU Radio flowgraph using the current IIO API.
- [ ] Validate configured Pluto rate, center, RF bandwidth, capture buffer and AGC
  operation on real hardware; the maintained flowgraph implements these settings.
- [x] Filter before hardware-rate integer decimation using GNU Radio FIR components;
  choose an integral resulting rate and advertise the actual stream rate.
- [x] Quantize once at the source: normalized float32 → clipped interleaved signed
  8-bit I/Q. Avoid per-listener conversion work.
- [x] Specify/validate a 32-byte little-endian header: magic/version/format/size,
  sequence, actual rate, center frequency, sample count, and source epoch.
- [x] Preserve bounded packetization history across scheduler buffers; count source
  samples/malformed values/saturated samples/published/dropped frames.
- [x] Use bounded nonblocking ZeroMQ publication. Health must track actual source
  progress and publication using monotonic time, failing after a two-second stall.
- [x] Add startup/readiness/liveness HTTP probes; default recovery restarts SDR only.
- [x] Remove the cascading watchdog and document how to diagnose the reported libiio
  issue with source health and isolated restart/reconnect evidence.
- [x] Test quantization/clipping/header metadata, arbitrary source chunk boundaries,
  filtered rate conversion, malformed inputs, healthy/stalled/resumed health.

## 3. Stateless distributor

- [x] Consume packed frames directly with one ZeroMQ SUB socket per replica;
  perform no audio/FFT DSP or worker allocation in the backend.
- [x] Validate frame size/version/rate/center/count/epoch and bound upstream messages.
- [x] Serve binary `/iq`, `/health`, `/ready`, and `/stream-info` endpoints.
- [x] Bound per-client queues and WebSocket send times; drop oldest queued frames
  for slow clients without delaying others. Expose drops/malformed/client counts.
- [x] Detect upstream discontinuities, reconnect after source restart, discard stale
  queues, and shut down sockets/tasks/clients without leaking resources.
- [x] Proxy ws/wss upgrades through nginx and serve WASM as application/wasm.
- [x] Test real two-client WebSocket delivery, two independent backend replicas,
  slow-client isolation, malformed packets, subscriber cleanup, and source restart.

## 4. C++ WebAssembly receiver using liquid-dsp

- [x] Pin liquid-dsp with FetchContent URL/checksum and preserve license attribution.
- [x] Prove library compiles for both native C++ tests and Emscripten before integration.
- [x] Wrap DSP handles with RAII, validate all boundary values, preallocate buffers,
  and expose a small documented ABI with bounded WASM memory.
- [x] Use library NCO frequency translation, antialias rate conversion, bandwidth
  filtering, and USB/LSB demodulation; preserve state across chunks.
- [x] Produce accurate 48 kHz audio from 520,834 Hz and other supported source rates.
- [x] Use library FFT and Hann window, FFT shift, normalized log-magnitude and
  calibration; feed existing automatic-range/palette renderer.
- [x] Reset state on tuning/stream epoch/sequence gaps and free resources on stop.
- [x] Test tone placement/normalization, USB/LSB rejection, unwanted channels and
  aliases, silence, saturation, invalid values, retuning, packet invariance,
  output-rate accuracy, and bounded memory across repeated construction/reset.
- [x] Execute compiled WASM tests with Bun and benchmark sustained configured-rate
  processing; report measured throughput rather than assuming sufficient speed.

## 5. Browser integration and playback

- [x] DSP worker owns raw WebSocket and C++ WASM instance; no DSP runs on Vue thread.
- [x] Validate binary headers, stream epochs and sequences; reconnect with capped
  backoff and recover from malformed input and unavailable WASM.
- [x] Transfer FFT/audio buffers with bounded outstanding messages; render at 30 FPS.
- [x] Replace server-worker request/status flows with local listen state and local
  tune/BW/USB/LSB messages; send no remote tuning commands.
- [x] Preserve controls, RF/IF conversion, zoom/pan/palettes, connection state, volume,
  and show the selected sideband's actual passband in the waterfall overlay.
- [x] Native AudioBufferSource → GainNode → destination with smooth volume changes;
  bound scheduling latency, recover underruns, and stop/disconnect on cleanup.
- [x] Handle asynchronous audio start/stop races and user-gesture resume errors.
- [x] Reset playback queues on discontinuity; resume audio after transient reconnect.
- [x] Add synthetic multi-tone I/Q source and browser integration tests covering
  rendered FFT, local retuning, USB/LSB, audio lifecycle/volume, reconnect and cleanup.

## 6. Builds, deployment, documentation, and acceptance

- [x] Build WASM before Vite; pin Bun/Emscripten and include generated assets through
  a reproducible Docker build. No root-owned host dependency installs are needed.
- [x] Simplify deployment to SDR/backend/frontend and existing public proxy; remove
  obsolete workloads during an explicitly requested deployment.
- [x] Add meaningful backend/C++/compiled-WASM/browser checks and frozen lockfiles.
- [x] Pass frontend typecheck/production build, Python checks, shell syntax, and
  Kubernetes/nginx validation; fix resulting implementation failures.
- [x] Verify container builds and an isolated Kubernetes rollout with synthetic I/Q,
  healthy probes and recovery after source restart without cascading restarts.
- [x] Document architecture, all config, protocol, ABI, DSP/tuning convention,
  library attribution, build/development/test commands and bandwidth costs in English.
- [ ] Verify actual Pluto reception, browser audio quality, hardware restart recovery,
  public HTTPS/wss and multiple listeners on the target station; record concrete limits.
- [x] Audit every checkbox against authoritative evidence, leaving unverifiable
  hardware/environment acceptance open with precise reasons.

## Verification evidence

Verified on 2026-10-03 on `feat/webassembly`:

- Bun 1.4.2: clean `bun install --frozen-lockfile` succeeded with an unchanged
  lockfile. Final Docker build also installed the cleaned dependency set with
  `--frozen-lockfile`. No npm/npx/yarn/pnpm commands or package-manager lockfiles
  remain. `npm-data`/`npm-letsencrypt` name Nginx Proxy Manager persistent volumes.
- `bun run typecheck`, `bun run build` and `bun run test`: passed; protocol suite
  has three tests and 13 assertions. Vite reports a remaining >500 kB JS chunk
  advisory; it does not fail the build.
- Native C++ `ctest`: passed, including wanted/opposite/out-of-band/alias rejection,
  USB/LSB retuning, positive/negative FFT placement and normalization, silence and
  full-scale input, exact chunk invariance, 48 kHz output from 520,834 Hz and
  boundary rates, and repeated construction/reset/destruction.
- `bun run test:wasm`: two tests, 495 assertions passed. The latest host run
  processed 1,562,502 I/Q samples in 0.257 s (11.66 times real time), produced
  144,000 PCM samples and kept linear memory fixed at 16 MiB. This measures WASM
  in Bun on this host, not browser/device/network capacity.
- Python/backend/browser suite: 10 tests passed. Real ZeroMQ/WebSocket tests
  verify independent backend replicas, multiple listeners, malformed input,
  bounded slow-client queues, epoch recovery and subscriber cleanup.
- Production frontend in Chromium: waterfall pixels, RF/IF tuning, USB/LSB,
  zoom/pan/palettes, native audio and GainNode volume, source restart, manual
  disconnect/reconnect, delayed audio-resume cancellation and resource cleanup,
  and missing-WASM errors passed. No tuning/control frames left the browser.
- GNU Radio vector-flowgraph check: 2 MHz → 500 kHz filtered decimation passed;
  wanted-tone RMS 1.000000 and alias RMS 0.00000013; four valid packed frames.
- All three production container builds passed; GNU Radio/IIO source-image
  imports, nginx configuration, Compose configuration, Python compilation,
  shell syntax and `git diff --check` passed. Liquid-dsp compiled natively and
  through pinned Emscripten 4.0.15 in the frontend image.
- Dedicated Kind cluster `websdr-wasm-check`: production manifests rolled out
  with synthetic I/Q and two backend replicas. nginx WebSocket delivery and
  `application/wasm` passed. A deliberate capture/publication stall triggered
  exactly one source-container restart; both listeners resumed with a new epoch.
  Backend and frontend restart counts remained zero. The temporary cluster was
  deleted; the original `kind-kind` kubeconfig context was unchanged.

Hardware acceptance remains open: the user confirmed that the Pluto is available
only on the production station. A read-only TCP connection from this workspace
to the configured IIO endpoint `192.168.2.1:30431` timed out. No RF reception, hardware
readback, actual libiio failure/recovery or public TLS edge was tested. The
existing station was not deployed to or modified. Synthetic tests prove the
software recovery mechanism, not the hardware fault's root cause.
