import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { imagetools } from 'vite-imagetools'
import { PrimeVueResolver } from '@primevue/auto-import-resolver'
import Components from 'unplugin-vue-components/vite'
import tailwindcss from '@tailwindcss/vite'

interface Params {
    mode: string
}

// noinspection JSUnusedGlobalSymbols
export default ({ mode }: Params) => {
    process.env = { ...process.env, ...loadEnv(mode, process.cwd()) }

    return defineConfig({
        base: '/',
        plugins: [
            tailwindcss(),
            Components({
                resolvers: [PrimeVueResolver()],
            }),
            imagetools({
                defaultDirectives: () => {
                    return new URLSearchParams({
                        format: 'webp',
                        quality: '50',
                    })
                },
            }),
            vue({
                template: {
                    compilerOptions: {
                        isCustomElement: (tag) => tag.startsWith('Tres'),
                    },
                    transformAssetUrls: {
                        base: null,
                        includeAbsolute: false,
                    },
                },
            }),
        ],

        resolve: {
            alias: {
                '&': '/app',
                '@': '/app/ts',
                '~': '/resources',
                'vue-i18n': 'vue-i18n/dist/vue-i18n.cjs.js', // https://github.com/intlify/vue-i18n-next/issues/789
            },
        },

        build: {
            rollupOptions: {
                input: 'index.html', // Ensures Vite knows where to start
            },
        },

        server: {
            host: '0.0.0.0',
            port: parseInt(process.env.VITE_PORT ?? '3100'),
            hmr: {
                host: process.env.VITE_EXTERNAL_HOST,
            },
        },
    })
}
