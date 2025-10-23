<script setup lang="ts">
import {ref, reactive} from 'vue';
import FrequencyControl from "&/components/FrequencyControl.vue";
import TabbedSettings from "&/components/TabbedSettings.vue";
import AppLayout from "&/layouts/AppLayout.vue";
import SignalContainer from "&/components/SignalContainer.vue";

// Reactive state for the main frequency slider
const frequency = ref(50);

// Reactive state for the tabbed settings panels
const audioSettings = reactive({
    volume: 70,
    sampleRate: null,
    filter: '',
});

const graphSettings = reactive({
    fftSize: null,
    refreshRate: null,
    colorScheme: '',
    yAxisScale: 50,
});

const physicsSettings = reactive({
    centerFreq: null,
    bandwidth: null,
    gain: 30,
    modulation: '',
});
</script>


<template>
    <AppLayout>
        <main class="p-4">
            <div class="max-w-6xl mx-auto space-y-6">
                <!-- Graph Placeholder -->
                <SignalContainer/>

                <!-- Slider Control -->
                <FrequencyControl v-model:frequency="frequency"/>

                <!-- Tabbed Settings -->
                <TabbedSettings v-model:audio-settings="audioSettings"
                                v-model:graph-settings="graphSettings"
                                v-model:physics-settings="physicsSettings"/>
            </div>
        </main>
    </AppLayout>

</template>
