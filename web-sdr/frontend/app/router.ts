import {createRouter, createWebHistory} from 'vue-router'
import HomePage from '&/pages/HomePage.vue'
import aboutpage from '&/pages/about.vue'
import ressources from '&/pages/ressources.vue'
import SatelliteTracker from '&/pages/SatelliteTracker.vue'


const routes = [
    {path: '/', component: HomePage},
    {path: '/about', component: aboutpage},
    {path: '/ressources', component: ressources},
    {path: '/satellite-tracker', component: SatelliteTracker}
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
