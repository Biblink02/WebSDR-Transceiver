FROM python:3.12-slim AS channelizer
RUN apt-get update && apt-get install -y --no-install-recommends cmake make g++ ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY dsp-wasm /src/dsp-wasm
RUN cmake -S /src/dsp-wasm -B /build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /build --target websdr_channelizer -j2

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=channelizer /build/libwebsdr_channelizer.so ./
COPY --from=channelizer /build/_deps/liquid-src/LICENSE ./licenses/liquid-dsp.txt
COPY backend-controller/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend-controller/*.py ./
COPY shared/iq_protocol.py ./
USER 65532:65532
EXPOSE 8080
ENV PORT=8080
CMD ["python", "backend_controller.py"]
