# SDR console

The receiver is organized under `frontend/dev/src/app/features/sdr`: Vue panels in
`components`, lifecycle/interaction code in `composables`, signal/display helpers
in `core`, protocol/Web Audio/WASM integration in `engine`, and dedicated DSP and
waterfall `workers`. `ReceiverConsole.vue` composes the panels; the route loads it
lazily. The shared YAML configuration loader is `app/config.ts`.

## Tuning and signal assist

Click a spectrum/waterfall frequency to tune, drag the waterfall to pan, use the
wheel or zoom buttons to zoom, and Shift + wheel to change bandwidth. The ruler's
passband edges can be dragged. RF input includes the configured LNB offset; IF is
shown separately. USB uses the carrier-to-carrier-plus-BW interval; LSB uses the
carrier-minus-BW-to-carrier interval.

`Find strongest` selects the highest-SNR persistent candidate once and fits its
bandwidth. Candidate buttons do the same for another signal. `Auto frequency`
tracks a region with a 1.5-second tuning interval, bin-jitter tolerance and a
three-second hold before switching away from a missing signal. `Auto bandwidth`
can be used independently for a signal overlapping the current passband. Manual
frequency/BW/sideband adjustments turn off automatic tuning. `Auto all` enables
frequency, bandwidth, display gain and range assistance together.

The worker estimates regions from time-averaged liquid-dsp spectra within the
configured received/view limits. A robust lower-percentile floor, minimum SNR,
three-frame persistence, DC/edge exclusion and bounded region count reject noise
and isolated spikes. Edges are measured relative to each peak to avoid Hann
leakage tails. Candidate lists and estimated SNR update at most four times per
second. These are spectral estimates, not modulation identification or a promise
of intelligible reception. Suppressed SSB carriers are not directly visible;
suggested carriers need fine tuning by ear. Narrow carriers are placed about
700 Hz inside the selected sideband so they are audible.

`Auto display gain` puts the strongest peak near the top of the display;
`Auto range` places the estimated noise floor near the bottom. Manual sliders
turn off their corresponding automatic option. These are local display controls;
Pluto retains its configured hardware AGC. Spectrum labels, peak and noise use
normalized dBFS, removing the configured additive calibration offset for the
readout. They are not absolute dBm or calibrated antenna power measurements.

## Resolution, appearance and energy

FFT size is selectable from 256 to 32,768. The default is 4,096; at 520,834 S/s,
32,768 gives about 15.9 Hz per bin. Frequency resolution improves as FFT size grows,
with a longer observation window and more client processing. C++ rebuilds only
its liquid-dsp FFT plan/Hann/history buffers on a resolution change. Audio DSP
objects keep their state; compiled-WASM checks compare PCM exactly across changes.

Profiles select Eco (2,048 / 5 FPS), Balanced (4,096 / 20 FPS) or Detail
(32,768 / 15 FPS). FFT and FPS can also be selected separately. The trace supports
smoothing, waterfall contrast, freeze and fullscreen. Ten palettes use maintained
[D3 chromatic interpolators](https://d3js.org/d3-scale-chromatic/sequential), including
Viridis, Inferno, Magma, Plasma and Cividis. Licenses are distributed in `/licenses`.

Raw waterfall history is a 256-row ring, capped at 32 MiB at the largest FFT.
Worker canvases stay at most 2,400 × 256 pixels; screen waterfall/overlay canvases
are capped at 2,400 × 1,024. Max pooling preserves narrow subpixel carriers when
rendering a large FFT on a small screen. Zoom/palette/gain/range changes recolor
stored dB rows. Worker message acknowledgements bound outstanding audio, spectra
and image bitmaps. WASM keeps fixed 16 MiB memory and each DSP worker owns one
receiver. Actual browser overhead is additional to these application buffers.

Hidden tabs skip FFT and plotting. With audio off and the default background-pause
option enabled, they also close reception. Returning to the tab reconnects.
Audio playback keeps reception active while hidden. Freeze pauses plotting and
signal assistance, with audio continuing. The console uses a static background.
The server stops/releases capture and requests Pluto sleep after its last viewer
leaves; see [capture lifecycle](capture-lifecycle.md).

## Local tools and verification

Save up to eight frequencies with bandwidth/sideband in this browser. Share
produces a URL containing RF frequency, bandwidth and sideband; reload restores
it. FFT/FPS/palette/volume/background-pause preferences and bookmarks persist
locally. Browser storage is optional and never required to receive. There are
no remote tune/control WebSocket messages.

Bun runs unit checks and a compiler runner using the maintained Vue/Volar APIs.
The normal `vue-tsc` CLI patches Node's loader, which Bun does not use
([upstream issue](https://github.com/vuejs/language-tools/issues/6090)). The runner
checks both TypeScript and Vue templates; an intentional template type error was
verified to fail it. No template shim suppresses checks.

Chromium integration checks actual production assets, signal selection/auto
options, 32K FFT during native audio, freeze/fullscreen/zoom, gain/range overrides,
bookmarks/share reload, hidden-tab pause/wake, volume and mobile widths. Visibility
events are injected to exercise the actual handler; browser scheduling policies
and RF/audio quality still need testing on target client devices and the Pluto.
