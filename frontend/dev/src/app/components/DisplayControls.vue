<script lang="ts" setup>
const props = defineProps<{
    contrast: number;   // range_db
    brightness: number; // gain offset
}>();

const emit = defineEmits(['update:contrast', 'update:brightness']);

const onContrastChange = (e: Event) => {
    emit('update:contrast', parseFloat((e.target as HTMLInputElement).value));
};

const onBrightnessChange = (e: Event) => {
    emit('update:brightness', parseFloat((e.target as HTMLInputElement).value));
};
</script>

<template>
    <div class="w-full flex items-center gap-8 px-6 py-3 bg-gray-900/95 backdrop-blur border-t border-gray-700 text-white shadow-xl">

        <div class="flex flex-col gap-1 flex-1">
            <div class="flex justify-between">
                <label class="text-xs uppercase tracking-wider text-gray-400 font-bold">Brightness (Gain)</label>
                <span class="text-xs text-green-400 font-mono">{{ brightness > 0 ? '+' : ''}}{{ brightness }} dB</span>
            </div>
            <input
                type="range"
                min="-30" max="30" step="1"
                :value="brightness"
                @input="onBrightnessChange"
                class="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
            />
        </div>

        <div class="flex flex-col gap-1 flex-1">
            <div class="flex justify-between">
                <label class="text-xs uppercase tracking-wider text-gray-400 font-bold">Contrast (Range)</label>
                <span class="text-xs text-yellow-400 font-mono">{{ contrast }} dB</span>
            </div>
            <input
                type="range"
                min="10" max="80" step="1"
                :value="contrast"
                @input="onContrastChange"
                class="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
            />
        </div>

    </div>
</template>
