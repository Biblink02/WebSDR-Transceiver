<script setup lang="ts">
import { useSdrStore } from '../store'
import { PALETTES } from '../core/palettes'
import { FFT_SIZES, type PROFILES } from '../core/types'
const store = useSdrStore()
function profile(event: Event) { store.setProfile((event.target as HTMLSelectElement).value as keyof typeof PROFILES) }
</script>
<template>
    <section class="panel display-panel">
        <div class="section-title">DISPLAY <span>CLIENT FFT</span></div>
        <div class="display-fields">
            <label>Profile<select aria-label="Display profile" :value="store.profile" @change="profile">
                <option value="eco">Eco</option><option value="balanced">Balanced</option><option value="detail">Detail</option><option value="custom" disabled>Custom</option>
            </select></label>
            <label>FFT size<select aria-label="FFT size" v-model.number="store.fftSize"><option v-for="size in FFT_SIZES" :key="size" :value="size">{{ size.toLocaleString('en-US') }}</option></select></label>
            <label>Frames/s<select aria-label="Display FPS" v-model.number="store.fps"><option v-for="fps in [5,10,15,20,30]" :key="fps" :value="fps">{{ fps }}</option></select></label>
            <label>Palette<select aria-label="Palette" v-model="store.palette"><option v-for="p in PALETTES" :key="p.value" :value="p.value">{{ p.label }}</option></select></label>
        </div>
        <div class="display-sliders">
            <label>Display gain <span>{{ store.gain.toFixed(1) }} dB</span><input aria-label="Display gain" type="range" v-model.number="store.gain" min="-40" max="120" step="1" @input="store.autoGain = false"/></label>
            <label>Dynamic range <span>{{ store.range.toFixed(1) }} dB</span><input aria-label="Dynamic range" type="range" v-model.number="store.range" min="20" max="100" step="1" @input="store.autoRange = false"/></label>
        </div>
        <details><summary>Appearance & energy</summary>
            <div class="display-sliders">
                <label>Contrast <span>{{ store.gamma.toFixed(2) }}</span><input aria-label="Contrast" type="range" v-model.number="store.gamma" min="0.5" max="1.5" step="0.05"/></label>
                <label>Trace smoothing <span>{{ (store.smoothing * 100).toFixed(0) }}%</span><input aria-label="Trace smoothing" type="range" v-model.number="store.smoothing" min="0" max="0.95" step="0.05"/></label>
            </div>
            <label class="energy-option"><input type="checkbox" v-model="store.pauseHidden"/> Pause background reception when audio is off</label>
            <p class="fine-print muted">Hidden tabs skip FFT drawing. After the last viewer leaves, the server releases capture and requests Pluto sleep. Audio keeps reception active.</p>
        </details>
    </section>
</template>
<style scoped>
.display-panel { padding:20px; }
.display-fields { display:grid; grid-template-columns:1fr 1fr 75px 1fr; gap:12px; margin-top:15px; }
.display-sliders { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:16px; }
.display-sliders span { float:right; color:var(--text); }
details { margin-top:16px; color:var(--muted); font-size:11px; }
summary { cursor:pointer; }
.energy-option { margin:16px 0 10px; display:flex; gap:8px; align-items:center; }
@media(max-width:480px) { .display-fields { grid-template-columns:1fr 1fr; } }
</style>
