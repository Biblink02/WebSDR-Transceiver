<script setup lang="ts">
import { useSdrStore } from '../store'
const store = useSdrStore()
</script>
<template>
    <section class="panel audio-panel">
        <div class="section-title">AUDIO <span>{{ store.squelch ? store.squelchOpen ? 'SQUELCH OPEN' : 'SQUELCH CLOSED' : 'LOCAL DSP' }}</span></div>
        <div class="audio-options">
            <label><input type="checkbox" v-model="store.audioAgc"/> Audio AGC</label>
            <label><input type="checkbox" v-model="store.squelch"/> Squelch</label>
        </div>
        <label class="audio-slider">Squelch threshold <span>{{ store.squelchThreshold }} dBFS</span>
            <input aria-label="Squelch threshold" type="range" min="-100" max="0" v-model.number="store.squelchThreshold" :disabled="!store.squelch"/></label>
        <label v-if="store.mode === 'cw'" class="audio-slider">CW pitch <span>{{ store.cwPitch }} Hz</span>
            <input aria-label="CW pitch" type="range" min="300" max="1200" step="10" v-model.number="store.cwPitch"/></label>
        <p class="muted fine-print">AGC balances received audio. Squelch monitors demodulated audio before gain. Volume stays independent.</p>
    </section>
</template>
<style scoped>
.audio-panel { padding:20px; }
.audio-options { display:flex; gap:24px; margin:18px 0; }
.audio-options label { display:flex; gap:8px; align-items:center; font-size:12px; }
.audio-slider { margin:18px 0; }.audio-slider span { float:right; }
</style>
