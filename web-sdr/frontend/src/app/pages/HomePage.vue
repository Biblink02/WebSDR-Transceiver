<script setup lang="ts">
import { ref, reactive } from 'vue';
import SdrPage from "&/pages/sdr/SdrPage.vue";
import NavbarComponent from "&/components/NavbarComponent.vue";

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
    <div class="min-h-screen ">

        <NavbarComponent></NavbarComponent>
        <!-- Main Content -->
        <main class="p-4">
            <div class="max-w-6xl mx-auto space-y-6">
                <!-- Graph Placeholder -->
                <SdrPage/>

                <!-- Slider Control -->
                <Card>
                    <template #content>
                        <div class="space-y-4">
                            <div class="flex items-center justify-between">
                                <label for="frequency-slider" class="text-sm font-medium">
                                    Frequency Control
                                </label>
                                <span class="text-sm">{{ frequency }} MHz</span>
                            </div>
                            <Slider v-model="frequency" id="frequency-slider" :max="100" :step="1" class="w-full" />
                        </div>
                    </template>
                </Card>

                <!-- Tabbed Settings -->
                <Card>
                    <template #content>
                        <TabView>
                            <TabPanel header="Audio">
                                <div class="grid gap-4 mt-6">
                                    <div class="space-y-2">
                                        <label for="volume">Volume</label>
                                        <Slider id="volume" v-model="audioSettings.volume" :max="100" :step="1" />
                                    </div>
                                    <div class="space-y-2">
                                        <label for="sample-rate">Sample Rate (Hz)</label>
                                        <InputText id="sample-rate" type="number" placeholder="48000" v-model="audioSettings.sampleRate" class="w-full" />
                                    </div>
                                    <div class="space-y-2">
                                        <label for="audio-filter">Audio Filter</label>
                                        <InputText id="audio-filter" placeholder="Low Pass" v-model="audioSettings.filter" class="w-full" />
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
                                        <InputText id="fft-size" type="number" placeholder="2048" v-model="graphSettings.fftSize" class="w-full" />
                                    </div>
                                    <div class="space-y-2">
                                        <label for="refresh-rate">Refresh Rate (ms)</label>
                                        <InputText id="refresh-rate" type="number" placeholder="100" v-model="graphSettings.refreshRate" class="w-full" />
                                    </div>
                                    <div class="space-y-2">
                                        <label for="color-scheme">Color Scheme</label>
                                        <InputText id="color-scheme" placeholder="Spectrum" v-model="graphSettings.colorScheme" class="w-full" />
                                    </div>
                                    <div class="space-y-2">
                                        <label for="y-axis-scale">Y-Axis Scale</label>
                                        <Slider id="y-axis-scale" v-model="graphSettings.yAxisScale" :max="100" :step="1" />
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
                                        <InputText id="center-freq" type="number" placeholder="100.0" v-model="physicsSettings.centerFreq" class="w-full" />
                                    </div>
                                    <div class="space-y-2">
                                        <label for="bandwidth">Bandwidth (kHz)</label>
                                        <InputText id="bandwidth" type="number" placeholder="200" v-model="physicsSettings.bandwidth" class="w-full" />
                                    </div>
                                    <div class="space-y-2">
                                        <label for="gain">Gain (dB)</label>
                                        <Slider id="gain" v-model="physicsSettings.gain" :max="60" :step="1" />
                                    </div>
                                    <div class="space-y-2">
                                        <label for="modulation">Modulation Type</label>
                                        <InputText id="modulation" placeholder="FM" v-model="physicsSettings.modulation" class="w-full" />
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
            </div>
        </main>
    </div>
</template>
