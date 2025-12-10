# WebSDR-Transceiver

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)]()
[![Kubernetes](https://img.shields.io/badge/Kubernetes-ready-blue.svg)]()
[![GNU Radio](https://img.shields.io/badge/GNU%20Radio-3.11-orange.svg)]()

This project provides a complete software suite for a ground station capable of receiving data from the QO-100 geostationary satellite. It includes a backend for signal processing and a web-based frontend that displays demodulated received signals via a waterfall chart (spectrogram) and enables real-time audio listening.

This project was developed as part of the BIP (Blended Intensive Programme) between:
- University of Padua
- Télécom Saint-Étienne
- Technical University of Darmstadt

## Overview

The system is built as a distributed microservice architecture running on Kubernetes. It bridges hardware Software Defined Radio (SDR) interfaces with a modern web UI.

### Key Features
- Real-time reception from the QO-100 satellite
- SSB demodulation performed server-side
- Web interface with live spectrogram and audio playback
- Dynamic worker allocation for multiple concurrent listeners
- Containerized architecture suitable for scaling

## Architecture

The application is containerized and orchestrated using Kubernetes (Kind).

- **Frontend:** Vue 3 + Vite web UI
- **Backend Controller:** Python/FastAPI, manages WebSocket connections, worker orchestration and control logic
- **SDR Server:** Interfaces with the PlutoSDR and streams I/Q data via ZeroMQ
- **Graphics Worker:** Computes FFT data and produces spectrogram frames
- **Audio Workers:** Each worker performs DSP demodulation for a specific requested frequency band

## Prerequisites

- Docker
- Kind
- kubectl
- GNU Radio (required locally for grcc)

## Installation & Deployment

Clone the repository:
```bash
git clone [https://github.com/Biblink02/WebSDR-Transceiver.git](https://github.com/Biblink02/WebSDR-Transceiver.git)
cd WebSDR-Transceiver
```

**Full Deployment (First Run or Code Changes):**
If you are running for the first time or have modified the source code (Python, Vue.js, GRC files), run:
```bash
./deploy.sh
```

**Fast Configuration Reload:**
If you only modified `config/config.yaml` (e.g., tuning frequencies, gains, or ports) and want to apply changes immediately without rebuilding Docker images:
```bash
./reload.sh
# Or manually: bash kubernetes/start-cluster.sh
```

Access the web interface:
```
http://localhost
```

## Configuration

The entire system behavior is controlled by a single configuration file located at `config/config.yaml`. This makes the Frontend, Backend, and DSP workers utilize synchronized parameters.

### Key Settings to Customize

Before running the cluster, you **must** update the `iio_uri` to match your hardware setup, and for deployment make sure to change also the `WS_URL`.

## Development Team (PRI05)

- Alberto (Biblink02) — University of Padua
- Alexandre (TheAnacondA57) — University of Télécom Saint-Étienne
- Clément (clfusero) — University of Télécom Saint-Étienne
- Fatemah (Pitclair) — University of Padua
- Lorenzo (Fireentity) — University of Padua
- Mihir (M1keP1) — Technical University of Darmstadt
- Vedant (vedant-224) — Technical University of Darmstadt

## License
MIT License
