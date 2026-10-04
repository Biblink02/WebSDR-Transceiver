import yaml from 'js-yaml'

export interface IqBand {
    id: number; center_freq: number; sample_rate: number; low: number; high: number; bits_per_second: number
}
export interface BandCatalog { default: number; input_sample_rate: number; input_center_freq: number; bands: IqBand[] }

export interface AppConfig {
    samp_rate: number
    fft_size: number
    lo_freq: number
    lnb_lo_freq: number
    max_bw_limit: number
    min_bw_limit: number
    range_db: number
    gain_db: number
    view_limit_min: number
    view_limit_max: number
    audio_rate: number
    bandwidth: number
    calibration: number
    ws_url: string
    bands: BandCatalog
}

export async function loadConfig(): Promise<AppConfig> {
    const response = await fetch('/config.yaml', { cache: 'no-store' })
    if (!response.ok) throw new Error('Failed to fetch config.yaml')
    const config = yaml.load(await response.text()) as AppConfig
    if (!config || typeof config !== 'object') throw new Error('Invalid SDR configuration')
    for (const key of ['samp_rate', 'fft_size', 'lo_freq', 'lnb_lo_freq', 'max_bw_limit',
        'min_bw_limit', 'range_db', 'gain_db',
        'view_limit_min', 'view_limit_max', 'audio_rate', 'bandwidth', 'calibration'] as const) {
        if (!Number.isFinite(config[key])) throw new Error(`Invalid configuration: ${key}`)
    }
    if (config.audio_rate !== 48000 || config.samp_rate < 48000 || config.samp_rate > 4000000 ||
        config.fft_size < 256 || config.fft_size > 32768 || (config.fft_size & (config.fft_size - 1)) ||
        config.min_bw_limit < 90 || config.max_bw_limit > 15000 || config.min_bw_limit > config.max_bw_limit ||
        config.bandwidth < config.min_bw_limit || config.bandwidth > config.max_bw_limit ||
        config.view_limit_max <= config.view_limit_min || config.range_db <= 0 ||
        typeof config.ws_url !== 'string') throw new Error('Unsupported SDR configuration values')
    const catalogResponse = await fetch('/bands', { cache: 'no-store' })
    if (!catalogResponse.ok) throw new Error('Failed to fetch I/Q subbands')
    const catalog = await catalogResponse.json() as BandCatalog
    if (!catalog || !Array.isArray(catalog.bands) || !catalog.bands.length || catalog.bands.length > 16 ||
        !Number.isInteger(catalog.default) || !catalog.bands.some(band => band.id === catalog.default) ||
        new Set(catalog.bands.map(band => band.id)).size !== catalog.bands.length ||
        catalog.bands.some(band => !Number.isInteger(band.id) ||
            ![band.center_freq, band.sample_rate, band.low, band.high, band.bits_per_second].every(Number.isFinite) ||
            band.sample_rate < 48000 || band.sample_rate > 4000000 || band.low >= band.high ||
            band.low < band.center_freq - band.sample_rate / 2 || band.high > band.center_freq + band.sample_rate / 2))
        throw new Error('Invalid I/Q subband catalog')
    config.bands = catalog
    return config
}
