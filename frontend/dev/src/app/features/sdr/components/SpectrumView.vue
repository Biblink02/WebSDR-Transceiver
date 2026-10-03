<script setup lang="ts">
import { ref } from 'vue'
import { useSdrStore } from '../store'
import { useSpectrumInteraction } from '../composables/useSpectrumInteraction'
import { useSpectrumRenderer } from '../composables/useSpectrumRenderer'
const store = useSdrStore()
const container = ref<HTMLElement | null>(null), ruler = ref<HTMLCanvasElement | null>(null)
const spectrum = ref<HTMLCanvasElement | null>(null), waterfall = ref<HTMLCanvasElement | null>(null)
const overlay = ref<HTMLCanvasElement | null>(null)
const interaction = useSpectrumInteraction(() => container.value)
const { setLatestData } = useSpectrumRenderer({ container, ruler, spectrum, waterfall, overlay },
    interaction.viewMin, interaction.viewMax)
async function fullscreen() { if (document.fullscreenElement) await document.exitFullscreen(); else await container.value?.parentElement?.requestFullscreen() }
defineExpose({ setLatestData })
</script>
<template>
    <section class="spectrum-panel panel">
        <div class="plot-toolbar">
            <span><i aria-hidden="true" class="pi pi-chart-line"/> SPECTRUM <small>{{ (store.settings.samp_rate / store.fftSize).toFixed(1) }} Hz/bin</small></span>
            <div class="button-row">
                <span class="muted">{{ interaction.zoom.value.toFixed(1) }}×</span>
                <button aria-label="Zoom out" @click="interaction.zoomBy(0.8)"><i aria-hidden="true" class="pi pi-search-minus"/></button>
                <button aria-label="Zoom in" @click="interaction.zoomBy(1.25)"><i aria-hidden="true" class="pi pi-search-plus"/></button>
                <button :aria-pressed="store.frozen" @click="store.frozen = !store.frozen">{{ store.frozen ? 'Resume display' : 'Freeze display' }}</button>
                <button @click="interaction.resetView">Reset zoom</button>
                <button aria-label="Fullscreen spectrum" title="Fullscreen spectrum" @click="fullscreen"><i aria-hidden="true" class="pi pi-expand"/></button>
            </div>
        </div>
        <div ref="container" class="plot-canvases" aria-label="Spectrum and waterfall. Click to tune, wheel to zoom, drag waterfall to pan."
             @pointerdown="interaction.onDown" @pointermove="interaction.onMove" @pointerup="interaction.onUp"
             @pointercancel="interaction.onCancel" @wheel="interaction.onWheel">
            <canvas ref="ruler" height="32" class="ruler"/>
            <canvas ref="spectrum" height="150" class="spectrum"/>
            <div class="waterfall-area"><canvas ref="waterfall"/><canvas ref="overlay" class="overlay"/></div>
            <div v-if="!store.isConnected" class="plot-empty">{{ store.statusText }}<small>The receiver wakes when a viewer connects.</small></div>
            <div v-if="store.frozen" class="frozen-badge">DISPLAY FROZEN · AUDIO CONTINUES</div>
        </div>
        <div class="plot-footer"><span>Click to tune · Wheel to zoom · Drag to pan · Shift + wheel for BW</span><span>Newest at top · dBFS</span></div>
    </section>
</template>
<style scoped>
.spectrum-panel { overflow: hidden; }
.plot-toolbar,.plot-footer { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:10px 14px; }
.plot-toolbar { font-size:12px; letter-spacing:.05em; }
.plot-toolbar small { margin-left:10px; color:var(--muted); letter-spacing:0; }
.plot-toolbar .button-row { flex-wrap:wrap; }
.plot-footer { font-size:10px; color:var(--muted); border-top:1px solid var(--line); }
.plot-canvases { position:relative; height:440px; touch-action:none; user-select:none; cursor:crosshair; }
canvas { display:block; width:100%; }
.ruler { height:32px; }
.spectrum { height:150px; }
.waterfall-area { height:calc(100% - 182px); position:relative; }
.waterfall-area canvas { height:100%; }
.overlay { position:absolute; inset:0; }
.plot-empty { position:absolute; inset:32px 0 0; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:10px; background:#09121ce0; color:var(--accent); }
.plot-empty small { color:var(--muted); }
.frozen-badge { position:absolute; right:12px; bottom:12px; background:#152335; color:#e9b872; padding:6px 10px; border-radius:6px; font-size:10px; }
:fullscreen .plot-canvases { height:calc(100vh - 90px); }
@media(max-width:600px) { .plot-canvases { height:370px; } .plot-toolbar small,.plot-footer span:last-child { display:none; } .plot-toolbar { flex-wrap:wrap; } }
</style>
