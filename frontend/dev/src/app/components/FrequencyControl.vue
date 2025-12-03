<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { getConfig } from "@/ConfigStore";

const props = defineProps<{
    frequency: number;
    bandwidth: number;
}>();

const emit = defineEmits(['update:frequency', 'update:bandwidth']);

// Use Config for limits
const config = getConfig();
const minFreq = computed(() => config.lo_freq - (config.samp_rate / 2));
const maxFreq = computed(() => config.lo_freq + (config.samp_rate / 2));

const BW_LIMITS = { min: 100, max: 200000 }; // Max 200k as per backend limit

const localFreq = ref(props.frequency);
const localBw = ref(props.bandwidth);

const handleFreqChange = () => {
    if (localFreq.value < minFreq.value) localFreq.value = minFreq.value;
    if (localFreq.value > maxFreq.value) localFreq.value = maxFreq.value;
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
                    :min="minFreq"
                    :max="maxFreq"
                    class="bg-black border border-gray-600 rounded px-2 py-1 text-green-400 font-mono text-sm focus:outline-none focus:border-green-500 w-40"
                />
                <span class="text-xs text-gray-500">
          Range: {{ (minFreq / 1e6).toFixed(2) }} - {{ (maxFreq / 1e6).toFixed(2) }} MHz
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
