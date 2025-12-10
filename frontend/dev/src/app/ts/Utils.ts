import {useSdrStore} from "@/stores/sdr.store";

// IF -> RF (For Display)
export function calculateDisplayFrequency(frequency: number): number {
    return frequency + useSdrStore().settings.lnb_lo_freq;
}

// RF -> IF (For Input)
export function calculateIFFrequency(displayFrequency: number): number {
    return displayFrequency - useSdrStore().settings.lnb_lo_freq;
}
