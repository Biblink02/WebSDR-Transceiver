<script lang="ts" setup>
import {computed, ref} from 'vue';

const props = defineProps({
    audioSettings: {type: Object, required: true},
    graphSettings: {type: Object, required: true},
    physicsSettings: {type: Object, required: true},
});

const emit = defineEmits([
    'update:audioSettings',
    'update:graphSettings',
    'update:physicsSettings',
]);

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

const activeTab = ref('audio'); // Default to the first tab
</script>

<template>
    <Card>
        <template #content>
            <Tabs v-model:value="activeTab">
                <TabList>
                    <Tab value="audio">Audio</Tab>
                    <Tab value="graph">Graph</Tab>
                    <Tab value="physics">Physics</Tab>
                </TabList>

                <TabPanels>
                    <TabPanel value="audio">
                        <div class="grid gap-4 mt-6">
                            <div class="space-y-2">
                                <label for="volume">Volume</label>
                                <Slider id="volume" v-model="localAudioSettings.volume" :max="100" :step="1"/>
                            </div>
                            <div class="space-y-2">
                                <label for="sample-rate">Sample Rate (Hz)</label>
                                <InputText id="sample-rate" v-model="localAudioSettings.sampleRate" class="w-full"
                                           placeholder="48000" type="number"/>
                            </div>
                            <div class="space-y-2">
                                <label for="audio-filter">Audio Filter</label>
                                <InputText id="audio-filter" v-model="localAudioSettings.filter" class="w-full"
                                           placeholder="Low Pass"/>
                            </div>
                            <div class="flex gap-2">
                                <Button class="flex-1" label="Reset" outlined/>
                                <Button class="flex-1" label="Apply"/>
                            </div>
                        </div>
                    </TabPanel>

                    <TabPanel value="graph">
                        <div class="grid gap-4 mt-6">
                            <div class="space-y-2">
                                <label for="fft-size">FFT Size</label>
                                <InputText id="fft-size" v-model="localGraphSettings.fftSize" class="w-full"
                                           placeholder="2048" type="number"/>
                            </div>
                            <div class="space-y-2">
                                <label for="refresh-rate">Refresh Rate (ms)</label>
                                <InputText id="refresh-rate" v-model="localGraphSettings.refreshRate" class="w-full"
                                           placeholder="100" type="number"/>
                            </div>
                            <div class="space-y-2">
                                <label for="color-scheme">Color Scheme</label>
                                <InputText id="color-scheme" v-model="localGraphSettings.colorScheme"
                                           class="w-full" placeholder="Spectrum"/>
                            </div>
                            <div class="space-y-2">
                                <label for="y-axis-scale">Y-Axis Scale</label>
                                <Slider id="y-axis-scale" v-model="localGraphSettings.yAxisScale" :max="100" :step="1"/>
                            </div>
                            <div class="flex gap-2">
                                <Button class="flex-1" label="Reset" outlined/>
                                <Button class="flex-1" label="Apply"/>
                            </div>
                        </div>
                    </TabPanel>

                    <TabPanel value="physics">
                        <div class="grid gap-4 mt-6">
                            <div class="space-y-2">
                                <label for="center-freq">Center Frequency (MHz)</label>
                                <InputText id="center-freq" v-model="localPhysicsSettings.centerFreq" class="w-full"
                                           placeholder="100.0" type="number"/>
                            </div>
                            <div class="space-y-2">
                                <label for="bandwidth">Bandwidth (kHz)</label>
                                <InputText id="bandwidth" v-model="localPhysicsSettings.bandwidth" class="w-full"
                                           placeholder="200" type="number"/>
                            </div>
                            <div class="space-y-2">
                                <label for="gain">Gain (dB)</label>
                                <Slider id="gain" v-model="localPhysicsSettings.gain" :max="60" :step="1"/>
                            </div>
                            <div class="space-y-2">
                                <label for="modulation">Modulation Type</label>
                                <InputText id="modulation" v-model="localPhysicsSettings.modulation" class="w-full"
                                           placeholder="FM"/>
                            </div>
                            <div class="flex gap-2">
                                <Button class="flex-1" label="Reset" outlined/>
                                <Button class="flex-1" label="Apply"/>
                            </div>
                        </div>
                    </TabPanel>
                </TabPanels>
            </Tabs>
        </template>
    </Card>
</template>
