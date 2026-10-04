<script setup lang="ts">
import { ref } from 'vue'
import { useSdrStore } from '../store'
const store = useSdrStore(), shareLink = ref('')
const numberValue = (event: Event) => Number((event.target as HTMLInputElement).value)
function share() {
    const url = new URL(location.href)
    url.search = new URLSearchParams({ freq: String(store.tuneFreq + store.settings.lnb_lo_freq),
        bw: String(store.bandwidth), side: store.sideband > 0 ? 'usb' : 'lsb', mode: store.mode, pitch: String(store.cwPitch) }).toString()
    history.replaceState(history.state, '', url)
    shareLink.value = url.href
    navigator.clipboard?.writeText(url.href).catch(() => {})
}
</script>
<template>
    <section class="panel tuning-panel">
        <div class="section-title">TUNING <span>{{ store.mode === 'cw' ? 'CW' : store.sideband > 0 ? 'USB' : 'LSB' }}</span></div>
        <div class="frequency-readout">{{ ((store.tuneFreq + store.settings.lnb_lo_freq) / 1e6).toFixed(6) }}<small>MHz RF</small></div>
        <div class="muted fine-print">IF {{ (store.tuneFreq / 1e6).toFixed(6) }} MHz · BW {{ (store.bandwidth / 1000).toFixed(2) }} kHz</div>
        <div class="tuning-fields">
            <label for="receiver-frequency">RF frequency · Hz
                <input id="receiver-frequency" type="number" :value="store.tuneFreq + store.settings.lnb_lo_freq" :step="store.tuningStep"
                       :min="store.limits.low + store.settings.lnb_lo_freq" :max="store.limits.high + store.settings.lnb_lo_freq"
                       @change="store.manualTune(numberValue($event) - store.settings.lnb_lo_freq)"/>
            </label>
            <label>Sideband<select aria-label="Sideband" :value="store.sideband" :disabled="store.mode === 'cw'"
                @change="store.manualTune(store.tuneFreq, store.bandwidth, numberValue($event) === -1 ? -1 : 1)">
                <option value="1">USB</option><option value="-1">LSB</option></select></label>
            <label for="receiver-bandwidth">Bandwidth · Hz<input id="receiver-bandwidth" type="number" :value="store.bandwidth" step="100"
                :min="store.settings.min_bw_limit" :max="store.settings.max_bw_limit"
                @change="store.manualTune(store.tuneFreq, numberValue($event))"/></label>
        </div>
        <label class="mode-control">Mode<select aria-label="Receiver mode" :value="store.mode" @change="store.setMode(($event.target as HTMLSelectElement).value === 'cw' ? 'cw' : 'ssb')">
            <option value="ssb">SSB</option><option value="cw">CW</option></select></label>
        <div class="button-row tuning-actions">
            <button aria-label="Tune down" @click="store.manualTune(store.tuneFreq - store.tuningStep)"><i aria-hidden="true" class="pi pi-minus"/></button>
            <select class="step-control" aria-label="Tuning step" v-model.number="store.tuningStep"><option :value="10">10 Hz</option><option :value="100">100 Hz</option><option :value="1000">1 kHz</option></select>
            <button aria-label="Tune up" @click="store.manualTune(store.tuneFreq + store.tuningStep)"><i aria-hidden="true" class="pi pi-plus"/></button>
            <button @click="store.saveBookmark"><i aria-hidden="true" class="pi pi-bookmark"/> Save</button>
            <button @click="share"><i aria-hidden="true" class="pi pi-link"/> Share</button>
        </div>
        <input v-if="shareLink" class="share-link" aria-label="Receiver share link" :value="shareLink" readonly @focus="($event.target as HTMLInputElement).select()"/>
    </section>
</template>
<style scoped>
.tuning-panel { padding:20px; }
.frequency-readout { font:600 clamp(21px,2.6vw,32px) monospace; color:var(--accent); letter-spacing:-.055em; margin-top:12px; white-space:nowrap; }
.frequency-readout small { font:10px sans-serif; color:var(--muted); margin-left:10px; letter-spacing:0; }
.tuning-fields { margin-top:18px; display:grid; grid-template-columns:minmax(140px,2fr) 70px minmax(90px,1fr); gap:12px; }
.tuning-actions { margin-top:12px; flex-wrap:wrap; }
.tuning-actions .step-control { width:90px; margin-top:0; flex:0 0 90px; }
.share-link { margin-top:10px; font-size:10px !important; }
.mode-control { margin-top:12px; max-width:160px; }
@media(max-width:500px) { .tuning-fields { grid-template-columns:1fr 1fr; } .tuning-fields label:first-child { grid-column:span 2; } }
</style>
