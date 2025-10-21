import {createRouter, createWebHistory} from 'vue-router'
import HomePage from './pages/HomePage.vue'
import SrdPage from './pages/sdr/SdrPage.vue'
import AboutUs from "./pages/AboutUs.vue";

const routes = [{path: '/', component: HomePage}, {path: '/sdr', component: SrdPage}, {path: '/aboutus', component: AboutUs}]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
