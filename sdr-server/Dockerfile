FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-numpy python3-yaml python3-zmq \
    libboost-program-options1.83.0 libgmp10 libxml2 \
    libusb-1.0-0 libiio0 libad9361-0 \
    libspdlog1.12 libvolk3.1t64 \
    libboost-thread1.83.0 libboost-system1.83.0 libboost-filesystem1.83.0 \
    libfftw3-single3 libzmq5 \
    curl ca-certificates libpython3-stdlib libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

ARG GR_VERSION=gr-3.11-custom-v2

RUN curl -L "https://github.com/Biblink02/WebSDR-Transceiver/releases/download/${GR_VERSION}/gnuradio-install.tar.gz" -o gnuradio-install.tar.gz \
 && tar -xzf gnuradio-install.tar.gz -C /usr/local \
 && rm gnuradio-install.tar.gz

ENV PYTHONPATH=/usr/local/lib/python3.12/site-packages
ENV LD_LIBRARY_PATH=/usr/local/lib
ENV PATH=/usr/local/bin:$PATH

WORKDIR /app
COPY *.py .

EXPOSE 5000 5001
CMD ["python3", "-u", "sdr_server.py"]
