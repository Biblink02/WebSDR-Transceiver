<script setup lang="ts">
import { computed } from 'vue';
import Card from 'primevue/card';       // Assuming PrimeVue components
import Slider from 'primevue/slider';   // Assuming PrimeVue components

// 1. Define the props the component accepts. 'frequency' is the value passed down.
const props = defineProps({
    frequency: {
        type: Number,
        required: true,
    },
});

// 2. Define the event it can emit. 'update:frequency' is the convention for v-model:frequency.
const emit = defineEmits(['update:frequency']);

// 3. Create a computed property to handle getting and setting the value.
//    This avoids mutating the prop directly.
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
