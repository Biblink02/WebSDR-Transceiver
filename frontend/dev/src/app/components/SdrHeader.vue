<script lang="ts" setup>
import {useSdrStore} from '@/stores/sdr.store'

const store = useSdrStore()
const emit = defineEmits(['toggle-audio'])

const onVolumeChange = (event: Event) => {
    const target = event.target as HTMLInputElement
    store.setVolume(Number(target.value))
}
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
            <div class="flex items-center gap-3 bg-black/30 px-3 py-2 rounded-full border border-gray-700">
                <span class="text-gray-400 text-xs font-bold uppercase">Vol</span>
                <input
                    :value="store.volume"
                    class="w-24 h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    max="100"
                    min="0"
                    type="range"
                    @input="onVolumeChange"
                />
            </div>

            <button
                :class="store.workerStatus === 'LISTENING'
          ? 'bg-red-600/90 hover:bg-red-600 text-white border-red-500'
          : 'bg-blue-600/90 hover:bg-blue-600 text-white border-blue-500 disabled:opacity-50 disabled:grayscale'"
                :disabled="!store.isConnected || store.workerStatus === 'FULL'"
                class="px-6 py-2 rounded font-bold text-sm transition-all shadow-lg border border-transparent cursor-pointer"
                @click="emit('toggle-audio')"
            >
                {{ store.workerStatus === 'LISTENING' ? 'STOP AUDIO' : 'START AUDIO' }}
            </button>
        </div>
    </div>
</template>
