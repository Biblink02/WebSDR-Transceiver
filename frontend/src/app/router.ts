import {createRouter, createWebHistory} from 'vue-router'
import HomePage from '&/pages/HomePage.vue'
import AboutUs from '&/pages/AboutUs.vue'
import Resources from '&/pages/Resources.vue'
import SatelliteTracker from '&/pages/SatelliteTracker.vue'
import SdrPage from '&/pages/SdrPage.vue'



const routes = [
    {path: '/', component: HomePage},
    {path: '/sdr', component: SdrPage},
    {path: '/about', component: AboutUs},
    {path: '/resources', component: Resources},
    {path: '/satellite-tracker', component: SatelliteTracker}
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
