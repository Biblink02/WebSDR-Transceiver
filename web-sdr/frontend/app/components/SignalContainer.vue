<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { io } from 'socket.io-client';
import { fft, magDb } from '@thi.ng/dsp'; // <-- Importiamo le funzioni DSP
import SpectrogramCanvas from './SpectrogramCanvas.vue'; // <-- Importiamo il figlio

// --- State per la WebSocket ---
const isConnected = ref(false);
const statusText = ref('CONNECTING');
const wsUrl = import.meta.env.VITE_WS_URL ?? 'http://localhost:8001';
const wsEvent = import.meta.env.VITE_WS_EVENT ?? 'update';
let socket = null;

// --- State per i dati DSP ---
// Questo ref conterrà i risultati della FFT (le magnitudini)
// e sarà passato come prop al componente canvas.
const fftMagnitudes = ref(null);

// --- Gestione Connessione ---
const toggleConnection = () => {
    if (!socket) return;
    if (isConnected.value) {
        socket.disconnect();
    } else {
        statusText.value = 'CONNECTING';
        socket.connect();
    }
};

// --- Lifecycle & Socket.IO ---
onMounted(() => {
    socket = io(wsUrl, {
        transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        isConnected.value = true;
        statusText.value = 'CONNECTED';
        console.log('Socket.IO connected:', socket.id);
    });

    socket.on('disconnect', () => {
        isConnected.value = false;
        statusText.value = 'DISCONNECTED';
        console.log('Socket.IO disconnected');
    });

    socket.on('connect_error', (err) => {
        isConnected.value = false;
        statusText.value = 'ERROR';
        console.error('Socket.IO connection error:', err.message);
    });

    socket.on(wsEvent, (rawData) => {
        if (!rawData) return;

        try {
            let timeDomainData;

            // Converti i dati in arrivo in un Float32Array
            if (rawData instanceof ArrayBuffer) {
                timeDomainData = new Float32Array(rawData);
            } else if (Array.isArray(rawData)) {
                timeDomainData = Float32Array.from(rawData);
            } else {
                console.warn("Unhandled raw data format:", typeof rawData);
                return;
            }

            // Assicurati che ci siano dati e che la lunghezza sia una potenza di 2
            // (La FFT è molto più efficiente con potenze di 2)
            if (timeDomainData.length === 0) return;
            if ((timeDomainData.length & (timeDomainData.length - 1)) !== 0) {
                console.warn(`Data length (${timeDomainData.length}) is not a power of 2. FFT might be slow or inaccurate.`);
                // Qui potresti troncare o padellare i dati, es:
                // timeDomainData = timeDomainData.slice(0, 1024);
            }

            // --- 1. Esegui la FFT ---
            // `fft` prende un segnale reale e restituisce uno spettro complesso
            // (interleaved: [re0, im0, re1, im1, ...])
            const spectrum = fft(timeDomainData);

            // --- 2. Calcola le Magnitudini in Decibel (dB) ---
            // `magDb` calcola 20 * log10(sqrt(re^2 + im^2)) per ogni bin
            const magnitudesDb = magDb(spectrum);

            // --- 3. Prendi solo la prima metà dello spettro ---
            // La seconda metà è uno specchio della prima (per segnali reali)
            const halfSpectrum = magnitudesDb.slice(0, magnitudesDb.length / 2);

            // --- 4. Aggiorna il ref ---
            // Vue rileverà questo cambiamento e passerà i nuovi dati al figlio
            fftMagnitudes.value = halfSpectrum;

        } catch (e) {
            console.error("Error processing raw data:", e);
        }
    });
});

onUnmounted(() => {
    if (socket) {
        socket.disconnect();
    }
});
</script>

<template>
    <Card>
        <template #content>
            <div class="flex flex-col items-center">
                <h2 class="text-2xl font-bold mb-4">Spectrogram</h2>
                <p class="mb-5 text-sm">X axis: Frequency → | Y axis: Time ↓ </p>
                <p class="mb-3 text-xs font-mono">
                    Socket.IO Status: <span :class="isConnected ? 'text-green-500' : 'text-red-500'">{{ statusText }}</span>
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

                <SpectrogramCanvas
                    :magnitudes="fftMagnitudes"
                    class="w-full h-80 rounded-md"
                />
            </div>
        </template>
    </Card>
</template>
