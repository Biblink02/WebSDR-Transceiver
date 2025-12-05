<script lang="ts" setup>
import { onMounted, onUnmounted, ref, watch } from "vue";
import WaterfallWorker from '@/workers/waterfall.worker.ts?worker';
import { useSdrStore } from "@/stores/sdr.store"; // Use Store
import { useSpectrogramInteraction } from "@/composables/useSpectrogramInteraction";

const props = defineProps<{
    modelValue: number;
    bandwidth: number;
}>();

const emit = defineEmits(["update:modelValue", "update:bandwidth"]);

const store = useSdrStore();
const config = store.settings; // Access settings from store

const containerRef = ref<HTMLElement | null>(null);
const canvasWaterfall = ref<HTMLCanvasElement | null>(null);
const canvasOverlay = ref<HTMLCanvasElement | null>(null);

let ctxW: CanvasRenderingContext2D | null = null;
let ctxO: CanvasRenderingContext2D | null = null;
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
} = useSpectrogramInteraction(config, () => props, emit, () => canvasOverlay.value);

const RULER_HEIGHT = 25;
const SELECTOR_HEIGHT = 60;

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

    // Grid/Ticks
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

    // Selector
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

    // Info Box
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

    worker.value.postMessage({
        type: 'config',
        payload: {
            gain_attack: config.gain_attack,
            gain_release: config.gain_release,
            range_db: config.range_db
        }
    });

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
        <canvas
            ref="canvasOverlay"
            class="absolute top-0 left-0 w-full h-full z-10 block"
            :style="{ cursor: hoverCursor }"
            @mousedown="onDown"
            @mouseleave="onUp"
            @mousemove="onMove"
            @mouseup="onUp"
            @wheel="onWheel"
        />
    </div>
</template>
