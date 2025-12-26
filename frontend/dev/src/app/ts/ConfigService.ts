import yaml from 'js-yaml'

export interface AppConfig {
    // DSP & Physics
    samp_rate: number
    fft_size: number
    lo_freq: number
    lnb_lo_freq: number

    // Frontend Limits
    max_bw_limit: number
    min_bw_limit: number
    channel_count: number
    buffer_threshold: number
    max_queue_size: number

    // Visualization
    range_db: number
    gain_db: number
    gain_attack: number
    gain_release: number
    view_limit_min: number
    view_limit_max: number

    // Audio
    audio_rate: number
    bandwidth: number

    // Connection
    ws_url: string

    // Protocol / Events
    ws_graphics_event: string
    ws_audio_event: string
    ws_server_full_event: string
    ws_worker_assigned_event: string
    ws_worker_released_event: string
    ws_correction_event: string
    ws_connect_event: string
    ws_disconnect_event: string
    ws_request_worker_event: string
    ws_dismiss_worker_event: string
    ws_tune_event: string
}

export async function loadConfig(): Promise<AppConfig> {
    try {
        const response = await fetch('/config.yaml')
        if (!response.ok) throw new Error('Failed to fetch config.yaml')

        const text = await response.text()
        return yaml.load(text) as AppConfig
    } catch (error) {
        console.error('Configuration load failed:', error)
        throw error
    }
}
