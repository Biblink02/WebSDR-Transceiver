<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import AppLayout from '&/layouts/AppLayout.vue'
import SpectrogramComponent from '&/components/SpectrogramComponent.vue'
import ControlDeck from '&/components/ControlDeck.vue'
import SdrHeader from '&/components/SdrHeader.vue'

import { useSdrStore } from '@/stores/sdr.store'
import { useSdrWorker } from '@/composables/useSdrWorker'

const store = useSdrStore()
const { initWorker, toggleAudio, toggleConnection } = useSdrWorker()
const spectrogramRef = ref<InstanceType<typeof SpectrogramComponent> | null>(null)

const range = ref(50);
const gain = ref(-10);

const onGraphicData = (data: Float32Array) => {
    spectrogramRef.value?.setLatestData(data)
}

onMounted(() => {
    if (store.settings.range_db) {
        range.value = store.settings.range_db;
    }
    if (store.settings.gain_db) {
        gain.value = store.settings.gain_db;
    }
    initWorker(onGraphicData)
})
</script>

<template>
    <AppLayout>
        <Toast/>

        <div class="flex flex-col h-[calc(100vh-6rem)] max-w-7xl mx-auto w-full p-4 gap-4">

            <SdrHeader
                @toggle-audio="toggleAudio"
                @toggle-connection="toggleConnection"
            />

            <div class="flex-1 min-h-0 relative rounded-lg border border-gray-700 shadow-2xl overflow-hidden bg-black">
                <SpectrogramComponent
                    ref="spectrogramRef"
                    class="w-full h-full block"
                    v-model:model-value="store.tuneFreq"
                    v-model:bandwidth="store.bandwidth"
                    :range="range"
                    :gain="gain"
                    :palette="store.palette"
                />
            </div>

            <div class="rounded-lg border border-gray-700 shadow-2xl overflow-hidden">
                <ControlDeck
                    v-model:frequency="store.tuneFreq"
                    v-model:bandwidth="store.bandwidth"
                    v-model:range="range"
                    v-model:gain="gain"
                    v-model:palette="store.palette"
                />
            </div>

        </div>
    </AppLayout>
</template>
