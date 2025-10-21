<script setup lang="ts">
import { computed } from 'vue';
import Card from 'primevue/card';
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';
import Slider from 'primevue/slider';
import InputText from 'primevue/inputtext';
import Button from 'primevue/button';

// 1. Define the props as before.
const props = defineProps({
    audioSettings: { type: Object, required: true },
    graphSettings: { type: Object, required: true },
    physicsSettings: { type: Object, required: true },
});

// 2. Define the 'update' events for each prop to enable v-model.
const emit = defineEmits([
    'update:audioSettings',
    'update:graphSettings',
    'update:physicsSettings',
]);

// 3. Create a computed property for each settings object.
//    When an input inside the template changes a value (e.g., volume),
//    it triggers the 'set' function, which emits the entire updated object.
const localAudioSettings = computed({
    get: () => props.audioSettings,
    set: (value) => emit('update:audioSettings', value),
});

const localGraphSettings = computed({
    get: () => props.graphSettings,
    set: (value) => emit('update:graphSettings', value),
});

const localPhysicsSettings = computed({
    get: () => props.physicsSettings,
    set: (value) => emit('update:physicsSettings', value),
});
</script>

<template>
    <Card>
        <template #content>
            <TabView>
                <TabPanel header="Audio">
                    <div class="grid gap-4 mt-6">
                        <div class="space-y-2">
                            <label for="volume">Volume</label>
                            <Slider id="volume" v-model="localAudioSettings.volume" :max="100" :step="1" />
                        </div>
                        <div class="space-y-2">
                            <label for="sample-rate">Sample Rate (Hz)</label>
                            <InputText id="sample-rate" type="number" placeholder="48000" v-model="localAudioSettings.sampleRate" class="w-full" />
                        </div>
                        <div class="space-y-2">
                            <label for="audio-filter">Audio Filter</label>
                            <InputText id="audio-filter" placeholder="Low Pass" v-model="localAudioSettings.filter" class="w-full" />
                        </div>
                        <div class="flex gap-2">
                            <Button label="Reset" outlined class="flex-1" />
                            <Button label="Apply" class="flex-1" />
                        </div>
                    </div>
                </TabPanel>

                <TabPanel header="Graph">
                    <div class="grid gap-4 mt-6">
                        <div class="space-y-2">
                            <label for="fft-size">FFT Size</label>
                            <InputText id="fft-size" type="number" placeholder="2048" v-model="localGraphSettings.fftSize" class="w-full" />
                        </div>
                        <div class="space-y-2">
                            <label for="refresh-rate">Refresh Rate (ms)</label>
                            <InputText id="refresh-rate" type="number" placeholder="100" v-model="localGraphSettings.refreshRate" class="w-full" />
                        </div>
                        <div class="space-y-2">
                            <label for="color-scheme">Color Scheme</label>
                            <InputText id="color-scheme" placeholder="Spectrum" v-model="localGraphSettings.colorScheme" class="w-full" />
                        </div>
                        <div class="space-y-2">
                            <label for="y-axis-scale">Y-Axis Scale</label>
                            <Slider id="y-axis-scale" v-model="localGraphSettings.yAxisScale" :max="100" :step="1" />
                        </div>
                        <div class="flex gap-2">
                            <Button label="Reset" outlined class="flex-1" />
                            <Button label="Apply" class="flex-1" />
                        </div>
                    </div>
                </TabPanel>

                <TabPanel header="Physics">
                    <div class="grid gap-4 mt-6">
                        <div class="space-y-2">
                            <label for="center-freq">Center Frequency (MHz)</label>
                            <InputText id="center-freq" type="number" placeholder="100.0" v-model="localPhysicsSettings.centerFreq" class="w-full" />
                        </div>
                        <div class="space-y-2">
                            <label for="bandwidth">Bandwidth (kHz)</label>
                            <InputText id="bandwidth" type="number" placeholder="200" v-model="localPhysicsSettings.bandwidth" class="w-full" />
                        </div>
                        <div class="space-y-2">
                            <label for="gain">Gain (dB)</label>
                            <Slider id="gain" v-model="localPhysicsSettings.gain" :max="60" :step="1" />
                        </div>
                        <div class="space-y-2">
                            <label for="modulation">Modulation Type</label>
                            <InputText id="modulation" placeholder="FM" v-model="localPhysicsSettings.modulation" class="w-full" />
                        </div>
                        <div class="flex gap-2">
                            <Button label="Reset" outlined class="flex-1" />
                            <Button label="Apply" class="flex-1" />
                        </div>
                    </div>
                </TabPanel>
            </TabView>
        </template>
    </Card>
</template>
