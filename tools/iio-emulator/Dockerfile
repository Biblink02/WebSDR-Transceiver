FROM ubuntu:24.04 AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake make gcc libc6-dev libxml2-dev libzstd-dev flex bison \
 && rm -rf /var/lib/apt/lists/*
# Official libiio emulator, pinned independently of the production GNU Radio ABI.
ADD --checksum=sha256:3bf0f466eff0f54dfbbc680628a826917065febb5cf31213447b666b0005628e https://codeload.github.com/analogdevicesinc/libiio/tar.gz/1f2ade12b3a97527334a8ed9319d4c2b63b9d4b7 /tmp/libiio.tar.gz
RUN mkdir /src && tar -xf /tmp/libiio.tar.gz -C /src --strip-components=1 \
 && cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Release \
    -DWITH_EMU_BACKEND=ON -DWITH_IIOD=ON -DWITH_AIO=OFF \
    -DWITH_LOCAL_BACKEND=OFF -DWITH_USB_BACKEND=OFF -DWITH_SERIAL_BACKEND=OFF \
    -DHAVE_DNS_SD=OFF -DWITH_UTILS=OFF -DLIBIIO_COMPAT=OFF \
 && cmake --build /build --parallel 4 --target iiod

FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends libxml2 libzstd1 \
 && rm -rf /var/lib/apt/lists/*
COPY --from=build /build/iiod/iiod /usr/local/bin/
COPY --from=build /build/libiio.so* /usr/local/lib/
COPY --from=build /src/COPYING* /usr/share/licenses/libiio/
RUN ldconfig
USER 65534:65534
EXPOSE 30431
# GNU Radio's distribution libiio uses the text protocol. Official IIOD serves
# that protocol over the same emu backend without replacing the production client.
ENTRYPOINT ["iiod", "-u", "emu:/data/pluto.xml"]
