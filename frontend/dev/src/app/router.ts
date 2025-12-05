import {createRouter, createWebHistory} from 'vue-router'
import HomePage from "./Pages/HomePage.vue";
import SdrPage from "./Pages/SdrPage.vue";
import AboutUs from "./Pages/AboutUs.vue";
import Resources from "./Pages/Resources.vue";


const routes = [
    {path: '/', component: HomePage, label: 'Our project'},
    {path: '/sdr', component: SdrPage, label: 'SDR'},
    {path: '/about-us', component: AboutUs, label: 'About us'},
    {path: '/resources', component: Resources, label: 'Resources'},
    //{ path: '/satellite-tracker', component: SatelliteTracker, label: 'Satellite Tracker' }
]
export const items = routes.map(r => ({
    label: r.label,
    to: r.path
}))

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
