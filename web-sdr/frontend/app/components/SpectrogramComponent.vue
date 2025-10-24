<script setup lang="ts">
import {ref, onMounted, onUnmounted} from 'vue';

// --- Props ---
// Props are no longer needed for magnitudes
defineProps({
    // You can keep other props if you have them
});

// --- Canvas State ---
const canvasRef = ref<HTMLCanvasElement | null>(null);
let ctx: CanvasRenderingContext2D | null = null;
let animationFrameId: number | null = null;

// --- Data Buffer ---
let latestMagnitudes: Float32Array | null = null;

const minDb = -100; // Value for the colder color
const maxDb = -20;  // Value for the hottest color

// --- Canvas Drawing Functions ---

function magnitudeToColor(magnitudeDb: number) {
    let norm = (magnitudeDb - minDb) / (maxDb - minDb);
    if (norm < 0) norm = 0;
    if (norm > 1) norm = 1;

    const hue = 240 - (norm * 240);
    return `hsl(${hue}, 100%, 50%)`;
}

function draw(magnitudes: Float32Array) {
    if (!ctx || !canvasRef.value) return;

    const canvas = canvasRef.value;
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    const processedMagnitudes = resizeData(magnitudes, canvasWidth);

    ctx.drawImage(canvas, 0, 1, canvasWidth, canvasHeight - 1, 0, 0, canvasWidth, canvasHeight - 1);

    for (let i = 0; i < canvasWidth; i++) {
        const magnitude = processedMagnitudes[i] || minDb;
        ctx.fillStyle = magnitudeToColor(magnitude);
        ctx.fillRect(i, canvasHeight - 1, 1, 1);
    }
}

function resizeData(data: Float32Array, targetWidth: number): Float32Array {
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

// --- Render Loop ---
function renderLoop() {
    animationFrameId = requestAnimationFrame(renderLoop);

    if (latestMagnitudes) {
        draw(latestMagnitudes);
        latestMagnitudes = null; // Clear buffer after drawing
    }
}

// --- Public Method ---
// This function will be called from the parent component (or worker handler)
function setLatestData(data: Float32Array) {
    latestMagnitudes = data;
}

defineExpose({ setLatestData });

// --- Lifecycle ---

onMounted(() => {
    const canvas = canvasRef.value;
    if (canvas) {
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
        ctx = canvas.getContext('2d');

        if (ctx) {
            ctx.fillStyle = magnitudeToColor(minDb);
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }

        renderLoop(); // Start the render loop
    }
});

onUnmounted(() => {
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
    }
});

</script>

<template>
    <canvas ref="canvasRef"></canvas>
</template>
