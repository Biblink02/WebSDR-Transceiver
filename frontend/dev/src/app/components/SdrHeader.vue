<script lang="ts" setup>
import {useSdrStore} from '@/stores/sdr.store'
import Button from 'primevue/button';
import Slider from 'primevue/slider';

const store = useSdrStore()
const emit = defineEmits(['toggle-audio'])
</script>

<template>
    <div
        class="flex flex-wrap justify-between items-center bg-gray-900/90 p-4 rounded-lg backdrop-blur border border-gray-700 shadow-lg shrink-0">
        <div>
            <h1 class="text-xl font-bold text-white tracking-wide">SDR CONSOLE</h1>
            <div class="flex items-center gap-3 text-xs font-mono mt-1">
                <span :class="store.isConnected ? 'text-green-400' : 'text-red-500'">
                  {{ store.statusText }}
                </span>
                <span v-if="store.workerStatus === 'LISTENING'" class="text-blue-400 animate-pulse">
                  ● AUDIO ACTIVE ({{ store.assignedWorkerId }})
                </span>
                <span v-if="store.workerStatus === 'FULL'" class="text-yellow-500">
                  ⚠ SYSTEM BUSY
                </span>
            </div>
        </div>

        <div class="flex items-center gap-6">
            <div class="flex items-center gap-3 bg-black/30 px-4 py-2 rounded-lg border border-gray-700 h-10">
                <i v-if="store.volume>0" class="pi pi-volume-up text-gray-400 text-sm cursor-pointer"
                   @click="store.volume=0"></i>
                <i v-else class="pi pi-volume-off text-gray-400 text-sm cursor-pointer"
                   @click="store.volume=50"></i>
                <div class="w-24 flex items-center">
                    <Slider
                        v-model="store.volume"
                        :min="0"
                        :max="100"
                        class="w-full"
                    />
                </div>
            </div>

            <Button
                :label="store.workerStatus === 'LISTENING' ? 'STOP AUDIO' : 'START AUDIO'"
                :icon="store.workerStatus === 'LISTENING' ? 'pi pi-stop' : 'pi pi-play'"
                :severity="store.workerStatus === 'LISTENING' ? 'danger' : 'info'"
                :disabled="!store.isConnected || store.workerStatus === 'FULL'"
                class="!rounded-lg !font-bold"
                raised
                @click="emit('toggle-audio')"
            />
        </div>
    </div>
</template>
