import {createRouter, createWebHistory} from 'vue-router'
import HomePage from './pages/HomePage.vue'
import AboutUs from "./pages/AboutUs.vue";

const routes = [
    {path: '/', component: HomePage},
    {path: '/about-us', component: AboutUs}
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
