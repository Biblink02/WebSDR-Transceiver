<script setup lang="ts">
<<<<<<< HEAD:web-sdr/frontend/src/app/layouts/AppLayout.vue
import { useDark, useToggle } from '@vueuse/core'
import NavbarLayout from './NavbarLayout.vue'
import FooterLayout from './FooterLayout.vue'
import ParticlesBackground from '../components/ParticlesBackground.vue'
=======
import {useDark, useToggle} from '@vueuse/core'
import FooterLayout from "./FooterLayout.vue";
import NavbarComponent from "../components/NavbarComponent.vue";
>>>>>>> feat/frontend:web-sdr/frontend/app/layouts/AppLayout.vue

const isDarkMode = useDark()
const toggleDarkMode = useToggle(isDarkMode)
</script>

<template>
<<<<<<< HEAD:web-sdr/frontend/src/app/layouts/AppLayout.vue
  <div class="min-h-screen w-full relative">
    <!-- Fond animé -->
    <ParticlesBackground class="absolute inset-0 z-0" />

    <!-- Contenu principal -->
    <div class="relative z-10 max-w-7xl w-full mx-auto pt-4 p-1 sm:p-4 md:p-7 space-y-10 min-h-screen">
      <!-- Dark Mode Toggle -->
      <button
        @click="toggleDarkMode()"
        class="lg:fixed absolute cursor-pointer top-9 right-9 text-favourite_yellow"
        :title="'Toggle ' + (isDarkMode ? 'Light' : 'Dark') + ' Mode'"
      >
        <div class="hidden dark:block">
          <i class="pi pi-sun" style="font-size: 1.6rem"></i>
        </div>
        <div class="dark:hidden">
          <i class="pi pi-moon" style="font-size: 1.5rem"></i>
        </div>
      </button>

      <!-- Navbar -->
      <NavbarLayout class="relative z-20" />

      <!-- Contenu des pages -->
      <slot />

      <!-- Footer -->
      <FooterLayout class="relative z-20" />
=======
    <div class="max-w-7xl w-full mx-auto pt-4 p-1 sm:p-4 md:p-7 space-y-10">
        <!-- Dark Mode -->
        <button
            @click="toggleDarkMode()"
            class="lg:fixed absolute cursor-pointer top-9 right-9 text-favourite_yellow"
            :title="'Toggle ' + (isDarkMode ? 'Light' : 'Dark') + ' Mode'"
        >
            <div class="hidden dark:block">
                <i class="pi pi-sun hidden" style="font-size: 1.6rem"></i>
            </div>
            <div class="dark:hidden">
                <i class="pi pi-moon hidden" style="font-size: 1.5rem"></i>
            </div>
        </button>
        <NavbarComponent/>
        <slot/>
        <FooterLayout/>
>>>>>>> feat/frontend:web-sdr/frontend/app/layouts/AppLayout.vue
    </div>
  </div>
</template>
