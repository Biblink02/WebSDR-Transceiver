import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { PrimeVueResolver } from '@primevue/auto-import-resolver'
import Components from 'unplugin-vue-components/vite'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

interface Params {
    mode: string
}

// noinspection JSUnusedGlobalSymbols
export default ({ mode }: Params) => {
    process.env = { ...process.env, ...loadEnv(mode, process.cwd()) }
    const backend = process.env.SDR_BACKEND_URL ?? 'http://127.0.0.1:8080'

    return defineConfig({
        base: '/',
        plugins: [
            tailwindcss(),
            Components({
                dts: 'app/components.d.ts',
                resolvers: [PrimeVueResolver()],
            }),
            vue({
                template: {
                    transformAssetUrls: {
                        base: null,
                        includeAbsolute: false,
                    },
                },
            }),
        ],

        resolve: {
            alias: {
                '&': fileURLToPath(new URL('./app', import.meta.url)),
                '~': fileURLToPath(new URL('./resources', import.meta.url)),
            },
        },

        build: {
            rollupOptions: {
                input: 'index.html', // Ensures Vite knows where to start
            },
        },
        server: {
            proxy: {
                '/iq': { target: backend, ws: true },
                '/stream-info': { target: backend },
                '/bands': { target: backend },
            },
            host: '0.0.0.0',
            port: parseInt(process.env.VITE_PORT ?? '3100'),
            hmr: {
                host: process.env.VITE_EXTERNAL_HOST,
            },
        },
    })
}
