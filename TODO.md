# WebSDR browser DSP implementation plan

## Hardware-free signal and IIO testing (2026-10-04)

- [x] Add deterministic generated USB/LSB speech and smoothly keyed Morse across
  all five bands, using SciPy/eSpeak NG rather than a second receiver DSP implementation.
- [x] Add versioned clean/fading/drift/squelch/QRM/recovery/automatic scenes, bounded
  configuration, seeded chunk-invariant noise and scheduled stalls without backlog bursts.
- [x] Add the official libiio emu backend, pinned commit/archive checksum and an
  unprivileged IIOD image compatible with the existing GNU Radio distribution client.
- [x] Generate a valid minimal Pluto XML/DTD and signed 12-bit I/Q replay; use the
  unchanged production IIO source and GNU Radio throttle only for demo pacing.
- [x] Verify production IIO capture byte for byte over 64 packed frames, repeat
  capture with a new epoch, and check frequency/rate, AGC/RF/tracking/FIR and ENSM attributes.
- [x] Pass 31 Python tests (102.66 s), native CTest, nine Bun tests / 122 assertions,
  six existing compiled-WASM tests / 767 assertions, Vue typechecking and production build.
- [x] Pass the additional generated-signal WASM test / 396 assertions: recovered
  USB/LSB speech correlation 0.9931/0.9967, approximately 5.5 ms filter delay, and
  keyed 700 Hz CW with silent key-up intervals.
- [x] Add persistent synthetic/IIO Kind previews with a dedicated kubeconfig,
  automatically isolated Python `.venv`, pinned PyYAML and local HTTP Caddy.
- [x] Verify all five bands through Caddy in both previews, source idle/wake,
  scheduled synthetic liveness recovery and real network-IIO recovery after emulator
  replacement. Backend/frontend restart counts remain zero; all five listeners resume.
- [x] Verify real browser USB audio and local recording through emulated IIO,
  GNU Radio, Caddy, native subbands and WASM, without browser runtime errors.
- [x] Keep hardware effects/RF acceptance explicit; record commands, station
  frequencies and limitations in [simulation and emulation](docs/simulation.md).
- [x] Commit receiver tools in the parent branch and subbands, signal scenarios,
  IIO integration and demo/docs separately with Conventional Commits, as now requested.

## Receiver tools follow-up

- [x] Add liquid-dsp audio AGC, smoothed squelch and CW with independent pitch.
- [x] Pin a selected signal, hold on loss and compensate bounded drift without
  resetting audio phase/filter/resampling state on frequency-only updates.
- [x] Record native browser audio before volume with downloadable metadata,
  bounded duration/memory/events and cleanup; add keyboard controls.
- [x] Type both worker protocols, connection states and session acknowledgements;
  abort obsolete WASM loads and allow worker-error recovery.
- [x] Verify native DSP, compiled WASM (six tests, 767 assertions), Bun (nine tests,
  122 assertions), Vue templates/typecheck, production build and frontend image.
  The full Python suite passed 18 tests; the final tools browser check passed
  in 17.31 seconds, including drifting/lost/recovered targets, hidden-tab AFC,
  decoded recorded audio at zero volume, metadata, shortcuts and a WASM-load race.
- [x] Commit the verified receiver tools after the user's 2026-10-04 instruction. Pipeline/CI work is excluded.

The subband version is implemented and verified separately on `feat/iq-subbands`,
in the worktree under `.worktrees/iq-subbands`. It derives from these receiver tools
and adds a shared native C++ channelizer, band selection and dedicated tests.
Worktrees preserve the two independent working copies. The subband
suite passed 25 tests and the isolated Caddy/Kind rollout passed with two bands,
source-only restart, idle/wake, long-lived WSS and persisted TLS data.

## SDR console and demand-driven capture follow-up

- [x] Redesign the SDR page with responsive tuning, signal-search, visualization
  and playback panels; organize feature code into smaller components/modules.
- [x] Detect persistent signal regions from averaged spectra, rank candidates,
  and support local auto frequency/BW, auto display gain/range and Auto all.
- [x] Add spectrum trace/markers, more palettes, selectable FFT resolution,
  display smoothing/freeze/FPS profiles, and useful local receiver tools.
- [x] Keep FFT/DSP per browser; verify larger FFTs in compiled WASM without audio
  interruption and bound processing, memory and rendering transfers.
- [x] Subscribe upstream only while a backend has actual WebSocket viewers.
- [x] Use ZeroMQ XPUB demand across replicas to stop/release GNU Radio capture
  and request Pluto sleep after an idle grace; wake on the first viewer.
- [x] Keep idle health/readiness successful and active stall recovery isolated;
  handle warm-up, disconnects, replica crashes and source restart.
- [x] Verify detection/auto controls, browser interactions, capture idle/wake and
  multi-replica recovery with synthetic I/Q; document hardware-only limits.
- [x] Record evidence and create atomic commits using the existing format.
- [x] Replace Proxy Manager and the separate nginx frontend with one Caddy
  frontend, versioned configuration, persistent TLS storage and isolated HTTPS/WSS
  checks; keep production activation separate from local verification.

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
and a public HTTPS hostname; preserve these values. The hostname now lives in
`config/Caddyfile`, and `ws_url: /` follows the page's origin. Convert noninteger ratios to
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
- [x] Proxy ws/wss upgrades through Caddy and serve WASM as application/wasm.
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
- [x] Simplify deployment to SDR/backend/Caddy frontend; remove
  obsolete workloads during an explicitly requested deployment.
- [x] Add meaningful backend/C++/compiled-WASM/browser checks and frozen lockfiles.
- [x] Pass frontend typecheck/production build, Python checks, shell syntax, and
  Kubernetes/Caddy validation; fix resulting implementation failures.
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
  remain. Old Proxy Manager volume data is preserved but no longer referenced.
- `bun run typecheck`, `bun run build` and `bun run test`: passed. Seven protocol,
  signal-analysis, rendering-buffer and palette tests contain 75 assertions.
  The Vue/Volar compiler runner checks templates under Bun; an intentional
  template type error was verified to fail it. The SDR route is lazy-loaded;
  the final Vite build has no >500 kB JS chunk advisory.
- Native C++ `ctest`: passed, including wanted/opposite/out-of-band/alias rejection,
  USB/LSB retuning, positive/negative FFT placement and normalization, silence and
  full-scale input, exact chunk invariance, 48 kHz output from 520,834 Hz and
  boundary rates, and repeated construction/reset/destruction.
- `bun run test:wasm`: four tests, 653 assertions passed. The 32K FFT host run
  processed 1,562,502 I/Q samples in 0.796 s (3.77 times real time under concurrent
  test/build load), produced 144,000 PCM samples and kept linear memory fixed at
  16 MiB. Repeated resolution changes preserve PCM exactly; every FFT size from
  256 through 32,768 preserves tone placement and Hann normalization. Two maximum
  receivers fit the heap; a third is rejected. This measures WASM in Bun on this
  host, not browser/device/network capacity.
- Python/backend/browser suite: 17 tests passed. Real ZeroMQ/WebSocket tests
  verify independent backend replicas, multiple listeners, malformed input,
  bounded slow-client queues, epoch recovery and subscriber cleanup.
- Demand lifecycle tests verify first/last viewer handling, grace cancellation,
  healthy idle state, bounded warm-up, source stalls, fresh epochs on wake and
  abrupt backend-process death. One surviving subscriber keeps capture active;
  zero subscribers stop sample publication. Device power is simulated/mocked.
- Production frontend in Chromium: waterfall pixels, RF/IF tuning, USB/LSB,
  zoom/pan/palettes, native audio and GainNode volume, source restart, manual
  disconnect/reconnect, delayed audio-resume cancellation and resource cleanup,
  and missing-WASM errors passed. No tuning/control frames left the browser.
  The new console also passed strongest-signal selection, automatic controls,
  32K FFT during continuous audio, freeze/fullscreen, manual gain/range overrides,
  bookmarks/share reload, preference persistence and mobile widths 390/450/768.
  Injected visibility events kept audio reception active while hidden and stopped
  idle reception when audio was off, then woke capture on return. The latest two
  browser checks passed in 25.16 s; the strengthened waterfall contrast check
  passed separately in 11.42 s and requires signal pixels to differ from the floor.
- GNU Radio vector-flowgraph check: 2 MHz → 500 kHz filtered decimation passed;
  wanted-tone RMS 1.000000 and alias RMS 0.00000013; four valid packed frames.
- All three production container builds passed; GNU Radio/IIO source-image
  imports, Caddy configuration, Compose configuration, Python compilation,
  shell syntax and `git diff --check` passed. Liquid-dsp compiled natively and
  through pinned Emscripten 4.0.15 in the frontend image.
- Dedicated Kind cluster `websdr-wasm-check`: production manifests rolled out
  with synthetic I/Q and two backend replicas. Caddy HTTP-to-HTTPS redirect,
  certificate validation against its actual local root CA, SPA share-link routes,
  WASM MIME/configuration/license serving and two WSS listeners for more than
  65 seconds passed. A deliberate capture/publication stall triggered exactly one
  source-container restart; both listeners resumed with a new epoch. Backend and
  frontend restart counts remained zero during source recovery. Idle publication
  stopped after the final viewer and a new viewer woke a fresh stream. Caddyfile
  validation/reload through stdin passed; an explicit frontend pod replacement
  preserved the original CA and resumed trusted HTTPS/WSS. The temporary cluster
  was deleted; the original `kind-kind` kubeconfig context was unchanged.
- Atomic Conventional Commits separate capture lifecycle, C++ FFT resizing,
  modular console/automation, waterfall verification, Caddy deployment and
  documentation. No production deployment was performed; no legacy mode remains.

Hardware acceptance remains open: the user confirmed that the Pluto is available
only on the production station. A read-only TCP connection from this workspace
to the configured IIO endpoint `192.168.2.1:30431` timed out. No RF reception, hardware
readback, actual libiio failure/recovery or public TLS edge was tested. The
existing station was not deployed to or modified. Actual AD9361 sleep/wake and
power consumption, hardware buffer release and reception after waking remain
hardware acceptance checks. Synthetic tests prove the software recovery mechanism,
not the hardware fault's root cause.
