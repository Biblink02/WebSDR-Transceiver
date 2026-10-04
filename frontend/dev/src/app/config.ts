import yaml from 'js-yaml'

export interface IqBand {
    id: number; center_freq: number; sample_rate: number; low: number; high: number; bits_per_second: number
}
export type IqSelection = number | 'full'
export type IqFullBand = Omit<IqBand, 'id'> & { id: 'full' }
export interface BandCatalog {
    default: number; input_sample_rate: number; input_center_freq: number;
    bands: IqBand[]; full_band: IqFullBand
}

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
    const validSpan = (band: IqBand | IqFullBand) =>
        [band.center_freq, band.sample_rate, band.low, band.high, band.bits_per_second].every(Number.isFinite) &&
        Number.isInteger(band.sample_rate) && band.sample_rate >= 48000 && band.sample_rate <= 4000000 &&
        band.center_freq > 0 && band.low < band.high && band.bits_per_second === band.sample_rate * 16 &&
        band.low >= band.center_freq - band.sample_rate / 2 && band.high <= band.center_freq + band.sample_rate / 2
    if (!catalog || !Array.isArray(catalog.bands) || !catalog.bands.length || catalog.bands.length > 16 ||
        catalog.bands.some(band => !band || !Number.isInteger(band.id) || !validSpan(band)) ||
        !Number.isInteger(catalog.default) || !catalog.bands.some(band => band.id === catalog.default) ||
        new Set(catalog.bands.map(band => band.id)).size !== catalog.bands.length ||
        !catalog.full_band || catalog.full_band.id !== 'full' || !validSpan(catalog.full_band) ||
        catalog.full_band.sample_rate !== catalog.input_sample_rate ||
        catalog.full_band.center_freq !== catalog.input_center_freq)
        throw new Error('Invalid I/Q subband catalog')
    config.bands = catalog
    return config
}
