<script setup lang="ts">
import { useSdrStore } from '../store'
const store = useSdrStore()
defineEmits(['find-strongest', 'auto-all'])
</script>
<template>
    <section class="panel automation-panel">
        <div class="section-title">SIGNAL ASSIST <span>LOCAL TO YOU</span></div>
        <p class="muted fine-print">Find a signal, fit its passband and keep the display readable.</p>
        <div class="button-row assist-actions">
            <button :disabled="!store.isConnected || !store.signals.length" @click="$emit('find-strongest')"><i aria-hidden="true" class="pi pi-search"/> Find strongest</button>
            <button class="primary" :disabled="!store.isConnected" @click="$emit('auto-all')"><i aria-hidden="true" class="pi pi-sparkles"/> Auto all</button>
        </div>
        <div class="auto-options">
            <label><input type="checkbox" v-model="store.autoFreq"/> Auto frequency</label>
            <label><input type="checkbox" v-model="store.autoBw"/> Auto bandwidth</label>
            <label><input type="checkbox" v-model="store.autoGain"/> Auto display gain</label>
            <label><input type="checkbox" v-model="store.autoRange"/> Auto range</label>
        </div>
        <p class="assist-note">Tracks persistent signals with a hold time. Suggested SSB carriers may need fine tuning by ear. Display gain changes your view.</p>
    </section>
</template>
<style scoped>
.automation-panel { padding:20px; }
.automation-panel p { margin-top:10px; }
.assist-actions { margin-top:14px; }
.auto-options { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:18px; }
.auto-options label { display:flex; align-items:center; gap:8px; color:#c6d5e2; font-size:12px; }
.assist-note { color:var(--muted); font-size:10px; line-height:1.6; }
</style>
