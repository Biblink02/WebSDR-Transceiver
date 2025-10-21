<script setup lang="ts">
import { useDark, useToggle } from '@vueuse/core'
import FooterLayout from "./FooterLayout.vue";
import NavbarLayout from "./NavbarLayout.vue";

const isDarkMode = useDark()
const toggleDarkMode = useToggle(isDarkMode)
</script>

<template>
  <div class="max-w-7xl w-full mx-auto pt-4 p-1 sm:p-4 md:p-7 space-y-10 relative">
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
    <NavbarLayout />

    <!-- Page Content -->
    <slot />

    <!-- Footer -->
    <FooterLayout />
  </div>
</template>

<style scoped>
/* Vous pouvez ajouter ici des styles spécifiques au layout */
</style>
