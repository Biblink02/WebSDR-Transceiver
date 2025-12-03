<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import WaterfallWorker from '@/workers/waterfall.worker.ts?worker';
import { getConfig } from "@/ConfigStore";

const props = defineProps<{
    modelValue: number;
    bandwidth: number;
}>();

const emit = defineEmits(["update:modelValue", "update:bandwidth"]);

const config = getConfig();

const RULER_HEIGHT = 25;
const SELECTOR_HEIGHT = 60;
const MIN_BW = 500;
const MAX_BW = 200000;
const MIN_ZOOM = 1;
const MAX_ZOOM = 50;

const containerRef = ref<HTMLElement | null>(null);
const canvasWaterfall = ref<HTMLCanvasElement | null>(null);
const canvasOverlay = ref<HTMLCanvasElement | null>(null);

let ctxW: CanvasRenderingContext2D | null = null;
let ctxO: CanvasRenderingContext2D | null = null;

const worker = ref<Worker | null>(null);

const zoom = ref(1);
const panHz = ref(0);
let isHoveringTop = false;

const viewSpan = computed(() => config.samp_rate / zoom.value);
const viewMin = computed(() => config.lo_freq + panHz.value - viewSpan.value / 2);
const viewMax = computed(() => config.lo_freq + panHz.value + viewSpan.value / 2);

function clampPan() {
    const maxOffset = (config.samp_rate - viewSpan.value) / 2;
    if (panHz.value > maxOffset) panHz.value = maxOffset;
    if (panHz.value < -maxOffset) panHz.value = -maxOffset;
}

function hzToPx(hz: number, w: number): number {
    const range = viewMax.value - viewMin.value;
    return ((hz - viewMin.value) / range) * w;
}

function pxToHz(px: number, w: number): number {
    const range = viewMax.value - viewMin.value;
    return viewMin.value + (px / w) * range;
}

function getAdaptiveStep(visibleHz: number, widthPx: number): number {
    const minPxBetweenTicks = 100;
    const maxTicks = widthPx / minPxBetweenTicks;
    const rawStep = visibleHz / maxTicks;
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
    const residual = rawStep / magnitude;

    if (residual > 5) return 10 * magnitude;
    if (residual > 2) return 5 * magnitude;
    if (residual > 1) return 2 * magnitude;
    return magnitude;
}

function formatFreq(hz: number): string {
    return (hz / 1e6).toFixed(hz % 1000 !== 0 ? 4 : 3);
}

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

function drawOverlay() {
    if (!ctxO || !canvasOverlay.value) return;
    const w = canvasOverlay.value.width;
    const h = canvasOverlay.value.height;

    ctxO.clearRect(0, 0, w, h);

    const hzVisible = viewMax.value - viewMin.value;
    const cx = hzToPx(props.modelValue, w);
    const bwPx = (props.bandwidth / hzVisible) * w;
    const left = cx - bwPx / 2;
    const right = cx + bwPx / 2;

    const step = getAdaptiveStep(hzVisible, w);
    const startTick = Math.ceil(viewMin.value / step) * step;

    ctxO.beginPath();
    ctxO.fillStyle = "rgba(255, 255, 255, 0.8)";
    ctxO.strokeStyle = "rgba(255, 255, 255, 0.15)";
    ctxO.font = "11px monospace";
    ctxO.textAlign = "center";
    ctxO.lineWidth = 1;

    for (let f = startTick; f < viewMax.value; f += step) {
        const x = hzToPx(f, w);

        ctxO.moveTo(x, 0);
        ctxO.lineTo(x, 10);

        ctxO.moveTo(x, RULER_HEIGHT);
        ctxO.lineTo(x, h);

        ctxO.fillText(formatFreq(f), x, 22);
    }
    ctxO.stroke();

    ctxO.fillStyle = "rgba(255, 204, 0, 0.15)";
    ctxO.fillRect(left, 0, bwPx, h);

    ctxO.fillStyle = "rgba(255, 204, 0, 0.9)";
    ctxO.fillRect(left, 0, 1, h);
    ctxO.fillRect(right - 1, 0, 1, h);

    ctxO.fillRect(left - 2, 0, 5, SELECTOR_HEIGHT);
    ctxO.fillRect(right - 3, 0, 5, SELECTOR_HEIGHT);
    ctxO.fillRect(left, SELECTOR_HEIGHT - 2, bwPx, 2);

    ctxO.beginPath();
    ctxO.strokeStyle = "#ff3333";
    ctxO.lineWidth = 2;
    ctxO.moveTo(cx, 0);
    ctxO.lineTo(cx, SELECTOR_HEIGHT);
    ctxO.stroke();

    ctxO.beginPath();
    ctxO.setLineDash([4, 4]);
    ctxO.strokeStyle = "rgba(255, 51, 51, 0.6)";
    ctxO.lineWidth = 1;
    ctxO.moveTo(cx, SELECTOR_HEIGHT);
    ctxO.lineTo(cx, h);
    ctxO.stroke();
    ctxO.setLineDash([]);

    let infoX = cx + 8;
    if (infoX > w - 130) infoX = cx - 138;

    const infoY = SELECTOR_HEIGHT + 20;

    ctxO.fillStyle = "rgba(0, 0, 0, 0.6)";
    ctxO.fillRect(infoX - 4, infoY - 14, 130, 32);

    ctxO.textAlign = "left";
    ctxO.fillStyle = "#fff";
    ctxO.font = "bold 12px monospace";
    ctxO.fillText(`${(props.modelValue / 1e6).toFixed(5)} MHz`, infoX, infoY);

    ctxO.fillStyle = "#fbbf24";
    ctxO.font = "11px monospace";
    ctxO.fillText(`BW: ${(props.bandwidth / 1e3).toFixed(1)} kHz`, infoX, infoY + 14);

    ctxO.textAlign = "right";
    ctxO.fillStyle = zoom.value > 1.01 ? "#4ade80" : "rgba(255,255,255,0.3)";
    ctxO.fillText(`${zoom.value.toFixed(1)}x`, w - 6, 16);
}

watch(
    () => [props.modelValue, props.bandwidth, zoom.value, panHz.value],
    () => {
        updateWorkerView();
        requestAnimationFrame(drawOverlay);
    },
    { immediate: true }
);

function setLatestData(data: Float32Array) {
    if (worker.value) {
        worker.value.postMessage({ type: 'fft', payload: data }, [data.buffer]);
    }
}
defineExpose({ setLatestData });

let dragging = false;
let startX = 0;
let startFreq = 0;
let startPan = 0;
let dragMode: 'MOVE' | 'RESIZE_L' | 'RESIZE_R' | 'PAN' | null = null;

function getMouseX(e: MouseEvent) {
    const r = canvasOverlay.value!.getBoundingClientRect();
    return (e.clientX - r.left) * (canvasOverlay.value!.width / r.width);
}

function getMouseY(e: MouseEvent) {
    const r = canvasOverlay.value!.getBoundingClientRect();
    return (e.clientY - r.top) * (canvasOverlay.value!.height / r.height);
}

function onDown(e: MouseEvent) {
    if (!canvasOverlay.value) return;
    const x = getMouseX(e);
    const y = getMouseY(e);
    const w = canvasOverlay.value.width;

    const cx = hzToPx(props.modelValue, w);
    const hzVisible = viewMax.value - viewMin.value;
    const bwPx = (props.bandwidth / hzVisible) * w;
    const left = cx - bwPx / 2;
    const right = cx + bwPx / 2;
    const tol = 12;

    dragging = true;
    startX = x;
    startFreq = props.modelValue;
    startPan = panHz.value;

    if (y <= SELECTOR_HEIGHT) {
        if (Math.abs(x - left) < tol) dragMode = 'RESIZE_L';
        else if (Math.abs(x - right) < tol) dragMode = 'RESIZE_R';
        else dragMode = 'MOVE';
    } else {
        if (zoom.value > 1.01) {
            dragMode = 'PAN';
            canvasOverlay.value.style.cursor = "grabbing";
        } else {
            dragging = false;
        }
    }
}

function onMove(e: MouseEvent) {
    if (!canvasOverlay.value) return;
    const x = getMouseX(e);
    const y = getMouseY(e);
    const w = canvasOverlay.value.width;

    if (!dragging) {
        if (y > SELECTOR_HEIGHT) {
            isHoveringTop = false;
            canvasOverlay.value.style.cursor = zoom.value > 1.01 ? "grab" : "default";
            return;
        }

        isHoveringTop = true;
        const cx = hzToPx(props.modelValue, w);
        const hzVisible = viewMax.value - viewMin.value;
        const bwPx = (props.bandwidth / hzVisible) * w;
        const left = cx - bwPx / 2;
        const right = cx + bwPx / 2;
        const tol = 12;

        if (Math.abs(x - left) < tol || Math.abs(x - right) < tol) canvasOverlay.value.style.cursor = "ew-resize";
        else if (x > left && x < right) canvasOverlay.value.style.cursor = "move";
        else canvasOverlay.value.style.cursor = "crosshair";
        return;
    }

    const dx = x - startX;
    const hzPerPx = (viewMax.value - viewMin.value) / w;

    if (dragMode === 'MOVE') {
        let f = startFreq + dx * hzPerPx;
        const minHw = config.lo_freq - config.samp_rate / 2;
        const maxHw = config.lo_freq + config.samp_rate / 2;
        f = Math.max(minHw, Math.min(maxHw, f));
        emit("update:modelValue", f);
    }
    else if (dragMode === 'RESIZE_L' || dragMode === 'RESIZE_R') {
        const currentHz = pxToHz(x, w);
        let bw = Math.abs(currentHz - props.modelValue) * 2;
        bw = Math.max(MIN_BW, Math.min(MAX_BW, bw));
        emit("update:bandwidth", bw);
    }
    else if (dragMode === 'PAN') {
        panHz.value = startPan - (dx * hzPerPx);
        clampPan();
    }
}

function onUp() {
    dragging = false;
    dragMode = null;
    if (canvasOverlay.value) {
        canvasOverlay.value.style.cursor = isHoveringTop ? "crosshair" : "default";
    }
}

function onWheel(e: WheelEvent) {
    e.preventDefault();
    if (e.shiftKey) {
        let bw = props.bandwidth + (e.deltaY > 0 ? -200 : 200);
        bw = Math.max(MIN_BW, Math.min(MAX_BW, bw));
        emit("update:bandwidth", bw);
        return;
    }
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    let z = zoom.value * factor;
    zoom.value = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, z));
    clampPan();
}

onMounted(() => {
    if (!containerRef.value || !canvasWaterfall.value || !canvasOverlay.value) return;

    const w = containerRef.value.clientWidth;
    const h = containerRef.value.clientHeight;

    canvasWaterfall.value.width = w;
    canvasWaterfall.value.height = h;
    canvasOverlay.value.width = w;
    canvasOverlay.value.height = h;

    ctxW = canvasWaterfall.value.getContext("2d", { alpha: false });
    ctxO = canvasOverlay.value.getContext("2d");

    worker.value = new WaterfallWorker();
    if (!worker.value) return;

    worker.value.postMessage({ type: 'config', payload: config });

    worker.value.postMessage({
        type: 'init',
        payload: {
            hwMinFreq: config.lo_freq - config.samp_rate / 2,
            hwMaxFreq: config.lo_freq + config.samp_rate / 2,
            viewMinFreq: viewMin.value,
            viewMaxFreq: viewMax.value,
            fftSize: config.fft_size,
            height: h
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
        const nw = containerRef.value.clientWidth;
        const nh = containerRef.value.clientHeight;

        canvasWaterfall.value!.width = nw;
        canvasWaterfall.value!.height = nh;
        canvasOverlay.value!.width = nw;
        canvasOverlay.value!.height = nh;

        worker.value?.postMessage({ type: 'resize', payload: { height: nh } });
        drawOverlay();
    });
    observer.observe(containerRef.value);
});

onUnmounted(() => {
    worker.value?.terminate();
});
</script>

<template>
    <div ref="containerRef" class="relative w-full h-full bg-black overflow-hidden select-none group">
        <canvas ref="canvasWaterfall" class="absolute top-0 left-0 w-full h-full block" />

        <canvas ref="canvasOverlay"
                class="absolute top-0 left-0 w-full h-full z-10 block cursor-crosshair"
                @mousedown="onDown"
                @mousemove="onMove"
                @mouseup="onUp"
                @mouseleave="onUp"
                @wheel="onWheel"
        />
    </div>
</template>
