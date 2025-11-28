FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3-pip \
    gnuradio \
    gnuradio-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install pyzmq

WORKDIR /app

COPY graphics_worker.grc .

RUN mkdir -p /root/.gnuradio/prefs
RUN grcc -o . graphics_worker.grc
RUN rm graphics_worker.grc

EXPOSE 5001

CMD ["python3", "-u", "graphics_worker.py"]
