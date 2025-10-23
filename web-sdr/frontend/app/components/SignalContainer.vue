<script setup lang="ts">
import {onMounted, onUnmounted, ref} from 'vue';
import AudioComponent from "&/components/AudioComponent.vue";
import SpectrogramComponent from "&/components/SpectrogramComponent.vue";
import MyWorker from '@/workers/dsp.worker.ts?worker'


const isConnected = ref(false);
const statusText = ref('CONNECTING');
const fftMagnitudes = ref<Float32Array | null>(null);
const audioData = ref<Float32Array | null>(null);

let dspWorker: Worker | null = null;

const wsUrl = import.meta.env.VITE_WS_URL ?? 'http://localhost:8001';
const wsEvent = import.meta.env.VITE_WS_EVENT ?? 'update';


//demod

onMounted(() => {


    //play audio


    dspWorker = new MyWorker()

    dspWorker.onmessage = (event: MessageEvent) => {
        const {type, payload} = event.data;

        switch (type) {
            case 'status':
                statusText.value = payload.status;
                isConnected.value = payload.isConnected;
                break;
            case 'fftData':
                fftMagnitudes.value = payload;
                break;
            case 'audioData':
                audioData.value = payload;
                break;
            case 'error':
                console.error("Error from DSP Worker:", payload);
                break;
        }
    };
    console.log("Sendig init message");
    dspWorker.postMessage({
        type: 'init',
        payload: {wsUrl, wsEvent}
    });
});

onUnmounted(() => {
    if (dspWorker) {
        dspWorker.postMessage({type: 'disconnect'});
        dspWorker.terminate();
    }
});

const toggleConnection = () => {
    if (dspWorker) {
        dspWorker.postMessage({type: 'toggleConnection'});
    }

};
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
                    :magnitudes="fftMagnitudes"
                    class="w-full h-80 rounded-md"
                />

                <AudioComponent :samples="audioData"/>
            </div>
        </template>
    </Card>
</template>
