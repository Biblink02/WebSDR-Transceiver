<script setup lang="ts">
import AppLayout from "&/layouts/AppLayout.vue";
</script>

<template>
  <AppLayout>
    <nav class="flex items-center space-x-8">
      <strong class="font-serif text-3xl font-semibold text-gray-800 dark:text-gray-100">
        <router-link
          to="/"
          class="cursor-pointer font-serif text-3xl font-semibold text-gray-800 dark:text-gray-100 hover:underline"
        >
          Our project
        </router-link>
      </strong>

      <router-link
        to="/sdr"
        class="font-serif text-xl text-gray-700 dark:text-gray-300 hover:underline"
      >
        SDR
      </router-link>

      <router-link
        to="/about"
        class="font-serif text-xl text-gray-700 dark:text-gray-300 hover:underline"
      >
        About us
      </router-link>
    </nav>
  </AppLayout>

  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 px-20">
    <h1
      class="font-serif text-2xl md:text-2xl font-bold text-gray-800 dark:text-gray-100 max-w-6xl mx-auto text-center"
    >
      This project, developed by group PRI05, aims to create software for a
      ground station capable of sending and receiving data from the QO-100
      geostationary satellite. The software displays both the transmitted
      signals and the demodulated received signals, with the additional feature
      of hearing the received audio.
    </h1>
  </div>
</template>

<style scoped></style>
