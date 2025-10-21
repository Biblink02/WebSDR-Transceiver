<template>
    <Card>
        <template #content>
            <div class="flex flex-col items-center">
                <h2 class="text-2xl font-bold  mb-4">Spettrogramma in Tempo Reale</h2>
                <p class="mb-5 text-sm">Asse Verticale (Y): Tempo ↓ | Asse Orizzontale (X): Frequenza →</p>
                <canvas
                    ref="canvasRef"
                    class="w-full h-80 rounded-md"
                ></canvas>
            </div>
        </template>
    </Card>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const canvasRef = ref(null);
let ctx = null;
let intervalId = null;
let time = 0;

const magnitudeToColor = (magnitude) => {
    if (magnitude < 0) magnitude = 0;
    if (magnitude > 255) magnitude = 255;
    const hue = 240 - (magnitude / 255) * 240;
    return `hsl(${hue}, 100%, 50%)`;
};

const draw = () => {
    if (!ctx || !canvasRef.value) return;

    const canvas = canvasRef.value;
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    // 1. Sposta l'immagine esistente di un pixel verso l'alto (scorrimento verticale)
    ctx.drawImage(canvas, 0, 1, canvasWidth, canvasHeight - 1, 0, 0, canvasWidth, canvasHeight - 1);

    // 2. Genera un nuovo array di magnitudini basato sulla LARGHEZZA del canvas
    const magnitudes = new Float32Array(canvasWidth);
    const peak1_pos = canvasWidth * 0.25 + Math.sin(time * 0.05) * 50;
    const peak2_pos = canvasWidth * 0.75 + Math.cos(time * 0.03) * 70;

    for (let i = 0; i < canvasWidth; i++) {
        let mag = Math.random() * 15;
        mag += 180 * Math.exp(-Math.pow(i - peak1_pos, 2) / 80);
        mag += 220 * Math.exp(-Math.pow(i - peak2_pos, 2) / 120);
        magnitudes[i] = mag;
    }

    time++;

    // 3. Disegna la nuova riga orizzontale di pixel sul fondo del canvas
    for (let i = 0; i < canvasWidth; i++) {
        const magnitude = magnitudes[i];
        ctx.fillStyle = magnitudeToColor(magnitude);
        ctx.fillRect(i, canvasHeight - 1, 1, 1); // Disegna su y costante
    }
};

onMounted(() => {
    const canvas = canvasRef.value;
    if (canvas) {
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
        ctx = canvas.getContext('2d');
        intervalId = setInterval(draw, 50);
    }
});

onUnmounted(() => {
    if (intervalId) {
        clearInterval(intervalId);
    }
});
</script>
