<script setup lang="ts">
import AppLayout from "&/layouts/AppLayout.vue"
import { useDark, useToggle } from '@vueuse/core'
</script>

<template>
  <AppLayout>
    <div class="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900 p-6 text-center">
      <h1 class="text-4xl md:text-5xl font-serif font-bold text-gray-800 dark:text-gray-100 mb-4">
        About Us
      </h1>
      <p class="text-lg text-gray-600 dark:text-gray-300 max-w-xl">
        Bienvenue sur la page à propos. Nous sommes une équipe dédiée à créer la meilleure experience utilisateur.
      </p>
    </div>
  </AppLayout>
</template>
