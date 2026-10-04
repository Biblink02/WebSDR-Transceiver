<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useSdrStore } from './store'
import { useReceiver } from './composables/useReceiver'
import ReceiverHeader from './components/ReceiverHeader.vue'
import TuningPanel from './components/TuningPanel.vue'
import AutomationPanel from './components/AutomationPanel.vue'
import DisplayPanel from './components/DisplayPanel.vue'
import SignalPanel from './components/SignalPanel.vue'
import BookmarkPanel from './components/BookmarkPanel.vue'
import SpectrumView from './components/SpectrumView.vue'
import AudioPanel from './components/AudioPanel.vue'
import RecordingPanel from './components/RecordingPanel.vue'
import { useRecording } from './composables/useRecording'
import { useShortcuts } from './composables/useShortcuts'
const store = useSdrStore(), receiver = useReceiver()
const recording = useRecording()
useShortcuts(() => { void receiver.toggleAudio() }, recording.toggle)
const plot = ref<InstanceType<typeof SpectrumView> | null>(null)
onMounted(() => receiver.initWorker(data => plot.value?.setLatestData(data)))
</script>
<template>
    <main class="receiver-console">
        <Toast/>
        <ReceiverHeader @toggle-audio="receiver.toggleAudio" @toggle-connection="receiver.toggleConnection"/>
        <div class="receiver-top"><TuningPanel/><AutomationPanel @find-strongest="receiver.findStrongest" @auto-all="receiver.autoAll"/></div>
        <SpectrumView ref="plot"/>
        <div class="receiver-bottom"><div class="receiver-sidebar"><DisplayPanel/><AudioPanel/><RecordingPanel :recording="recording"/></div>
            <div class="receiver-sidebar"><SignalPanel @select="receiver.select" @track="receiver.pin"/><BookmarkPanel/></div></div>
        <div class="receiver-telemetry"><span><i class="pi pi-bolt"/> Demand-driven capture · per-listener tuning</span>
            <span>{{ (store.settings.samp_rate / 1000).toFixed(1) }} kS/s · {{ store.frames.toLocaleString() }} frames · {{ store.processingMs.toFixed(1) }} ms DSP/frame · {{ store.gaps }} gaps</span>
        </div>
    </main>
</template>
<style>
.receiver-console { --accent:#66dec7; --text:#dce7f0; --muted:#8395a7; --line:#243446; color:var(--text); max-width:1440px; margin:75px auto 0; display:flex; flex-direction:column; gap:16px; font-family:Inter,sans-serif; }
.receiver-console .panel { background:#0e1925f5; border:1px solid var(--line); border-radius:12px; box-shadow:0 8px 24px #00000018; }
.receiver-console .section-title { font-size:10px; font-weight:650; letter-spacing:.12em; color:#b2c5d5; display:flex; justify-content:space-between; align-items:center; gap:10px; }
.receiver-console .section-title span { font-size:9px; color:var(--muted); font-weight:400; letter-spacing:.06em; }
.receiver-console .eyebrow { font-size:9px; color:var(--muted); letter-spacing:.18em; }
.receiver-console .muted { color:var(--muted); }
.receiver-console .fine-print { font-size:11px; line-height:1.6; }
.receiver-console button { display:inline-flex; align-items:center; justify-content:center; gap:7px; font-size:11px; font-weight:500; padding:9px 12px; border:1px solid #34485d; border-radius:7px; background:#192a3b; cursor:pointer; color:var(--text); white-space:nowrap; transition:background .12s; }
.receiver-console button:hover { background:#253e52; }
.receiver-console button:disabled { opacity:.45; cursor:default; }
.receiver-console button.primary { background:var(--accent); border-color:var(--accent); color:#092721; }
.receiver-console button.primary:hover { background:#94ecd9; }
.receiver-console :is(button,input,select,summary):focus-visible { outline:2px solid var(--accent); outline-offset:3px; }
.receiver-console .button-row { display:flex; align-items:center; gap:8px; }
.receiver-console label { display:block; font-size:10px; color:var(--muted); }
.receiver-console :is(input[type=number],input[readonly],select) { display:block; width:100%; margin-top:7px; padding:9px 10px; color:var(--text); background:#0a1420; border:1px solid #2b4053; border-radius:6px; font:12px monospace; min-width:0; }
.receiver-console select { cursor:pointer; }
.receiver-console input[type=range] { display:block; width:100%; margin-top:12px; accent-color:var(--accent); height:5px; cursor:pointer; }
.receiver-console input[type=checkbox] { accent-color:var(--accent); width:14px; height:14px; }
.receiver-console .pi { font-size:12px; }
.receiver-top { display:grid; grid-template-columns:1.1fr 1fr; gap:16px; }
.receiver-bottom { display:grid; grid-template-columns:1.1fr 1fr; gap:16px; align-items:start; }
.receiver-sidebar { display:flex; flex-direction:column; gap:16px; }
.receiver-telemetry { display:flex; justify-content:space-between; gap:12px; font-size:10px; color:var(--muted); padding:2px 5px; flex-wrap:wrap; }
@media(max-width:900px) { .receiver-top,.receiver-bottom { grid-template-columns:1fr; } }
</style>
