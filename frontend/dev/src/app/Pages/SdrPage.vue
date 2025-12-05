<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import AppLayout from '&/layouts/AppLayout.vue'
import SpectrogramComponent from '&/components/SpectrogramComponent.vue'
import FrequencyControl from '&/components/FrequencyControl.vue'
import SdrHeader from '&/components/SdrHeader.vue'

import { useSdrStore } from '@/stores/sdr.store'
import { useSdrWorker } from '@/composables/useSdrWorker'

const store = useSdrStore()
const { initWorker, toggleAudio } = useSdrWorker()
const spectrogramRef = ref<InstanceType<typeof SpectrogramComponent> | null>(null)

// Performance Optimization:
// Graphic data flows directly from Worker -> Composable -> Component
// bypassing Pinia/Vue Reactivity system to maintain 60FPS.
const onGraphicData = (data: Float32Array) => {
    spectrogramRef.value?.setLatestData(data)
}

onMounted(() => {
    initWorker(onGraphicData)
})
</script>

<template>
    <AppLayout>
        <Toast/>
        <div class="flex flex-col h-[calc(100vh-theme('spacing.24'))] max-w-7xl mx-auto w-full p-4 gap-4">

            <SdrHeader @toggle-audio="toggleAudio" />

            <div class="relative w-full h-[450px] shrink-0 bg-black rounded-lg overflow-hidden border border-gray-700 shadow-2xl flex flex-col group">

                <SpectrogramComponent
                    ref="spectrogramRef"
                    class="w-full h-full block"
                    v-model:model-value="store.tuneFreq"
                    v-model:bandwidth="store.bandwidth"
                />

                <div class="absolute bottom-0 left-0 w-full z-20 transition-transform duration-300 translate-y-full group-hover:translate-y-0 opacity-90">
                    <FrequencyControl
                        v-model:frequency="store.tuneFreq"
                        v-model:bandwidth="store.bandwidth"
                    />
                </div>

            </div>

        </div>
    </AppLayout>
</template>
