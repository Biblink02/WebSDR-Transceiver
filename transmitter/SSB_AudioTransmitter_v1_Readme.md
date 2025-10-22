# 🎧 SSB Audio Transmitter  

 **Single Sideband (SSB) transmitter** using **GNU Radio Companion** and a **PlutoSDR**.  
It takes your mic audio and turns it into an RF signal you can actually transmit.  

***

## What It Does  

Think of it like a small digital radio setup:
- Grabs your **mic input**  
- Cleans it up with a **band-pass filter** (so your voice sounds crisp)
- **band-pass filter** also turns it into a single side band by eliminating the -ve freq (float to complex)
- Lets you pick between **Upper Sideband (USB)** and **Lower Sideband (LSB)**  
- Has a mic **gain control** you can tweak live  
- Sends everything out through the **PlutoSDR**  
- Shows live plots so you can see what’s happening  

***

## Quick Block Rundown  

| Block | Job |
|-------|-----|
| Audio Source | Pulls audio from your mic at 48 kHz |
| Band-Pass Filter | Keeps only voice frequencies (300–3500 Hz) |
| Gain Control | Adjusts how loud your audio is |
| IQ Swap + Selector | Chooses USB or LSB mode |
| Resampler | Converts to 1 MHz sample rate for SDR |
| Pluto Sink | Transmits to the PlutoSDR |
| QtGUI Displays | Shows spectrum and waterfall views |

***

## How To Try It  

1. Open up the `.grc` file in **GNU Radio Companion**  
2. Plug in your **ADALM-Pluto SDR**  
3. Hit **Run** (the orange play button)  
4. Use the sliders and buttons to adjust frequency, gain, and sideband  
5. Speak into your mic and watch your signal come alive!  

***

## Requirements  

- GNU Radio 3.10 or later  
- gr-iio (for Pluto SDR support)  
- ADALM-Pluto SDR  
- Qt5 or PyQt for the GUI  

***
