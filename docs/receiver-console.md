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

FFT size is selectable from 256 to 32,768. The default is 4,096; at 128,000 S/s,
4,096 gives 31.25 Hz/bin and 32,768 gives about 3.9 Hz/bin. Frequency resolution improves as FFT size grows,
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
ordinary signal assistance, with audio continuing. If audio is active and a
pinned target or automatic tuning needs tracking, hidden/frozen views keep
analysis at four FFTs per second and transfer no plot buffers. The console uses a static background.
The server stops/releases capture and requests Pluto sleep after its last viewer
leaves; see [capture lifecycle](capture-lifecycle.md).

## Local tools and verification

Save up to eight frequencies with bandwidth/sideband/mode in this browser. Share
produces a URL containing RF frequency, bandwidth, sideband, mode and CW pitch; reload restores
it. FFT/FPS/palette/volume/background-pause preferences and bookmarks persist
locally. Browser storage is optional and never required to receive. There are
no remote tune/control WebSocket messages.

## Audio, pinned tracking and recording

Audio AGC is independent of display gain and volume. It uses the existing
[liquid-dsp AGC/squelch implementation](https://liquidsdr.org/doc/agc/). Squelch
thresholds refer to demodulated audio before AGC; release has a 200 ms hold and
a smoothed gate. CW mode centers the passband on the actual carrier and uses
the library oscillator to set a 300–1,200 Hz listening pitch, independently of
the selected CW bandwidth. Frequency-only tuning/AFC preserves phase and audio
processing state; mode/BW/sideband changes rebuild audio filters.

Each candidate has a Track button. The pinned tracker chooses the nearest
compatible region within a bounded search gate and total drift limit. On loss,
it holds frequency rather than choosing the strongest remaining signal. Fine
AFC uses sub-bin estimates of a narrow Hann FFT peak. Wide regions use their
occupied center, so changing voice peaks do not become frequency references.
Neither method identifies transmitters or hidden SSB carriers; nearby unresolved
carriers can be ambiguous. Release or manual tuning stops pinned tracking.

Native [MediaStream Recording](https://www.w3.org/TR/mediastream-recording/)
records processed audio before the volume control, with no microphone access
or server upload. The browser negotiates WebM/Opus, Ogg/Opus or M4A; separate
download links provide audio and JSON containing UTC start time, tuning/audio
changes and source gaps. One recording is bounded to 10 minutes, 32 MiB and
4,096 metadata events. Stopping audio finalizes recording; leaving the page
discards it. Download before starting another recording. Unsupported browsers
show the recording control as unavailable while reception remains usable.

Shortcuts outside editable/button controls: Space toggles audio, arrows tune
by the selected step, Shift + arrows multiply it by ten, R toggles recording,
B saves the frequency and F freezes the plot. CW mode is included in bookmarks
and shared links; audio preferences and pitch persist locally.

Worker commands/events are discriminated TypeScript unions, including typed
connection states and session-specific buffer acknowledgements. Switches are
exhaustive. WASM loads are abortable, and obsolete success/failure callbacks
cannot affect a newer session. Fatal worker errors allow an explicit restart.
Compile-time checks reject malformed commands and missing acknowledgement IDs.

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

## Receive bands

Choose **Receive band** to move the visible spectrum to another portion of the
station. The 128 kHz stream has a usable 102.4 kHz span and overlaps its neighbors.
Only the selected span appears in the waterfall and automatic signal search.
Select **Full spectrum** in the same menu to view the entire configured capture
and keep the current frequency. This costs 8.33 Mbit/s per browser at 520,834 Hz,
compared with 2.05 Mbit/s for a subband; the menu displays the full-stream bitrate.
The selection belongs to this listener and remains manual regardless of load.
Band changes reconnect the stream, release pinned tracking, reset zoom/history
and finalize recording by stopping audio. Press Start audio to listen again.

Fine frequency/BW/sideband/CW controls remain local. Entering a frequency outside
the current subband selects a suitable overlapping band when the entire passband
fits; otherwise tuning clamps to the available limits. Shared links and saved
frequencies retain the chosen band, including full spectrum. Fine tuning while
full spectrum is selected keeps that selection. See [subband details](iq-subbands.md).
