import { interpolateTurbo, interpolateViridis, interpolateInferno, interpolateMagma,
    interpolatePlasma, interpolateCividis, interpolateCool, interpolateWarm,
    interpolateCubehelixDefault, interpolateGreys } from 'd3-scale-chromatic'
import { color } from 'd3-color'

export const PALETTES = [
    { value: 'classic', label: 'Classic', interpolate: interpolateTurbo },
    { value: 'viridis', label: 'Viridis', interpolate: interpolateViridis },
    { value: 'inferno', label: 'Inferno', interpolate: interpolateInferno },
    { value: 'magma', label: 'Magma', interpolate: interpolateMagma },
    { value: 'plasma', label: 'Plasma', interpolate: interpolatePlasma },
    { value: 'cividis', label: 'Cividis', interpolate: interpolateCividis },
    { value: 'cool', label: 'Cool', interpolate: interpolateCool },
    { value: 'warm', label: 'Warm', interpolate: interpolateWarm },
    { value: 'cubehelix', label: 'Cubehelix', interpolate: interpolateCubehelixDefault },
    { value: 'grayscale', label: 'Grayscale', interpolate: (t: number) => interpolateGreys(1 - t) },
]
export function paletteColors(name: string): Uint8ClampedArray {
    const palette = PALETTES.find(p => p.value === name) ?? PALETTES[0]
    const bytes = new Uint8ClampedArray(256 * 4)
    for (let i = 0; i < 256; i++) {
        const rgb = color(palette.interpolate(i / 255))!.rgb()
        bytes.set([rgb.r, rgb.g, rgb.b, 255], i * 4)
    }
    return bytes
}
