<script setup lang="ts">
import {ref, onMounted, onUnmounted} from 'vue';

// --- Props ---
defineProps({
    // You can keep other props if you have them
});

// --- Canvas State ---
const canvasRef = ref<HTMLCanvasElement | null>(null);
let ctx: CanvasRenderingContext2D | null = null;
let animationFrameId: number | null = null;

// --- Data Buffer ---
// Questo buffer ora contiene magnitudini LINEARI
let latestMagnitudes: Float32Array | null = null;

// --- Auto-DB / AGC State ---
let currentMaxDb = -20.0;
let currentMinDb = -100.0;

const dynamicRange = 80.0;
const autoGainAttack = 0.1;
const autoGainRelease = 0.005;

// --- Funzione di conversione ---
const NOISE_FLOOR_DB = -120.0; // Impedisce Math.log10(0) = -Infinity

function linearToDb(data: Float32Array): Float32Array {
    const dbData = new Float32Array(data.length);
    for (let i = 0; i < data.length; i++) {
        // 20 * log10(magnitudine)
        const db = 20 * Math.log10(data[i]);
        // Applica il "noise floor"
        dbData[i] = db < NOISE_FLOOR_DB ? NOISE_FLOOR_DB : db;
    }
    return dbData;
}


// --- Canvas Drawing Functions ---

function magnitudeToColor(magnitudeDb: number, minDb: number, maxDb: number) {
    let norm = (magnitudeDb - minDb) / (maxDb - minDb);
    if (norm < 0) norm = 0;
    if (norm > 1) norm = 1;

    const hue = 240 - (norm * 240);
    return `hsl(${hue}, 100%, 50%)`;
}

// Draw ora accetta dati lineari e li converte
function draw(linearMagnitudes: Float32Array) {
    if (!ctx || !canvasRef.value) return;

    // --- 1. Converti in dB ---
    const magnitudesDb = linearToDb(linearMagnitudes);

    const canvas = canvasRef.value;
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    // --- 2. Trova il picco nei dati dB ---
    let dataPeak = -Infinity;
    for (let i = 0; i < magnitudesDb.length; i++) {
        if (magnitudesDb[i] > dataPeak) dataPeak = magnitudesDb[i];
    }
    if (dataPeak === -Infinity) dataPeak = currentMaxDb;

    // --- 3. Applica la logica AGC (Attack/Release) al MaxDB ---
    if (dataPeak > currentMaxDb) {
        currentMaxDb += (dataPeak - currentMaxDb) * autoGainAttack;
    } else {
        currentMaxDb -= (currentMaxDb - dataPeak) * autoGainRelease;
    }

    // --- 4. Calcola il MinDB in base al range dinamico ---
    currentMinDb = currentMaxDb - dynamicRange;

    // --- 5. Disegna la riga ---
    const processedMagnitudes = resizeData(magnitudesDb, canvasWidth);

    ctx.drawImage(canvas, 0, 1, canvasWidth, canvasHeight - 1, 0, 0, canvasWidth, canvasHeight - 1);

    for (let i = 0; i < canvasWidth; i++) {
        const magnitude = processedMagnitudes[i] || currentMinDb;
        ctx.fillStyle = magnitudeToColor(magnitude, currentMinDb, currentMaxDb);
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
        draw(latestMagnitudes); // Passa i dati lineari a draw
        latestMagnitudes = null;
    }
}

// --- Public Method ---
// Questa funzione riceve i dati LINEARI dal genitore
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
            ctx.fillStyle = magnitudeToColor(currentMinDb, currentMinDb, currentMaxDb);
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }

        renderLoop();
    }
});

onUnmounted(() => {
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
    }
});

</script><template>
    <canvas ref="canvasRef"></canvas>
</template>
