
<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { io } from 'socket.io-client'; // Import Socket.IO client library

const canvasRef = ref(null);
let ctx = null;
let socket = null;

// --- Socket.IO Connection State ---
const isConnected = ref(false);
const statusText = ref('CONNECTING');

const wsUrl = 'http://localhost:8001';

// --- Canvas Drawing Functions ---
const magnitudeToColor = (magnitude) => {
    if (magnitude < 0) magnitude = 0;
    if (magnitude > 255) magnitude = 255;
    const hue = 240 - (magnitude / 255) * 240;
    return `hsl(${hue}, 100%, 50%)`;
};

const draw = (magnitudes) => {
    if (!ctx || !canvasRef.value || !magnitudes) return;

    const canvas = canvasRef.value;
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    // 1. Shift existing image up by 1 pixel
    ctx.drawImage(canvas, 0, 1, canvasWidth, canvasHeight - 1, 0, 0, canvasWidth, canvasHeight - 1);

    // 2. Draw the new pixel row at the bottom
    for (let i = 0; i < canvasWidth; i++) {
        const magnitude = magnitudes[i] || 0;
        ctx.fillStyle = magnitudeToColor(magnitude);
        ctx.fillRect(i, canvasHeight - 1, 1, 1);
    }
};

// --- Data Handling ---

const resizeData = (data, targetWidth) => {
    if (!data || data.length === 0 || targetWidth === 0) {
        return new Float32Array(targetWidth);
    }
    if (data.length === targetWidth) {
        return data;
    }

    const resized = new Float32Array(targetWidth);
    const scale = data.length / targetWidth;

    for (let i = 0; i < targetWidth; i++) {
        const index = Math.floor(i * scale);
        resized[i] = data[index];
    }
    return resized;
};

// --- Lifecycle & Socket.IO Listeners ---

onMounted(() => {
    const canvas = canvasRef.value;
    if (canvas) {
        // Set canvas resolution
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
        ctx = canvas.getContext('2d');

        // Fill base color
        ctx.fillStyle = magnitudeToColor(0);
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    // Connect to Socket.IO server
    socket = io(wsUrl, {
        transports: ['websocket', 'polling'] // Allow fallback to polling
    });

    // --- Standard Socket.IO Events ---
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

    // --- Custom Data Event ---
    // !!! CHANGE 'spectrogram-data' to match your server event name !!!
    socket.on('spectrogram-data', (newData) => {
        if (!newData || !ctx) return;

        console.log(newData)
        let incomingMagnitudes;
        const canvasWidth = canvasRef.value.width;

        try {
            // Socket.IO gestisce già il parsing di JSON e ArrayBuffer
            if (newData instanceof ArrayBuffer) {
                incomingMagnitudes = new Float32Array(newData);
            } else if (Array.isArray(newData)) {
                incomingMagnitudes = newData;
            } else {
                console.warn("Unhandled Socket.IO data format:", typeof newData);
                return;
            }

            const processedMagnitudes = resizeData(incomingMagnitudes, canvasWidth);
            draw(processedMagnitudes);

        } catch (e) {
            console.error("Error processing Socket.IO data:", e);
        }
    });
});

onUnmounted(() => {
    // Disconnect the socket when the component is destroyed
    if (socket) {
        socket.disconnect();
    }
});
</script>

<template>
    <Card>
        <template #content>
            <div class="flex flex-col items-center">
                <h2 class="text-2xl font-bold mb-4">Spettrogramma in Tempo Reale</h2>
                <p class="mb-5 text-sm">Asse Verticale (Y): Tempo ↓ | Asse Orizzontale (X): Frequenza →</p>
                <p class="mb-3 text-xs font-mono">
                    Socket.IO Status: <span :class="isConnected ? 'text-green-500' : 'text-red-500'">{{ statusText }}</span>
                </p>
                <canvas
                    ref="canvasRef"
                    class="w-full h-80 rounded-md"
                ></canvas>
            </div>
        </template>
    </Card>
</template>

