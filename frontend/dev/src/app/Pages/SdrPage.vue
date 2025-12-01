<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import AppLayout from '&/layouts/AppLayout.vue';
import SpectrogramComponent from '&/components/SpectrogramComponent.vue';
import FrequencyControl from '&/components/FrequencyControl.vue';
import SocketWorker from '@/workers/socket.worker.ts?worker';
import { setVolume, feedAudio, startAudioPlayback, stopAudioPlayback } from "@/AudioPlayer";

// --- State ---
const isConnected = ref(false);
const statusText = ref('CONNECTING');
const workerStatus = ref<'IDLE' | 'LISTENING' | 'FULL'>('IDLE');
const assignedWorkerId = ref<string | null>(null);

const CENTER_FREQ = 102500000;
const tuneFreq = ref(CENTER_FREQ);
const bandwidth = ref(15000);
const volume = ref(100);

const spectrogramRef = ref<InstanceType<typeof SpectrogramComponent> | null>(null);
let socketWorker: Worker | null = null;
const wsUrl = import.meta.env.VITE_WS_URL || 'http://localhost:80';

// --- Worker Logic ---
onMounted(() => {
    socketWorker = new SocketWorker();
    if (!socketWorker) return;

    socketWorker.onmessage = (event: MessageEvent) => {
        const { type, payload } = event.data;

        switch (type) {
            case 'status':
                statusText.value = payload.status;
                isConnected.value = payload.isConnected;
                if (!payload.isConnected) stopAudio();
                break;

            case 'graphicData':
                spectrogramRef.value?.setLatestData(payload);
                break;

            case 'audioData':
                feedAudio(payload);
                break;

            case 'workerAssigned':
                workerStatus.value = 'LISTENING';
                assignedWorkerId.value = payload.worker;
                if (payload.freq) tuneFreq.value = payload.freq;
                startAudioPlayback();
                break;

            case 'workerReleased':
                workerStatus.value = 'IDLE';
                assignedWorkerId.value = null;
                stopAudioPlayback();
                break;

            case 'serverFull':
                workerStatus.value = 'FULL';
                alert("Server busy: No audio workers available.");
                break;

            case 'error':
                console.error("Worker Error:", payload);
                break;
        }
    };

    socketWorker.postMessage({ type: 'init', payload: { wsUrl } });
});

onUnmounted(() => {
    stopAudio();
    if (socketWorker) {
        socketWorker.postMessage({ type: 'disconnect' });
        socketWorker.terminate();
    }
});

// --- Actions ---
function toggleAudio() {
    if (!socketWorker) return;

    if (workerStatus.value === 'LISTENING') {
        socketWorker.postMessage({ type: 'releaseWorker' });
    } else {
        socketWorker.postMessage({
            type: 'requestWorker',
            payload: { freq: tuneFreq.value, bw: bandwidth.value }
        });
    }
}

function stopAudio() {
    if (workerStatus.value === 'LISTENING' && socketWorker) {
        socketWorker.postMessage({ type: 'releaseWorker' });
    }
    stopAudioPlayback();
}

function updateTuning() {
    if (workerStatus.value === 'LISTENING' && socketWorker) {
        socketWorker.postMessage({
            type: 'tune',
            payload: { freq: Number(tuneFreq.value), bw: Number(bandwidth.value) }
        });
    }
}

// Handlers for the FrequencyControl Component
function onFreqUpdate(newFreq: number) {
    tuneFreq.value = newFreq;
    updateTuning();
}

function onBwUpdate(newBw: number) {
    bandwidth.value = newBw;
    updateTuning();
}

function updateVolume() {
    setVolume(volume.value / 100);
}
</script>

<template>
    <AppLayout>
        <div class="flex flex-col h-[calc(100vh-theme('spacing.24'))] max-w-7xl mx-auto w-full p-4 gap-4">

            <div class="flex flex-wrap justify-between items-center bg-gray-900/90 p-4 rounded-lg backdrop-blur border border-gray-700 shadow-lg shrink-0">

                <div>
                    <h1 class="text-xl font-bold text-white tracking-wide">SDR CONSOLE</h1>
                    <div class="flex items-center gap-3 text-xs font-mono mt-1">
                        <span :class="isConnected ? 'text-green-400' : 'text-red-500'">
                            {{ statusText }}
                        </span>
                        <span v-if="workerStatus === 'LISTENING'" class="text-blue-400 animate-pulse">
                            ● AUDIO ACTIVE ({{ assignedWorkerId }})
                        </span>
                        <span v-if="workerStatus === 'FULL'" class="text-yellow-500">
                            ⚠ SYSTEM BUSY
                        </span>
                    </div>
                </div>

                <div class="flex items-center gap-6">
                    <div class="flex items-center gap-3 bg-black/30 px-3 py-2 rounded-full border border-gray-700">
                        <span class="text-gray-400 text-xs font-bold uppercase">Vol</span>
                        <input
                            type="range"
                            min="0"
                            max="100"
                            v-model="volume"
                            @input="updateVolume"
                            class="w-24 h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        />
                    </div>

                    <button
                        @click="toggleAudio"
                        :disabled="!isConnected || workerStatus === 'FULL'"
                        class="px-6 py-2 rounded font-bold text-sm transition-all shadow-lg border border-transparent"
                        :class="workerStatus === 'LISTENING'
                            ? 'bg-red-600/90 hover:bg-red-600 text-white border-red-500'
                            : 'bg-blue-600/90 hover:bg-blue-600 text-white border-blue-500 disabled:opacity-50 disabled:grayscale'"
                    >
                        {{ workerStatus === 'LISTENING' ? 'STOP RECEIVER' : 'START RECEIVER' }}
                    </button>
                </div>
            </div>

            <div class="relative w-full flex-grow bg-black rounded-lg overflow-hidden border border-gray-700 shadow-2xl flex flex-col">

                <SpectrogramComponent
                    ref="spectrogramRef"
                    class="w-full h-full block"
                    :frequency="tuneFreq"
                />

                <div class="absolute top-0 bottom-0 left-1/2 w-px bg-red-500/60 pointer-events-none z-0"></div>

                <div class="absolute bottom-0 left-0 w-full z-10">
                    <FrequencyControl
                        :frequency="tuneFreq"
                        :bandwidth="bandwidth"
                        @update:frequency="onFreqUpdate"
                        @update:bandwidth="onBwUpdate"
                    />
                </div>
            </div>

        </div>
    </AppLayout>
</template>
