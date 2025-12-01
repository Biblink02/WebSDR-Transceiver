<script setup lang="ts">
import { ref, watch } from 'vue';

const props = defineProps<{
    frequency: number;
    bandwidth: number;
}>();

const emit = defineEmits(['update:frequency', 'update:bandwidth']);

// TODO: Fetch these limits from backend configuration
const FREQ_LIMITS = { min: 7000000, max: 30000000 };
const BW_LIMITS = { min: 100, max: 10000 };

const localFreq = ref(props.frequency);
const localBw = ref(props.bandwidth);

const handleFreqChange = () => {
    if (localFreq.value < FREQ_LIMITS.min) localFreq.value = FREQ_LIMITS.min;
    if (localFreq.value > FREQ_LIMITS.max) localFreq.value = FREQ_LIMITS.max;
    emit('update:frequency', localFreq.value);
};

const handleBwChange = () => {
    if (localBw.value < BW_LIMITS.min) localBw.value = BW_LIMITS.min;
    if (localBw.value > BW_LIMITS.max) localBw.value = BW_LIMITS.max;
    emit('update:bandwidth', localBw.value);
};

watch(() => props.frequency, (val) => localFreq.value = val);
watch(() => props.bandwidth, (val) => localBw.value = val);
</script>

<template>
    <div class="w-full flex items-center justify-between px-6 py-3 bg-gray-900/90 backdrop-blur-sm border-t border-gray-700 text-white">

        <div class="flex flex-col gap-1">
            <label class="text-[10px] uppercase tracking-wider text-gray-400">Frequency (Hz)</label>
            <div class="flex items-center gap-2">
                <input
                    type="number"
                    v-model="localFreq"
                    @change="handleFreqChange"
                    :min="FREQ_LIMITS.min"
                    :max="FREQ_LIMITS.max"
                    class="bg-black border border-gray-600 rounded px-2 py-1 text-green-400 font-mono text-sm focus:outline-none focus:border-green-500 w-40"
                />
                <span class="text-xs text-gray-500">
          Range: {{ FREQ_LIMITS.min / 1e6 }} - {{ FREQ_LIMITS.max / 1e6 }} MHz
        </span>
            </div>
        </div>

        <div class="flex flex-col gap-1">
            <label class="text-[10px] uppercase tracking-wider text-gray-400">Bandwidth (Hz)</label>
            <input
                type="number"
                v-model="localBw"
                @change="handleBwChange"
                :min="BW_LIMITS.min"
                :max="BW_LIMITS.max"
                class="bg-black border border-gray-600 rounded px-2 py-1 text-green-400 font-mono text-sm focus:outline-none focus:border-green-500 w-32"
            />
        </div>

    </div>
</template>
