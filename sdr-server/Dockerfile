FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnuradio python3 python3-numpy python3-yaml python3-zmq python3-libiio \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY sdr-server/*.py ./
COPY shared/iq_protocol.py ./
EXPOSE 5000 8081
CMD ["python3", "-u", "sdr_server.py"]
