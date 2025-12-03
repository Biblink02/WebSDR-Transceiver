import yaml from 'js-yaml'

export interface AppConfig {
    // DSP & Visualization
    samp_rate: number
    fft_size: number
    lo_freq: number
    bandwidth: number

    // Connection
    WS_URL: string
    WS_GRAPHICS_EVENT: string
    WS_AUDIO_EVENT: string

    // Audio
    audio_rate: number
    CHANNELS: number
    MAX_QUEUE_SIZE: number
    BUFFER_THRESHOLD: number

    // Graphic
    RANGE_DB: number
    GAIN_ATTACK: number
    GAIN_RELEASE: number
}

let config: AppConfig | null = null

export async function loadConfig(): Promise<AppConfig> {
    if (config) return config

    try {
        const response = await fetch('/config.yaml')
        if (!response.ok) throw new Error('Failed to fetch config.yaml')

        const text = await response.text()
        config = yaml.load(text) as AppConfig
        return config
    } catch (error) {
        console.error('Configuration load failed:', error)
        throw error
    }
}

export function getConfig(): AppConfig {
    if (!config) throw new Error('Config not loaded')
    return config
}
