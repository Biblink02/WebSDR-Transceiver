import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './bootstrap'
import '../resources/css/app.css'
import 'primeicons/primeicons.css'
import 'devicon/devicon.min.css'
import '@fontsource-variable/inter'
import PrimeVue from 'primevue/config'
import LocaleEn from 'primelocale/en.json'
import Aura from '@primevue/themes/aura'
import { createHead } from '@unhead/vue/client'
import { loadConfig } from "@/ConfigService"
import { useSdrStore } from "@/stores/sdr.store"
import ToastService from 'primevue/toastservice'

const initApp = async () => {
    const configData = await loadConfig()

    const app = createApp(App)
    const pinia = createPinia()

    app.use(router)
        .use(pinia)
        .use(PrimeVue, {
            theme: {
                preset: Aura,
                options: {
                    darkModeSelector: ".dark",
                },
            },
            locale: LocaleEn['en'],
        })
        .use(ToastService)
        .use(createHead())

    const store = useSdrStore()
    store.init(configData)

    app.mount('#app')
}

initApp()
