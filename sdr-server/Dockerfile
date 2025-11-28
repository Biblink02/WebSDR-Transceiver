FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y python3-pip gnuradio libiio-utils libad9361-0 gnuradio-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY sdr_server.grc .
RUN mkdir -p /root/.gnuradio/prefs
RUN grcc -o . sdr_server.grc
RUN rm sdr_server.grc
EXPOSE 5000
CMD ["python3", "-u", "sdr_server.py"]


