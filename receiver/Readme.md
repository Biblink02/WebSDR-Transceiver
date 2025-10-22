# 📡 PlutoSDR Receiver → FFT → UDP  

Grabs RF signals using a **PlutoSDR**, processes the samples through an **FFT**, and sends the results over a **UDP socket** for external use.  

***

## What It Does  

- Receives IQ samples from PlutoSDR at **2.45 GHz**, sampling at **2 MS/s** (good balance between bandwidth and processing load).  
- Filters with a **low-pass filter** (cutoff ~200 kHz) to focus on signals of interest and reduce noise from outside frequencies.  
- Packs samples into chunks of **1024** for FFT processing — this size offers reasonable frequency resolution without lagging too much.  
- Converts time-domain samples to frequency domain to inspect power spectra.  
- Normalizes power values by dividing by FFT length (to keep levels consistent).  
- Tags frames by length and converts to network packets (PDUs).  
- Sends data over UDP to localhost port **8000** — to be used to stream using SocketIO
- Shows real-time frequency and waterfall plots for visual monitoring.

***

## Block Parameters Explained  

| Block | Parameter | Why It’s Set That Way |
|-------|-----------|----------------------|
| PlutoSDR Source | frequency = 2450 MHz | Target ISM band around 2.45 GHz, common for experiments |
| PlutoSDR Source | samplerate = 2,000,000 | Captures a wide enough bandwidth but manageable for real-time FFT |
| Low-Pass Filter | cutoff = 200 kHz | Limits noise and out-of-band signals to focus FFT on desired frequencies |
| FFT Block | fft_size = 1024 | Nice tradeoff between frequency detail and processing speed |
| Multiply Const | const = 1/1024 | Normalizes FFT output so power scale stays consistent |
| Network Socket | host = 127.0.0.1, port = 8000 | Local UDP streaming target, easy to test and capture data |

***

## Using This  

1. Connect your PlutoSDR.  
2. Launch the flowgraph in GNU Radio Companion.  
3. Tweak the frequency or sample rate if needed.  
4. Run and watch real-time spectral displays.  
5. Listen for UDP packets on port 8000 with another app.

***

## What You Need  

- GNU Radio 3.10+ with gr-iio plugin  
- ADALM-Pluto SDR  
- Python 3 

***

## About  

Made by **Mihir Vedant** as a neat demo of PlutoSDR + FFT + UDP streaming
