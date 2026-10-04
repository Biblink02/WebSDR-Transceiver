<script setup lang="ts">
import { useSdrStore } from '../store'
import type { Signal } from '../core/types'
const store = useSdrStore()
defineEmits<{ select: [signal: Signal]; track: [signal: Signal] }>()
</script>
<template>
    <section class="panel signal-panel">
        <div class="section-title">DETECTED SIGNALS <span>{{ store.signals.length }} CANDIDATES</span></div>
        <div class="signal-list" v-if="store.signals.length">
            <div v-for="(signal, index) in store.signals.slice(0,6)" :key="index" class="signal-item">
            <button class="signal-row"
                    :aria-label="'Tune signal ' + (index + 1)" @click="$emit('select', signal)">
                <span class="signal-index">{{ index + 1 }}</span>
                <span class="signal-frequency">{{ ((signal.peakFreq + store.settings.lnb_lo_freq) / 1e6).toFixed(5) }} <small>MHz</small></span>
                <span class="signal-kind">{{ signal.narrow ? 'Narrow' : ((signal.high - signal.low) / 1000).toFixed(1) + ' kHz' }}</span>
                <span class="signal-snr">+{{ signal.snr.toFixed(0) }} dB</span>
            </button>
            <button class="track-button" :aria-label="'Track signal ' + (index + 1)" @click="$emit('track', signal)">Track</button>
            </div>
        </div>
        <p class="signal-empty" v-else>{{ store.isConnected ? 'Searching for persistent signals…' : 'Connect to search the received band.' }}</p>
        <div class="signal-stats">
            <span>Noise <strong>{{ store.noiseDb === null ? '—' : (store.noiseDb - store.settings.calibration).toFixed(0) + ' dBFS' }}</strong></span>
            <span>Peak <strong>{{ store.peakDb === null ? '—' : (store.peakDb - store.settings.calibration).toFixed(0) + ' dBFS' }}</strong></span>
        </div>
        <div v-if="store.trackingTarget" class="tracking-controls">
            <div class="fine-print" role="status">Pinned signal · {{ store.trackingState.toUpperCase() }} · drift {{ store.drift >= 0 ? '+' : '' }}{{ store.drift.toFixed(1) }} Hz</div>
            <label><input type="checkbox" v-model="store.afc" :disabled="!store.trackingTarget.narrow"/> Fine AFC on narrow carrier</label>
            <label>Maximum drift · Hz <input type="number" aria-label="Maximum tracking drift" v-model.number="store.maxDrift" min="100" max="5000" step="100"/></label>
            <button @click="store.releaseTracking">Release tracking</button>
            <p class="muted fine-print">Holds this target on loss. Fine AFC follows a narrow carrier; it does not identify a suppressed voice carrier.</p>
        </div>
    </section>
</template>
<style scoped>
.signal-panel { padding:20px; }
.signal-list { margin:12px 0; }
.signal-item { display:flex; align-items:center; gap:8px; }.track-button { flex-shrink:0; padding:6px !important; font-size:10px !important; }
.signal-row { display:flex; align-items:center; gap:10px; width:100%; border:0 !important; border-bottom:1px solid var(--line) !important; padding:11px 0 !important; background:transparent !important; text-align:left; }
.signal-index { font-size:10px; color:#e9b872; background:#e9b87218; padding:3px 6px; border-radius:4px; }
.signal-frequency { flex:1; font:12px monospace; }
.signal-frequency small,.signal-kind { color:var(--muted); font-size:10px; }
.signal-snr { font:11px monospace; color:var(--accent); }
.signal-empty { padding:30px 0; color:var(--muted); font-size:12px; }
.signal-stats { display:flex; gap:22px; margin-top:15px; font-size:10px; color:var(--muted); }
.signal-stats strong { font:11px monospace; color:var(--text); margin-left:5px; }
.tracking-controls { margin-top:18px; border-top:1px solid var(--line); padding-top:14px; }
.tracking-controls label { display:block; margin:14px 0; }.tracking-controls input[type=number] { max-width:140px; }
</style>
