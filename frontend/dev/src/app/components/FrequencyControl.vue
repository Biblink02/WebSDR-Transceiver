<script lang="ts" setup>
import { computed, ref, watch } from "vue";
import { useSdrStore } from "@/stores/sdr.store";
import { calculateDisplayFrequency, calculateIFFrequency } from "@/Utils";

const props = defineProps<{
    frequency: number;
    bandwidth: number;
}>();

const emit = defineEmits(["update:frequency", "update:bandwidth"]);

const store = useSdrStore();
const config = store.settings;

const minFreqRF = computed(() => calculateDisplayFrequency(config.lo_freq - config.samp_rate / 2));
const maxFreqRF = computed(() => calculateDisplayFrequency(config.lo_freq + config.samp_rate / 2));

const BW_LIMITS = { min: config.min_bw_limit, max: config.max_bw_limit };

const localFreq = ref(calculateDisplayFrequency(props.frequency));
const localBw = ref(props.bandwidth);

const handleFreqChange = () => {
    let val = Math.round(localFreq.value);
    if (val < minFreqRF.value) val = minFreqRF.value;
    if (val > maxFreqRF.value) val = maxFreqRF.value;
    if (localFreq.value !== val) localFreq.value = val;
    emit("update:frequency", calculateIFFrequency(val));
};

const handleBwChange = () => {
    let val = Math.round(localBw.value);
    if (val < BW_LIMITS.min) val = BW_LIMITS.min;
    if (val > BW_LIMITS.max) val = BW_LIMITS.max;
    if (localBw.value !== val) localBw.value = val;
    emit("update:bandwidth", val);
};

watch(() => props.frequency, val => {
    localFreq.value = Math.round(calculateDisplayFrequency(val));
});

watch(() => props.bandwidth, val => {
    localBw.value = Math.round(val);
});
</script>

<template>
    <div class="w-full flex items-center justify-between px-6 py-3 bg-gray-900/90 backdrop-blur-sm border-t border-gray-700 text-white">
        <div class="flex flex-col gap-1">
            <label class="text-xs uppercase tracking-wider text-gray-400">Frequency (RF)</label>
            <div class="flex items-center gap-2">
                <input
                    type="number"
                    step="1"
                    v-model="localFreq"
                    @change="handleFreqChange"
                    :min="minFreqRF"
                    :max="maxFreqRF"
                    class="bg-black border border-gray-600 rounded px-2 py-1 text-green-400 font-mono text-sm focus:outline-none focus:border-green-500 w-40"
                />
                <span class="text-xs text-gray-500">
                    Range: {{ (minFreqRF / 1e6).toFixed(3) }} - {{ (maxFreqRF / 1e6).toFixed(3) }} MHz
                </span>
            </div>
        </div>
    </div>
</template>
