import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AppConfig } from '@/ConfigService'

export const useSdrStore = defineStore('sdr', () => {
    const config = ref<AppConfig | null>(null)

    // State
    const isConnected = ref(false)
    const statusText = ref('CONNECTING')
    const workerStatus = ref<'IDLE' | 'LISTENING' | 'FULL'>('IDLE')
    const assignedWorkerId = ref<string | null>(null)

    // Default values (will be overwritten by init)
    const tuneFreq = ref(0)
    const bandwidth = ref(15000)
    const volume = ref(100)

    // --- Actions ---

    function init(loadedConfig: AppConfig) {
        config.value = loadedConfig
        // Set defaults from config
        tuneFreq.value = loadedConfig.lo_freq
    }

    function setConnectionStatus(connected: boolean, text: string) {
        isConnected.value = connected
        statusText.value = text
    }

    function setWorkerStatus(status: 'IDLE' | 'LISTENING' | 'FULL', workerId: string | null = null) {
        workerStatus.value = status
        assignedWorkerId.value = workerId
    }

    function setFrequency(freq: number) {
        tuneFreq.value = freq
    }

    function setBandwidth(bw: number) {
        bandwidth.value = bw
    }

    function setVolume(vol: number) {
        volume.value = Math.max(0, Math.min(100, vol))
    }

    // --- Getters ---

    const settings = computed((): AppConfig => {
        if (!config.value) {
            throw new Error("Configuration not loaded in Store")
        }
        return config.value
    })

    return {
        config,
        settings,
        isConnected,
        statusText,
        workerStatus,
        assignedWorkerId,
        tuneFreq,
        bandwidth,
        volume,
        init,
        setConnectionStatus,
        setWorkerStatus,
        setFrequency,
        setBandwidth,
        setVolume
    }
})
