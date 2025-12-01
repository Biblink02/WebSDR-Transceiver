<script setup lang="ts">
import {onMounted, onUnmounted, ref} from 'vue';
import AudioComponent from "&/components/AudioComponent.vue";
import SpectrogramComponent from "&/components/SpectrogramComponent.vue";
import MyWorker from '@/workers/socket.worker.ts?worker'
import {feedAudio} from "@/AudioPlayer";


// --- State ---
const isConnected = ref(false);
const statusText = ref('CONNECTING');
const audioData = ref<Float32Array | null>(null);

// Reference to our Worker
let socketWorker: Worker | null = null;

// Reference to the SpectrogramComponent instance
const spectrogramComponentRef = ref<InstanceType<typeof SpectrogramComponent> | null>(null);

// Information to pass to the Worker
const wsUrl = import.meta.env.VITE_WS_URL ?? 'http://localhost:80';
// Get the specific event names from .env
const wsEventGraphics = import.meta.env.VITE_WS_GRAPHICS_EVENT ?? 'update_graphic';
const wsEventAudio = import.meta.env.VITE_WS_AUDIO_EVENT ?? 'update_audio';

onMounted(() => {
    socketWorker = new MyWorker()
    if(!socketWorker) return;
    socketWorker.onmessage = (event: MessageEvent) => {
        const {type, payload} = event.data;

        switch (type) {
            case 'status':
                statusText.value = payload.status;
                isConnected.value = payload.isConnected;
                break;
            case 'graphicData':
                if (spectrogramComponentRef.value) {
                    spectrogramComponentRef.value.setLatestData(payload);
                }
                break;
            case 'audioData':
                feedAudio(payload);
                break;
            case 'error':
                console.error("Error from DSP Worker:", payload);
                break;
        }
    };

    console.log("Sending init message");

    socketWorker.postMessage({
        type: 'init',
        payload: {wsUrl, wsEventGraphics, wsEventAudio}
    });
});

onUnmounted(() => {
    if (socketWorker) {
        socketWorker.postMessage({type: 'disconnect'});
        socketWorker.terminate();
    }
});

function toggleConnection(): void {
    if (socketWorker) {
        socketWorker.postMessage({type: 'toggleConnection'});
    }

}

function toggleAudio(): void {
    if (socketWorker) {
        socketWorker.postMessage({type: 'toggleAudio'})
    }
}
</script>

<template>
    <Card>
        <template #content>
            <div class="flex flex-col items-center">
                <h2 class="text-2xl font-bold mb-4">Spectrogram</h2>
                <p class="mb-5 text-sm">X axis: Frequency → | Y axis: Time ↓ </p>
                <p class="mb-3 text-xs font-mono">
                    Socket.IO Status: <span :class="isConnected ? 'text-green-500' : 'text-red-500'">{{
                        statusText
                    }}</span>
                </p>

                <button
                    @click="toggleConnection"
                    class="mb-4 px-4 py-2 cursor-pointer rounded-md text-white font-semibold transition-colors text-sm"
                    :class="isConnected
                        ? 'bg-red-500 hover:bg-red-600'
                        : 'bg-green-500 hover:bg-green-600'"
                >
                    {{ isConnected ? 'Disconnect' : 'Connect' }}
                </button>

                <SpectrogramComponent
                    ref="spectrogramComponentRef"
                    class="w-full h-80 rounded-md"
                />

                <AudioComponent :samples="audioData" @toggle-audio="toggleAudio()"/>
            </div>
        </template>
    </Card>
</template>
