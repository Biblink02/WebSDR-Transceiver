<script lang="ts" setup>
import { computed, ref, watch } from 'vue';
import { useSdrStore } from "@/stores/sdr.store";

const props = defineProps<{
    frequency: number;
    bandwidth: number;
}>();

const emit = defineEmits(['update:frequency', 'update:bandwidth']);

const store = useSdrStore();
const config = store.settings;

const minFreq = computed(() => config.lo_freq - (config.samp_rate / 2));
const maxFreq = computed(() => config.lo_freq + (config.samp_rate / 2));

const BW_LIMITS = { min: 100, max: config.max_bw_limit };

const localFreq = ref(props.frequency);
const localBw = ref(props.bandwidth);

const handleFreqChange = () => {
    let val = Math.round(localFreq.value);

    if (val < minFreq.value) val = minFreq.value;
    if (val > maxFreq.value) val = maxFreq.value;

    if (localFreq.value !== val) localFreq.value = val;

    emit('update:frequency', val);
};

const handleBwChange = () => {
    let val = Math.round(localBw.value);

    if (val < BW_LIMITS.min) val = BW_LIMITS.min;
    if (val > BW_LIMITS.max) val = BW_LIMITS.max;

    if (localBw.value !== val) localBw.value = val;

    emit('update:bandwidth', val);
};

watch(() => props.frequency, (val) => localFreq.value = Math.round(val));
watch(() => props.bandwidth, (val) => localBw.value = Math.round(val));
</script>

<template>
    <div class="w-full flex items-center justify-between px-6 py-3 bg-gray-900/90 backdrop-blur-sm border-t border-gray-700 text-white">

        <div class="flex flex-col gap-1">
            <label class="text-[10px] uppercase tracking-wider text-gray-400">Frequency (Hz)</label>
            <div class="flex items-center gap-2">
                <input
                    type="number"
                    step="1"
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
                step="1"
                v-model="localBw"
                @change="handleBwChange"
                :min="BW_LIMITS.min"
                :max="BW_LIMITS.max"
                class="bg-black border border-gray-600 rounded px-2 py-1 text-green-400 font-mono text-sm focus:outline-none focus:border-green-500 w-32"
            />
        </div>

    </div>
</template>
