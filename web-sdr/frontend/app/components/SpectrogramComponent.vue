<script setup>
import { ref, onMounted, watch } from 'vue';

// --- Props ---
// Riceviamo le magnitudini calcolate dal componente padre
const props = defineProps({
    magnitudes: {
        type: [Float32Array, Array],
        default: () => null
    }
});

// --- Canvas State ---
const canvasRef = ref(null);
let ctx = null;

// --- Costanti per il colore ---
// Regola questi valori per cambiare il range dinamico del tuo spettrogramma
const minDb = -100; // Valore dB mappato al colore "più freddo" (blu)
const maxDb = -20;  // Valore dB mappato al colore "più caldo" (rosso)

// --- Canvas Drawing Functions ---

/**
 * Converte una magnitudine in dB in un colore HSL.
 */
const magnitudeToColor = (magnitudeDb) => {
    // Normalizza la magnitudine (dB) in un range 0.0 - 1.0
    let norm = (magnitudeDb - minDb) / (maxDb - minDb);
    if (norm < 0) norm = 0;
    if (norm > 1) norm = 1;

    // Mappa 0.0 (basso) -> blu (hue 240)
    // Mappa 1.0 (alto) -> rosso (hue 0)
    const hue = 240 - (norm * 240);
    return `hsl(${hue}, 100%, 50%)`;
};

const draw = (magnitudes) => {
    if (!ctx || !canvasRef.value || !magnitudes) return;

    const canvas = canvasRef.value;
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    // 1. Sposta l'immagine esistente su di 1 pixel
    ctx.drawImage(canvas, 0, 1, canvasWidth, canvasHeight - 1, 0, 0, canvasWidth, canvasHeight - 1);

    // 2. Disegna la nuova riga di pixel in basso
    for (let i = 0; i < canvasWidth; i++) {
        // magnitudes[i] è ora un valore in dB (es. -80.5)
        const magnitude = magnitudes[i] || minDb;
        ctx.fillStyle = magnitudeToColor(magnitude);
        ctx.fillRect(i, canvasHeight - 1, 1, 1);
    }
};

/**
 * Ridimensiona l'array di magnitudini per adattarlo alla larghezza del canvas.
 */
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

// --- Lifecycle ---

onMounted(() => {
    const canvas = canvasRef.value;
    if (canvas) {
        // Imposta la risoluzione del canvas
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
        ctx = canvas.getContext('2d');

        // Riempi con il colore di base (corrispondente a minDb)
        ctx.fillStyle = magnitudeToColor(minDb);
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
});

// --- Watcher ---
// Questo è il cuore del componente figlio.
// Reagisce quando la prop 'magnitudes' cambia.
watch(() => props.magnitudes, (newMagnitudes) => {
    if (!ctx || !canvasRef.value || !newMagnitudes || newMagnitudes.length === 0) {
        return; // Non fare nulla se non c'è contesto o dati
    }

    const canvasWidth = canvasRef.value.width;
    const processedMagnitudes = resizeData(newMagnitudes, canvasWidth);
    draw(processedMagnitudes);
});

</script>

<template>
    <canvas ref="canvasRef"></canvas>
</template>
