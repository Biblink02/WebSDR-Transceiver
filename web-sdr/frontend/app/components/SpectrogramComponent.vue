<script setup lang="ts">
import {ref, onMounted, watch} from 'vue';

// --- Props ---
const props = defineProps({
    magnitudes: {
        type: [Float32Array, Array],
        default: () => null
    }
});

// --- Canvas State ---
const canvasRef = ref(null);
let ctx: any = null;

const minDb = -100; // Value for the colder color
const maxDb = -20;  // Value for the hottest color

// --- Canvas Drawing Functions ---

function magnitudeToColor(magnitudeDb: any) {
    let norm = (magnitudeDb - minDb) / (maxDb - minDb);
    if (norm < 0) norm = 0;
    if (norm > 1) norm = 1;

    const hue = 240 - (norm * 240);
    return `hsl(${hue}, 100%, 50%)`;
}

function draw(magnitudes: any) {
    if (!ctx || !canvasRef.value || !magnitudes) return;

    const canvas: any = canvasRef.value;
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    ctx.drawImage(canvas, 0, 1, canvasWidth, canvasHeight - 1, 0, 0, canvasWidth, canvasHeight - 1);

    for (let i = 0; i < canvasWidth; i++) {
        const magnitude = magnitudes[i] || minDb;
        ctx.fillStyle = magnitudeToColor(magnitude);
        ctx.fillRect(i, canvasHeight - 1, 1, 1);
    }
}

function resizeData(data: any, targetWidth: number) {
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
}

// --- Lifecycle ---

onMounted(() => {
    const canvas: any = canvasRef.value;
    if (canvas) {
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
        ctx = canvas.getContext('2d');

        ctx.fillStyle = magnitudeToColor(minDb);
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
});

// --- Watcher ---
watch(() => props.magnitudes, (newMagnitudes) => {
    if (!ctx || !canvasRef.value || !newMagnitudes || newMagnitudes.length === 0) {
        return;
    }

    const canvasWidth: number = canvasRef.value.width;
    const processedMagnitudes = resizeData(newMagnitudes, canvasWidth);
    draw(processedMagnitudes);
});

</script>

<template>
    <canvas ref="canvasRef"></canvas>
</template>
