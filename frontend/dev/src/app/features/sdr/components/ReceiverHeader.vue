<script setup lang="ts">
import { useSdrStore } from '../store'
const store = useSdrStore()
defineEmits(['toggle-audio', 'toggle-connection'])
</script>
<template>
    <header class="receiver-header panel">
        <div>
            <div class="eyebrow">LIVE RADIO · YOUR OWN RECEIVER</div>
            <h1>SDR console<span class="status-dot" :class="{ online: store.isConnected }"/></h1>
            <div class="connection-status" role="status">{{ store.statusText }}<span v-if="store.isListening"> · AUDIO ACTIVE</span></div>
        </div>
        <div class="playback">
            <label class="volume-control">Volume <input type="range" aria-label="Volume" v-model.number="store.volume" min="0" max="100"/></label>
            <div class="button-row">
                <button :aria-label="store.connectionWanted ? 'Disconnect' : 'Connect'" @click="$emit('toggle-connection')">
                    <i aria-hidden="true" :class="store.connectionWanted ? 'pi pi-power-off' : 'pi pi-refresh'"/>
                    {{ store.connectionWanted ? 'Disconnect' : 'Connect' }}
                </button>
                <button class="primary" :disabled="!store.isConnected" @click="$emit('toggle-audio')">
                    <i aria-hidden="true" :class="store.isListening ? 'pi pi-stop' : 'pi pi-play'"/>
                    {{ store.isListening ? 'STOP AUDIO' : 'START AUDIO' }}
                </button>
            </div>
        </div>
    </header>
</template>
<style scoped>
.receiver-header { padding:20px 24px; display:flex; justify-content:space-between; align-items:center; gap:20px; }
h1 { font-size:28px; font-weight:650; margin:4px 0; letter-spacing:-.04em; display:flex; align-items:center; gap:12px; }
.status-dot { width:7px; height:7px; border-radius:50%; background:#e9b872; }
.status-dot.online { background:var(--accent); box-shadow:0 0 12px #66dec760; }
.connection-status { color:var(--muted); font:11px monospace; }
.connection-status span { color:var(--accent); }
.playback { display:flex; align-items:center; gap:24px; }
.volume-control { display:flex; align-items:center; gap:10px; font-size:11px; color:var(--muted); }
.volume-control input { width:85px; }
@media(max-width:800px) { .receiver-header { align-items:flex-start; flex-direction:column; } .playback { width:100%; justify-content:space-between; flex-wrap:wrap; gap:12px; } }
</style>
