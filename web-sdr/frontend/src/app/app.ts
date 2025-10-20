import {createApp} from 'vue'
import App from './App.vue'
import router from './router'
import './bootstrap'
import '../resources/css/app.css'
import 'primeicons/primeicons.css'
import 'devicon/devicon.min.css'
import '@fontsource-variable/inter'
import PrimeVue from 'primevue/config'
import LocaleIt from 'primelocale/it.json'
import Aura from '@primevue/themes/aura'
import {definePreset} from '@primevue/themes'
import {createHead} from '@unhead/vue/client'

const head = createHead()
const app = createApp(App)
const customPreset = definePreset(Aura, {
    semantic: {
        primary: {
            50: '{yellow.50}',
            100: '{yellow.100}',
            200: '{yellow.200}',
            300: '{yellow.300}',
            400: '{yellow.400}',
            500: '{yellow.500}',
            600: '{yellow.600}',
            700: '{yellow.700}',
            800: '{yellow.800}',
            900: '{yellow.900}',
            950: '{yellow.950}',
        },
    },
})

app.use(router)
    .use(PrimeVue, {
        theme: {
            preset: customPreset,
            options: {
                darkModeSelector: ".dark",
            },
        },

        locale: LocaleIt['it'],
    })
    .use(head)
    .mount('#app')
