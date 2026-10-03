FROM emscripten/emsdk:4.0.15 AS wasm
WORKDIR /src
COPY dsp-wasm/ ./
RUN emcmake cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build --parallel 4

FROM oven/bun:1.4.2 AS ui
WORKDIR /app
COPY frontend/dev/src/package.json frontend/dev/src/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/dev/src/ ./
COPY --from=wasm /src/build/websdr_dsp.wasm ./public/dsp.wasm
COPY --from=wasm /src/build/_deps/liquid-src/LICENSE ./public/licenses/liquid-dsp.txt
RUN bun run typecheck && bun run build

FROM scratch AS frontend-export
COPY --from=ui /app/dist/ /

FROM nginx:1.27-alpine AS runtime
COPY --from=ui /app/dist/ /usr/share/nginx/html/
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
