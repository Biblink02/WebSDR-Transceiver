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
import {createHead} from '@unhead/vue/client'
import {loadConfig} from "@/ConfigStore";

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
            locale: LocaleIt['it'],
        })
        .use(head)
        .mount('#app')
}

initApp().then()
