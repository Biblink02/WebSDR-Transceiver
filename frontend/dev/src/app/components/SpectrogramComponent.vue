<script lang="ts" setup>
import { onMounted, onUnmounted, ref, watch } from "vue";
import WaterfallWorker from '@/workers/waterfall.worker.ts?worker';
import { useSdrStore } from "@/stores/sdr.store";
import { useSpectrogramInteraction } from "@/composables/useSpectrogramInteraction";

const props = defineProps<{
    modelValue: number;
    bandwidth: number;
    range: number;
    gain: number;
    palette: string; // New Prop
}>();

const emit = defineEmits(["update:modelValue", "update:bandwidth"]);

const store = useSdrStore();
const config = store.settings;

const containerRef = ref<HTMLElement | null>(null);
const canvasWaterfall = ref<HTMLCanvasElement | null>(null);
const canvasOverlay = ref<HTMLCanvasElement | null>(null);
const canvasRuler = ref<HTMLCanvasElement | null>(null);

let ctxW: CanvasRenderingContext2D | null = null;
let ctxO: CanvasRenderingContext2D | null = null;
let ctxR: CanvasRenderingContext2D | null = null;
const worker = ref<Worker | null>(null);

const {
    zoom,
    panHz,
    hoverCursor,
    viewMin,
    viewMax,
    onDown,
    onMove,
    onUp,
    onWheel,
    hzToPx,
    getAdaptiveStep,
    formatFreq
} = useSpectrogramInteraction(config, () => props, emit, () => containerRef.value);

const RULER_HEIGHT = 30;

function updateWorkerView() {
    if (!worker.value) return;
    worker.value.postMessage({
        type: 'view',
        payload: {
            viewMin: viewMin.value,
            viewMax: viewMax.value
        }
    });
}

function updateWorkerConfig() {
    if(!worker.value) return;
    worker.value.postMessage({
        type: 'config',
        payload: {
            gain_attack: config.gain_attack,
            gain_release: config.gain_release,
            range_db: props.range,
            gain: props.gain
        }
    });
}

// Watch palette changes
watch(() => props.palette, (newPalette) => {
    worker.value?.postMessage({ type: 'palette', payload: newPalette });
});

watch(() => [props.range, props.gain], updateWorkerConfig);

function drawRuler() {
    if (!ctxR || !canvasRuler.value) return;
    const w = canvasRuler.value.width;
    const h = canvasRuler.value.height;

    ctxR.fillStyle = "#18181b";
    ctxR.fillRect(0, 0, w, h);

    ctxR.beginPath();
    ctxR.moveTo(0, h);
    ctxR.lineTo(w, h);
    ctxR.strokeStyle = "#3f3f46";
    ctxR.stroke();

    const hzVisible = viewMax.value - viewMin.value;
    const step = getAdaptiveStep(hzVisible, w);
    const startTick = Math.ceil(viewMin.value / step) * step;

    ctxR.font = "bold 11px monospace";
    ctxR.textAlign = "center";
    ctxR.fillStyle = "#a1a1aa";
    ctxR.strokeStyle = "#52525b";
    ctxR.lineWidth = 1;

    ctxR.beginPath();
    for (let f = startTick; f < viewMax.value; f += step) {
        const x = hzToPx(f, w);
        ctxR.moveTo(x, h);
        ctxR.lineTo(x, h - 5);
        ctxR.fillText(formatFreq(f), x, h - 8);
    }
    ctxR.stroke();

    const left = hzToPx(props.modelValue - props.bandwidth/2, w);
    const bwPx = (props.bandwidth / hzVisible) * w;
    const right = left + bwPx;

    ctxR.fillStyle = "rgba(74, 222, 128, 0.2)";
    ctxR.fillRect(left, 0, bwPx, h);

    ctxR.fillStyle = "#4ade80";
    ctxR.fillRect(left, h-10, 2, 10);
    ctxR.fillRect(right-2, h-10, 2, 10);

    const cx = hzToPx(props.modelValue, w);
    ctxR.beginPath();
    ctxR.strokeStyle = "#22c55e";
    ctxR.lineWidth = 2;
    ctxR.moveTo(cx, 0);
    ctxR.lineTo(cx, h);
    ctxR.stroke();

    ctxR.fillStyle = "#22c55e";
    ctxR.beginPath();
    ctxR.moveTo(cx - 5, 0);
    ctxR.lineTo(cx + 5, 0);
    ctxR.lineTo(cx, 6);
    ctxR.fill();

    ctxR.beginPath();
    ctxR.moveTo(0, h);
    ctxR.lineTo(w, h);
    ctxR.strokeStyle = "#3f3f46";
    ctxR.stroke();
}

function drawOverlay() {
    if (!ctxO || !canvasOverlay.value) return;
    const w = canvasOverlay.value.width;
    const h = canvasOverlay.value.height;

    ctxO.clearRect(0, 0, w, h);

    const hzVisible = viewMax.value - viewMin.value;
    const step = getAdaptiveStep(hzVisible, w);
    const startTick = Math.ceil(viewMin.value / step) * step;

    ctxO.beginPath();
    ctxO.strokeStyle = "rgba(255, 255, 255, 0.1)";
    ctxO.lineWidth = 1;
    for (let f = startTick; f < viewMax.value; f += step) {
        const x = hzToPx(f, w);
        ctxO.moveTo(x, 0);
        ctxO.lineTo(x, h);
    }
    ctxO.stroke();

    const left = hzToPx(props.modelValue - props.bandwidth/2, w);
    const bwPx = (props.bandwidth / hzVisible) * w;
    const right = left + bwPx;

    ctxO.fillStyle = "rgba(74, 222, 128, 0.1)";
    ctxO.fillRect(left, 0, bwPx, h);

    ctxO.fillStyle = "rgba(74, 222, 128, 0.5)";
    ctxO.fillRect(left, 0, 1, h);
    ctxO.fillRect(right - 1, 0, 1, h);

    const cx = hzToPx(props.modelValue, w);
    ctxO.beginPath();
    ctxO.strokeStyle = "rgba(74, 222, 128, 0.4)";
    ctxO.setLineDash([5, 5]);
    ctxO.moveTo(cx, 0);
    ctxO.lineTo(cx, h);
    ctxO.stroke();
    ctxO.setLineDash([]);
}

watch(
    () => [props.modelValue, props.bandwidth, zoom.value, panHz.value],
    () => {
        updateWorkerView();
        requestAnimationFrame(() => {
            drawOverlay();
            drawRuler();
        });
    },
    { immediate: true }
);

function setLatestData(data: Float32Array) {
    if (worker.value) {
        worker.value.postMessage({ type: 'fft', payload: data }, [data.buffer]);
    }
}
defineExpose({ setLatestData });

onMounted(() => {
    if (!containerRef.value || !canvasWaterfall.value || !canvasOverlay.value || !canvasRuler.value) return;

    const w = Math.max(1, containerRef.value.clientWidth);
    const totalH = containerRef.value.clientHeight;

    const waterfallH = Math.max(1, totalH - RULER_HEIGHT);

    canvasRuler.value.width = w;
    canvasRuler.value.height = RULER_HEIGHT;

    canvasWaterfall.value.width = w;
    canvasWaterfall.value.height = waterfallH;

    canvasOverlay.value.width = w;
    canvasOverlay.value.height = waterfallH;

    ctxW = canvasWaterfall.value.getContext("2d", { alpha: false });
    ctxO = canvasOverlay.value.getContext("2d");
    ctxR = canvasRuler.value.getContext("2d");

    worker.value = new WaterfallWorker();
    if (!worker.value) return;

    updateWorkerConfig();

    worker.value.postMessage({
        type: 'init',
        payload: {
            hwMinFreq: config.lo_freq - config.samp_rate / 2,
            hwMaxFreq: config.lo_freq + config.samp_rate / 2,
            viewMinFreq: viewMin.value,
            viewMaxFreq: viewMax.value,
            fftSize: config.fft_size,
            height: waterfallH, // Now safely > 0
            palette: props.palette
        }
    });

    worker.value.onmessage = (e) => {
        if (e.data.type === 'frame' && ctxW && canvasWaterfall.value) {
            ctxW.drawImage(e.data.bitmap, 0, 0, canvasWaterfall.value.width, canvasWaterfall.value.height);
            e.data.bitmap.close();
        }
    };

    const observer = new ResizeObserver(() => {
        if (!containerRef.value) return;

        // FIX 3: Apply same safety checks to ResizeObserver
        const nw = Math.max(1, containerRef.value.clientWidth);
        const nh = containerRef.value.clientHeight;
        const nWaterfallH = Math.max(1, nh - RULER_HEIGHT);

        canvasRuler.value!.width = nw;
        canvasWaterfall.value!.width = nw;
        canvasWaterfall.value!.height = nWaterfallH;
        canvasOverlay.value!.width = nw;
        canvasOverlay.value!.height = nWaterfallH;

        worker.value?.postMessage({ type: 'resize', payload: { height: nWaterfallH } });
        drawOverlay();
        drawRuler();
    });
    observer.observe(containerRef.value);
});

onUnmounted(() => {
    worker.value?.terminate();
});
</script>

<template>
    <div
        ref="containerRef"
        class="relative w-full h-full bg-black flex flex-col overflow-hidden select-none group border border-gray-700 rounded-lg"
        :style="{ cursor: hoverCursor }"
        @mousedown="onDown"
        @mouseleave="onUp"
        @mousemove="onMove"
        @mouseup="onUp"
        @wheel="onWheel"
    >
        <canvas
            ref="canvasRuler"
            class="w-full block z-20 shadow-sm pointer-events-none"
            :style="{ height: RULER_HEIGHT + 'px', flex: '0 0 ' + RULER_HEIGHT + 'px' }"
        />
        <div class="relative flex-1 w-full overflow-hidden bg-black pointer-events-none">
            <canvas ref="canvasWaterfall" class="absolute top-0 left-0 w-full h-full block" />
            <canvas ref="canvasOverlay" class="absolute top-0 left-0 w-full h-full z-10 block" />
        </div>
    </div>
</template>
