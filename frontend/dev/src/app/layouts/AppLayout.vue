<script setup lang="ts">
import NavbarLayout from './NavbarLayout.vue'
import FooterLayout from './FooterLayout.vue'
import ParticlesBackground from '../components/ParticlesBackground.vue'

</script>

<template>
  <div class="min-h-screen w-full relative">
    <!-- Fond animé -->
    <ParticlesBackground class="absolute inset-0 z-0" />

    <!-- Contenu principal -->
    <div class="relative z-10 max-w-8xl w-full mx-auto pt-4 p-1 sm:p-4 md:p-7 space-y-10 min-h-screen">

      <!-- Navbar -->
      <NavbarLayout class="relative z-20" />

      <!-- Contenu des Pages -->
      <slot />

      <!-- Footer -->
      <FooterLayout class="relative z-20" />
    </div>
  </div>
</template>

<style scoped>

</style>
