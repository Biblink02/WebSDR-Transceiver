FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install only GNU Radio and pyzmq (no Pluto drivers here)
RUN apt-get update && apt-get install -y \
    python3-pip \
    gnuradio \
    # gnuradio-dev is needed for the 'grcc' command
    gnuradio-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pyzmq for remote control
RUN pip3 install pyzmq

WORKDIR /app

COPY audio_worker.grc .

# Compile the GRC file into Python
RUN mkdir -p /root/.gnuradio/prefs
RUN grcc -o . audio_worker.grc
RUN rm audio_worker.grc

# Expose control port
EXPOSE 5001

# Run the script (headless mode)
CMD ["python3", "-u", "audio_worker.py"]
