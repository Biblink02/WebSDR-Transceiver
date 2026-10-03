import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { AppConfig } from '@/ConfigService'

export const useSdrStore = defineStore('sdr', () => {
    const config = ref<AppConfig | null>(null)
    const isConnected = ref(false)
    const isListening = ref(false)
    const statusText = ref('CONNECTING...')
    const tuneFreq = ref(0)
    const bandwidth = ref(2700)
    const sideband = ref<1 | -1>(1)
    const volume = ref(50)
    const palette = ref('classic')
    const passband = computed(() => ({
        low: tuneFreq.value + (sideband.value < 0 ? -bandwidth.value : 0),
        high: tuneFreq.value + (sideband.value > 0 ? bandwidth.value : 0),
    }))

    function init(loadedConfig: AppConfig) {
        config.value = loadedConfig
        tuneFreq.value = loadedConfig.lo_freq
        bandwidth.value = loadedConfig.bandwidth
    }
    function setConnectionStatus(connected: boolean, text: string) {
        isConnected.value = connected
        statusText.value = text
    }
    function setFrequency(freq: number) { tuneFreq.value = freq }
    function setBandwidth(bw: number) { bandwidth.value = bw }
    const settings = computed(() => {
        if (!config.value) throw new Error('SDR configuration is not loaded')
        return config.value
    })
    return { config, settings, isConnected, isListening, statusText, tuneFreq, bandwidth,
        sideband, passband, volume, palette, init, setConnectionStatus, setFrequency, setBandwidth }
})
