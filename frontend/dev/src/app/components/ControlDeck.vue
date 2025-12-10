<script lang="ts" setup>
import { computed } from 'vue';
import { useSdrStore } from "@/stores/sdr.store";
import { calculateDisplayFrequency, calculateIFFrequency } from "@/Utils";
import InputNumber from 'primevue/inputnumber';
import Slider from 'primevue/slider';
import Select from 'primevue/select';

const props = defineProps<{
    frequency: number;
    bandwidth: number;
    contrast: number;
    brightness: number;
    palette: string;
}>();

const emit = defineEmits([
    'update:frequency',
    'update:bandwidth',
    'update:contrast',
    'update:brightness',
    'update:palette'
]);

const store = useSdrStore();
const config = store.settings;

const paletteOptions = [
    { label: 'Classic', value: 'classic' },
    { label: 'Inferno', value: 'inferno' },
    { label: 'Ocean', value: 'ocean' },
    { label: 'Greyscale', value: 'greyscale' },
];

// Calculate limits in RF domain for the input field
const minFreqRF = calculateDisplayFrequency(config.lo_freq - (config.samp_rate / 2));
const maxFreqRF = calculateDisplayFrequency(config.lo_freq + (config.samp_rate / 2));

// Label for display
const rfFreqMHz = computed(() => (calculateDisplayFrequency(props.frequency) / 1e6).toFixed(4));

// BRIDGE: User sees RF, System gets IF
const localFreq = computed({
    get: () => Math.round(calculateDisplayFrequency(props.frequency)),
    set: (val) => {
        if (typeof val === 'number') {
            emit('update:frequency', calculateIFFrequency(val));
        }
    }
});

const localBw = computed({
    get: () => Math.round(props.bandwidth),
    set: (val) => emit('update:bandwidth', val as number)
});

const localContrast = computed({
    get: () => props.contrast,
    set: (val) => emit('update:contrast', val)
});

const localBrightness = computed({
    get: () => props.brightness,
    set: (val) => emit('update:brightness', val)
});

const localPalette = computed({
    get: () => props.palette,
    set: (val) => emit('update:palette', val)
});
</script>

<template>
    <div class="bg-gray-900 p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 text-white items-end">

        <div class="flex flex-col gap-2 border-r border-gray-700 pr-6">
            <div class="flex justify-between items-end">
                <label class="text-xs uppercase tracking-widest text-blue-400 font-bold">Frequency</label>
                <span class="text-xs font-mono text-gray-400">{{ rfFreqMHz }} MHz</span>
            </div>
            <InputNumber
                v-model="localFreq"
                :min="minFreqRF"
                :max="maxFreqRF"
                :useGrouping="true"
                fluid
                inputClass="font-mono text-green-400 font-bold !bg-black/40 !border-gray-600 focus:!border-green-500 !rounded-lg h-12"
                suffix=" Hz"
            />
        </div>

        <div class="flex flex-col gap-2 border-r border-gray-700 pr-6">
            <label class="text-xs uppercase tracking-widest text-blue-400 font-bold">Bandwidth</label>
            <InputNumber
                v-model="localBw"
                :min="config.min_bw_limit"
                :max="config.max_bw_limit"
                :step="100"
                fluid
                inputClass="font-mono text-yellow-400 font-bold !bg-black/40 !border-gray-600 focus:!border-yellow-500 !rounded-lg h-12"
                suffix=" Hz"
            />
        </div>

        <div class="flex flex-col gap-2">
            <label class="text-xs uppercase tracking-wider text-purple-400 font-bold">Palette</label>
            <Select
                v-model="localPalette"
                :options="paletteOptions"
                optionLabel="label"
                optionValue="value"
                fluid
                class="!bg-gray-800 !border-gray-600 !rounded-lg h-12 flex items-center"
            />
        </div>

        <div class="flex flex-col gap-2">
            <div class="flex justify-between">
                <label class="text-xs uppercase tracking-wider text-gray-400 font-bold">Gain</label>
                <span class="text-xs text-gray-300 font-mono">{{ brightness }} dB</span>
            </div>
            <div class="h-12 flex items-center rounded-lg px-3 border border-transparent">
                <Slider
                    v-model="localBrightness"
                    :min="-40"
                    :max="40"
                    class="w-full"
                />
            </div>
        </div>

        <div class="flex flex-col gap-2">
            <div class="flex justify-between">
                <label class="text-xs uppercase tracking-wider text-gray-400 font-bold">Range</label>
                <span class="text-xs text-gray-300 font-mono">{{ contrast }} dB</span>
            </div>
            <div class="h-12 flex items-center rounded-lg px-3 border border-transparent">
                <Slider
                    v-model="localContrast"
                    :min="10"
                    :max="100"
                    class="w-full"
                />
            </div>
        </div>

    </div>
</template>

<style scoped>

</style>
