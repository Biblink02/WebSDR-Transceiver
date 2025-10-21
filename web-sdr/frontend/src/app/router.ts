import {createRouter, createWebHistory} from 'vue-router'
import HomePage from './pages/HomePage.vue'
import SrdPage from './pages/sdr/SdrPage.vue'

const routes = [{path: '/', component: HomePage}, {path: '/sdr', component: SrdPage}]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
