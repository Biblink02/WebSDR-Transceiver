<script setup lang="ts">
import { useSdrStore } from '../store'
import type { useRecording } from '../composables/useRecording'
const store = useSdrStore()
defineProps<{ recording: ReturnType<typeof useRecording> }>()
</script>
<template>
    <section class="panel recording-panel">
        <div class="section-title">RECORDING <span>THIS BROWSER</span></div>
        <p class="muted fine-print">Record processed audio with tuning metadata. Up to 10 minutes or 32 MiB; independent of volume.</p>
        <div class="button-row">
            <button :class="{ primary: recording.state.active }" :disabled="!recording.state.supported || recording.state.finishing || (!recording.state.active && !store.isListening)"
                @click="recording.toggle">{{ recording.state.active ? 'Stop recording' : 'Start recording' }}</button>
            <span class="muted">{{ Math.floor(recording.state.seconds / 60) }}:{{ String(Math.floor(recording.state.seconds) % 60).padStart(2, '0') }}</span>
        </div>
        <div class="downloads" v-if="recording.state.audioUrl">
            <a :href="recording.state.audioUrl" :download="recording.state.filename + '.' + recording.extension">Download audio</a>
            <a :href="recording.state.metadataUrl" :download="recording.state.filename + '.json'">Download metadata</a>
        </div>
        <p v-if="recording.state.error" role="alert">{{ recording.state.error }}</p>
        <p v-if="!recording.state.supported" class="muted fine-print">Audio recording is unavailable in this browser.</p>
        <details><summary>Keyboard shortcuts</summary><p class="muted fine-print">Space: audio · ←/→: tune · Shift + arrows: 10× step · R: record · B: save frequency · F: freeze. Shortcuts pause while editing controls.</p></details>
    </section>
</template>
<style scoped>
.recording-panel { padding:20px; }.button-row { margin-top:14px; }.downloads { display:flex; gap:18px; margin-top:16px; font-size:12px; }
a { color:var(--accent); text-decoration:underline; } details { margin-top:18px; font-size:11px; color:var(--muted); } summary { cursor:pointer; }
</style>
