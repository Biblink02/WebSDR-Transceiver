import {createApp} from 'vue'
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
import {createHead} from '@unhead/vue/client'
import {loadConfig} from "@/ConfigStore";
import ToastService from 'primevue/toastservice';

const initApp = async () => {
    await loadConfig()

    const head = createHead()
    const app = createApp(App)

    app.use(router)
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
        .use(head)
        .mount('#app')
}

initApp()
