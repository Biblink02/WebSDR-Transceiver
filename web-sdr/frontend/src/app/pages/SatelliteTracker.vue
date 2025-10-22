<script setup lang="ts">
import { useDark, useToggle } from '@vueuse/core'
import NavbarLayout from '../layouts/NavbarLayout.vue'
import FooterLayout from '../layouts/FooterLayout.vue'
import ParticlesBackground from '../components/ParticlesBackground.vue'

const isDarkMode = useDark()
const toggleDarkMode = useToggle(isDarkMode)
</script>

<template>
  <div class="min-h-screen w-full relative">
    <!-- Fond animé -->
    <ParticlesBackground class="absolute inset-0 z-0" />

    <!-- Contenu principal -->
    <div class="relative z-10 w-full">
      <!-- Dark Mode Toggle -->
      <button
        @click="toggleDarkMode()"
        class="lg:fixed absolute cursor-pointer top-9 right-9 text-favourite_yellow z-50"
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

      <!-- Header pour la page Satellite Tracker -->
      <div class="text-center py-2">
        <h1 class="text-2xl font-bold text-white drop-shadow-lg mb-1">
          Satellite Tracker
        </h1>
        <p class="text-sm text-white drop-shadow-md">
          Track satellites in real-time using sattrack.app
        </p>
      </div>
      
      <!-- Container pour l'embedding -->
      <div class="w-full min-h-[930px] h-[calc(100vh-200px)] px-1 pb-1 flex items-center justify-center overflow-hidden">
        <iframe
          src="https://sattrack.app?zoom=0.6"
          class="w-full h-full border-0 rounded-lg shadow-2xl"
          title="Satellite Tracker"
          allowfullscreen
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"
        ></iframe>
      </div>

      <!-- Footer -->
      <FooterLayout class="relative z-20" />
    </div>
  </div>
</template>

<style scoped>
/* Styles spécifiques pour la page Satellite Tracker */
iframe {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  transform: scale(0.8);
  transform-origin: center center;
  width: 100%; /* Compensate for scale */
  height: 100%; /* Compensate for scale */
  min-width: 600px;
  min-height: 930px;
}
</style>
