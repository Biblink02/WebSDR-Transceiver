# 📡 PlutoSDR Receiver → FFT → UDP + Direct IQ UDP Stream

Captures RF signals using a **PlutoSDR**, processes them through an **FFT** for spectral analysis **and** simultaneously streams **raw IQ samples** directly over a separate UDP port.

---

## 🔧 What It Does

* **Receives IQ samples** from PlutoSDR at **2.45 GHz**, sampling at **2 MS/s**.
* **Low-pass filters** the data (~200 kHz cutoff) to isolate signals of interest.
* **Branches into two parallel paths**:

  1. **FFT Path** → converts to frequency domain, normalizes, visualizes, and sends FFT magnitudes via **UDP (port 8000)**.
  2. **Direct IQ Path** → sends complex (fc32) IQ samples *directly from the SDR* via **UDP (port 8005)**.
* The FFT path lets you analyze spectral content, while the IQ path lets you record or demodulate raw baseband data elsewhere.
* **Real-time frequency and waterfall displays** remain for local monitoring.

---

## ⚙️ Block Parameters Explained

| Block                          | Parameter                                              | Purpose                                          |
| ------------------------------ | ------------------------------------------------------ | ------------------------------------------------ |
| **PlutoSDR Source**            | `frequency = 2450e6`                                   | Tunes to the 2.45 GHz ISM band                   |
|                                | `samplerate = 2e6`                                     | 2 MS/s gives good bandwidth for general analysis |
| **Low-Pass Filter**            | `cutoff = 200e3`                                       | Focuses on relevant sub-band and reduces noise   |
| **FFT Block**                  | `fft_size = 1024`                                      | Balances frequency resolution and responsiveness |
| **Multiply Const**             | `const = 1/fft_len`                                    | Normalizes FFT output amplitude                  |
| **Network Socket (FFT)**       | `host = 127.0.0.1`, `port = 8000`                      | Sends processed FFT data over UDP                |
| **Stream→Tagged Stream (IQ)**  | `type = complex`, `len_tag_key = "packet_len_iq"`      | Packetizes raw IQ samples                        |
| **PDU Tagged Stream→PDU (IQ)** | `type = complex`, `tag = "packet_len_iq"`              | Converts tagged stream to PDUs                   |
| **Network Socket (IQ)**        | `type = UDP_CLIENT`, `host = 127.0.0.1`, `port = 8005` | Sends raw complex IQ packets over UDP            |

---

## 🧠 Understanding the Two Outputs

| Path             | Data Type                       | UDP Port | Use Case                                      |
| ---------------- | ------------------------------- | -------- | --------------------------------------------- |
| FFT Output       | Float power values (magnitude²) | **8000** | Visualization, spectral analysis              |
| Direct IQ Output | Complex float32 (I/Q)           | **8005** | Recording, demodulation, ML signal processing |

---

## 🚀 How to Use

1. Connect your **ADALM-Pluto SDR**.
2. Open the flowgraph (`Reciever_FFT-UDP_v3_stable.grc`) in GNU Radio Companion.
3. Adjust the **center frequency**, **sample rate**, or **filter cutoff** if needed.
4. Run the flowgraph — you’ll see live FFT and waterfall displays.
5. Listen or capture:

   * **UDP 8000** → FFT magnitude frames (for spectrum visualization).
   * **UDP 8005** → raw complex IQ packets (for external decoding or storage).

Example:

```bash
# To view FFT UDP packets
nc -u 127.0.0.1 8000 | hexdump -C

# To record raw IQ stream
nc -u 127.0.0.1 8005 > iq_data.raw
```

---

## 🧩 Requirements

* GNU Radio 3.10+
* `gr-iio` (for PlutoSDR)
* ADALM-Pluto SDR hardware
* Python 3 environment

---

## 👤 About

Created by **Mihir Vedant** — enhanced version adds a **direct IQ streaming path** for dual-purpose SDR analysis and raw-data streaming.
