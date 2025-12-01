<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

const canvasRef = ref<HTMLCanvasElement | null>(null);
let ctx: CanvasRenderingContext2D | null = null;
let animationFrameId: number | null = null;

let latestMagnitudesDb: Float32Array | null = null;

let currentMaxDb = -20.0;
let currentMinDb = -100.0;
const dynamicRange = 70.0;
const autoGainAttack = 0.05;
const autoGainRelease = 0.005;

function magnitudeToColor(magnitudeDb: number, minDb: number, maxDb: number) {
    let norm = (magnitudeDb - minDb) / (maxDb - minDb);
    if (norm < 0) norm = 0;
    if (norm > 1) norm = 1;

    const hue = 240 - (norm * 240);
    return `hsl(${hue}, 100%, 50%)`;
}

function draw(magnitudesDb: Float32Array) {
    if (!ctx || !canvasRef.value) return;

    const canvas = canvasRef.value;
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    let dataPeak = -Infinity;
    for (let i = 0; i < magnitudesDb.length; i += 10) {
        if (magnitudesDb[i] > dataPeak) dataPeak = magnitudesDb[i];
    }
    if (dataPeak === -Infinity) dataPeak = currentMaxDb;

    if (dataPeak > currentMaxDb) {
        currentMaxDb += (dataPeak - currentMaxDb) * autoGainAttack;
    } else {
        currentMaxDb -= (currentMaxDb - dataPeak) * autoGainRelease;
    }
    currentMinDb = currentMaxDb - dynamicRange;

    ctx.drawImage(canvas, 0, 0, canvasWidth, canvasHeight - 1, 0, 1, canvasWidth, canvasHeight - 1);

    const processedMagnitudes = resizeData(magnitudesDb, canvasWidth);

    for (let i = 0; i < canvasWidth; i++) {
        const magnitude = processedMagnitudes[i];
        ctx.fillStyle = magnitudeToColor(magnitude, currentMinDb, currentMaxDb);
        ctx.fillRect(i, 0, 1, 1);
    }
}

function resizeData(data: Float32Array, targetWidth: number): Float32Array {
    if (!data || data.length === 0) return new Float32Array(targetWidth);
    if (data.length === targetWidth) return data;

    const resized = new Float32Array(targetWidth);
    const scale = data.length / targetWidth;

    for (let i = 0; i < targetWidth; i++) {
        const index = Math.floor(i * scale);
        resized[i] = data[index];
    }
    return resized;
}

function renderLoop() {
    animationFrameId = requestAnimationFrame(renderLoop);
    if (latestMagnitudesDb) {
        draw(latestMagnitudesDb);
        latestMagnitudesDb = null;
    }
}

function setLatestData(data: Float32Array) {
    latestMagnitudesDb = data;
}

defineExpose({ setLatestData });

onMounted(() => {
    const canvas = canvasRef.value;
    if (canvas) {
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
        ctx = canvas.getContext('2d', { alpha: false });

        if (ctx) {
            ctx.fillStyle = '#000000';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }
        renderLoop();
    }
});

onUnmounted(() => {
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
});
</script>

<template>
    <canvas ref="canvasRef" class="w-full h-full bg-black block"></canvas>
</template>
