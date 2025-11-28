<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps({
    frequency: {
        type: Number,
        required: true,
    },
});

const emit = defineEmits(['update:frequency']);

const frequencyValue = computed({
    get: () => props.frequency,
    set: (newValue) => emit('update:frequency', newValue),
});
</script>

<template>
    <Card>
        <template #content>
            <div class="space-y-4">
                <div class="flex items-center justify-between">
                    <label for="frequency-slider" class="text-sm font-medium">
                        Frequency Control
                    </label>
                    <span class="text-sm">{{ frequencyValue }} MHz</span>
                </div>
                <Slider v-model="frequencyValue" id="frequency-slider" :max="100" :step="1" class="w-full" />
            </div>
        </template>
    </Card>
</template>
