    import {createRouter, createWebHistory} from 'vue-router'
import HomePage from './pages/HomePage.vue'
<<<<<<< HEAD:web-sdr/frontend/src/app/router.ts
import SrdPage from './pages/sdr/SdrPage.vue'
import aboutpage from './pages/about.vue'
import ressources from './pages/ressources.vue'
import SatelliteTracker from './pages/SatelliteTracker.vue'


const routes = [
    {path: '/', component: HomePage}, 
    {path: '/sdr', component: SrdPage},
    {path: '/about', component: aboutpage},
    {path: '/ressources', component: ressources},
    {path: '/satellite-tracker', component: SatelliteTracker}
=======
import AboutUs from "./pages/AboutUs.vue";

const routes = [
    {path: '/', component: HomePage},
    {path: '/about-us', component: AboutUs}
>>>>>>> feat/frontend:web-sdr/frontend/app/router.ts
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
